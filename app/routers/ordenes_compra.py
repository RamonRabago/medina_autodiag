"""
Router para órdenes de compra a proveedores.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.orden_compra import OrdenCompra, DetalleOrdenCompra, EstadoOrdenCompra
from app.models.pago_orden_compra import PagoOrdenCompra
from app.models.proveedor import Proveedor
from app.models.repuesto import Repuesto
from app.models.movimiento_inventario import TipoMovimiento
from app.schemas.orden_compra import OrdenCompraCreate, OrdenCompraUpdate, RecepcionMercanciaRequest, ItemsOrdenCompra, PagoOrdenCompraCreate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.inventario_service import InventarioService
from app.utils.roles import require_roles
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter(prefix="/ordenes-compra", tags=["Órdenes de Compra"])


def _generar_numero(db: Session) -> str:
    hoy = datetime.utcnow().strftime("%Y%m%d")
    ultima = (
        db.query(OrdenCompra)
        .filter(OrdenCompra.numero.like(f"OC-{hoy}-%"))
        .order_by(OrdenCompra.id_orden_compra.desc())
        .first()
    )
    seq = 1
    if ultima and ultima.numero:
        try:
            seq = int(ultima.numero.split("-")[-1]) + 1
        except (ValueError, IndexError):
            pass
    return f"OC-{hoy}-{seq:04d}"


@router.post("/", status_code=201)
def crear_orden(
    data: OrdenCompraCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Crea una orden de compra en estado BORRADOR."""
    prov = db.query(Proveedor).filter(Proveedor.id_proveedor == data.id_proveedor).first()
    if not prov:
        raise HTTPException(404, detail="Proveedor no encontrado")
    if not prov.activo:
        raise HTTPException(400, detail="Proveedor inactivo")

    total = Decimal("0")
    for item in data.items:
        rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_repuesto).first()
        if not rep:
            raise HTTPException(404, detail=f"Repuesto {item.id_repuesto} no encontrado")
        total += Decimal(str(item.cantidad_solicitada)) * Decimal(str(item.precio_unitario_estimado))

    numero = _generar_numero(db)
    oc = OrdenCompra(
        numero=numero,
        id_proveedor=data.id_proveedor,
        id_usuario=current_user.id_usuario,
        estado=EstadoOrdenCompra.BORRADOR,
        total_estimado=total,
        observaciones=data.observaciones,
    )
    db.add(oc)
    db.flush()
    for item in data.items:
        det = DetalleOrdenCompra(
            id_orden_compra=oc.id_orden_compra,
            id_repuesto=item.id_repuesto,
            cantidad_solicitada=item.cantidad_solicitada,
            precio_unitario_estimado=item.precio_unitario_estimado,
        )
        db.add(det)
    db.commit()
    db.refresh(oc)
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "ORDEN_COMPRA", oc.id_orden_compra, {})
    return _orden_a_dict(db, oc)


@router.get("/")
def listar_ordenes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    estado: Optional[str] = Query(None),
    id_proveedor: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Lista órdenes de compra con filtros y paginación."""
    query = db.query(OrdenCompra).order_by(desc(OrdenCompra.fecha))
    if estado:
        query = query.filter(OrdenCompra.estado == estado)
    if id_proveedor:
        query = query.filter(OrdenCompra.id_proveedor == id_proveedor)
    total = query.count()
    ordenes = query.offset(skip).limit(limit).all()
    items = [_orden_a_dict(db, o) for o in ordenes]
    return {
        "ordenes": items,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.get("/estados")
def listar_estados(current_user=Depends(require_roles("ADMIN", "CAJA"))):
    return [{"valor": e.value} for e in EstadoOrdenCompra]


def _calcular_total_a_pagar(oc: OrdenCompra) -> Decimal:
    """Total a pagar = suma de (cantidad_recibida * precio_real_o_estimado) por detalle."""
    total = Decimal("0")
    for d in oc.detalles:
        if d.cantidad_recibida <= 0:
            continue
        precio = d.precio_unitario_real if d.precio_unitario_real is not None else d.precio_unitario_estimado
        total += Decimal(str(d.cantidad_recibida)) * Decimal(str(precio))
    return total


@router.get("/cuentas-por-pagar")
def listar_cuentas_por_pagar(
    id_proveedor: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Lista órdenes de compra con saldo pendiente por pagar.
    Solo órdenes RECIBIDA o RECIBIDA_PARCIAL con mercancía recibida.
    """
    query = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_([
            EstadoOrdenCompra.RECIBIDA,
            EstadoOrdenCompra.RECIBIDA_PARCIAL,
        ]),
        OrdenCompra.estado != EstadoOrdenCompra.CANCELADA,
    )
    if id_proveedor:
        query = query.filter(OrdenCompra.id_proveedor == id_proveedor)
    ordenes = query.order_by(OrdenCompra.fecha.desc()).all()

    items = []
    for oc in ordenes:
        total_a_pagar = _calcular_total_a_pagar(oc)
        if total_a_pagar <= 0:
            continue
        pagos = db.query(PagoOrdenCompra).filter(
            PagoOrdenCompra.id_orden_compra == oc.id_orden_compra
        ).all()
        total_pagado = sum(float(p.monto) for p in pagos)
        saldo = max(0, float(total_a_pagar) - total_pagado)
        if saldo <= 0:
            continue
        prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
        items.append({
            "id_orden_compra": oc.id_orden_compra,
            "numero": oc.numero,
            "nombre_proveedor": prov.nombre if prov else "",
            "id_proveedor": oc.id_proveedor,
            "total_a_pagar": round(float(total_a_pagar), 2),
            "total_pagado": round(total_pagado, 2),
            "saldo_pendiente": round(saldo, 2),
            "fecha_recepcion": oc.fecha_recepcion.isoformat() if oc.fecha_recepcion else None,
            "estado": oc.estado.value if hasattr(oc.estado, "value") else str(oc.estado),
        })
    return {
        "items": items,
        "total_cuentas": len(items),
        "total_saldo_pendiente": round(sum(i["saldo_pendiente"] for i in items), 2),
    }


@router.get("/{id_orden}")
def obtener_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    return _orden_a_dict(db, oc)


@router.put("/{id_orden}")
def actualizar_orden(
    id_orden: int,
    data: OrdenCompraUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado != EstadoOrdenCompra.BORRADOR:
        raise HTTPException(400, detail="Solo se puede editar una orden en BORRADOR")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(oc, k, v)
    db.commit()
    db.refresh(oc)
    return _orden_a_dict(db, oc)


@router.post("/{id_orden}/enviar")
def enviar_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Cambia estado a ENVIADA (listo para pedir al proveedor)."""
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado != EstadoOrdenCompra.BORRADOR:
        raise HTTPException(400, detail="Solo se puede enviar una orden en BORRADOR")
    oc.estado = EstadoOrdenCompra.ENVIADA
    oc.fecha_envio = datetime.utcnow()
    db.commit()
    db.refresh(oc)
    return _orden_a_dict(db, oc)


@router.post("/{id_orden}/recibir")
def recibir_mercancia(
    id_orden: int,
    data: RecepcionMercanciaRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Registra la recepción de mercancía.
    Por cada item: crea movimiento ENTRADA, actualiza stock (CPP), marca cantidad_recibida.
    """
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado not in (EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.RECIBIDA_PARCIAL):
        raise HTTPException(400, detail="Solo se puede recibir en órdenes ENVIADA o RECIBIDA_PARCIAL")

    if data.referencia_proveedor:
        oc.referencia_proveedor = data.referencia_proveedor

    ids_detalle = {d.id: d for d in oc.detalles}
    for item in data.items:
        if item.id_detalle not in ids_detalle:
            raise HTTPException(400, detail=f"Detalle {item.id_detalle} no pertenece a esta orden")
        if item.cantidad_recibida <= 0:
            continue
        det = ids_detalle[item.id_detalle]
        if item.cantidad_recibida > det.cantidad_solicitada - det.cantidad_recibida:
            raise HTTPException(
                400,
                detail=f"Cantidad recibida excede lo pendiente en línea {det.id} (repuesto {det.id_repuesto})"
            )
        precio = item.precio_unitario_real if item.precio_unitario_real is not None else float(det.precio_unitario_estimado)
        try:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=det.id_repuesto,
                    tipo_movimiento=TipoMovimiento.ENTRADA,
                    cantidad=item.cantidad_recibida,
                    precio_unitario=Decimal(str(precio)),
                    referencia=f"OC-{oc.id_orden_compra}",
                    motivo=f"Recepción orden compra {oc.numero}",
                ),
                current_user.id_usuario,
            )
        except ValueError as e:
            raise HTTPException(400, detail=str(e))
        det.cantidad_recibida += item.cantidad_recibida
        if precio != float(det.precio_unitario_estimado):
            det.precio_unitario_real = precio

    # Actualizar estado
    total_solicitado = sum(d.cantidad_solicitada for d in oc.detalles)
    total_recibido = sum(d.cantidad_recibida for d in oc.detalles)
    if total_recibido >= total_solicitado:
        oc.estado = EstadoOrdenCompra.RECIBIDA
        oc.fecha_recepcion = datetime.utcnow()
    else:
        oc.estado = EstadoOrdenCompra.RECIBIDA_PARCIAL
    db.commit()
    db.refresh(oc)
    registrar_auditoria(db, current_user.id_usuario, "ACTUALIZAR", "ORDEN_COMPRA", id_orden, {"accion": "recibir"})
    return _orden_a_dict(db, oc)


@router.post("/{id_orden}/items")
def agregar_items(
    id_orden: int,
    data: ItemsOrdenCompra,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Agrega items a una orden en BORRADOR."""
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado != EstadoOrdenCompra.BORRADOR:
        raise HTTPException(400, detail="Solo se pueden agregar items en órdenes BORRADOR")
    total_extra = Decimal("0")
    for item in data.items:
        rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_repuesto).first()
        if not rep:
            raise HTTPException(404, detail=f"Repuesto {item.id_repuesto} no encontrado")
        total_extra += Decimal(str(item.cantidad_solicitada)) * Decimal(str(item.precio_unitario_estimado))
        det = DetalleOrdenCompra(
            id_orden_compra=oc.id_orden_compra,
            id_repuesto=item.id_repuesto,
            cantidad_solicitada=item.cantidad_solicitada,
            precio_unitario_estimado=item.precio_unitario_estimado,
        )
        db.add(det)
    oc.total_estimado = (oc.total_estimado or 0) + total_extra
    db.commit()
    db.refresh(oc)
    return _orden_a_dict(db, oc)


@router.delete("/{id_orden}/items/{id_detalle}")
def quitar_item(
    id_orden: int,
    id_detalle: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Quita un item de una orden en BORRADOR."""
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado != EstadoOrdenCompra.BORRADOR:
        raise HTTPException(400, detail="Solo se pueden quitar items en órdenes BORRADOR")
    det = db.query(DetalleOrdenCompra).filter(
        DetalleOrdenCompra.id == id_detalle,
        DetalleOrdenCompra.id_orden_compra == id_orden,
    ).first()
    if not det:
        raise HTTPException(404, detail="Detalle no encontrado")
    subtotal = Decimal(str(det.cantidad_solicitada)) * Decimal(str(det.precio_unitario_estimado))
    oc.total_estimado = max(0, (oc.total_estimado or 0) - subtotal)
    db.delete(det)
    db.commit()
    db.refresh(oc)
    return _orden_a_dict(db, oc)


@router.post("/{id_orden}/pagar")
def registrar_pago(
    id_orden: int,
    data: PagoOrdenCompraCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Registra un pago contra una orden de compra (cuenta por pagar)."""
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado not in (EstadoOrdenCompra.RECIBIDA, EstadoOrdenCompra.RECIBIDA_PARCIAL):
        raise HTTPException(400, detail="Solo se pueden registrar pagos en órdenes RECIBIDA o RECIBIDA_PARCIAL")

    total_a_pagar = _calcular_total_a_pagar(oc)
    pagos_existentes = db.query(PagoOrdenCompra).filter(
        PagoOrdenCompra.id_orden_compra == id_orden
    ).all()
    total_pagado = sum(float(p.monto) for p in pagos_existentes)
    saldo = float(total_a_pagar) - total_pagado

    monto = Decimal(str(data.monto))
    if monto > saldo:
        raise HTTPException(
            400,
            detail=f"Monto excede el saldo pendiente (${saldo:.2f})",
        )

    pago = PagoOrdenCompra(
        id_orden_compra=id_orden,
        id_usuario=current_user.id_usuario,
        monto=monto,
        metodo=data.metodo,
        referencia=data.referencia,
        observaciones=data.observaciones,
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "PAGO_ORDEN_COMPRA", pago.id_pago, {"monto": float(monto)})
    return {
        "id_pago": pago.id_pago,
        "id_orden_compra": id_orden,
        "monto": float(pago.monto),
        "saldo_anterior": round(saldo, 2),
        "saldo_nuevo": round(saldo - float(pago.monto), 2),
    }


@router.post("/{id_orden}/cancelar")
def cancelar_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado not in (EstadoOrdenCompra.BORRADOR, EstadoOrdenCompra.ENVIADA):
        raise HTTPException(400, detail="Solo se puede cancelar órdenes BORRADOR o ENVIADA")
    oc.estado = EstadoOrdenCompra.CANCELADA
    db.commit()
    db.refresh(oc)
    registrar_auditoria(db, current_user.id_usuario, "CANCELAR", "ORDEN_COMPRA", id_orden, {})
    return _orden_a_dict(db, oc)


def _orden_a_dict(db: Session, oc: OrdenCompra) -> dict:
    detalles = []
    for d in oc.detalles:
        rep = db.query(Repuesto).filter(Repuesto.id_repuesto == d.id_repuesto).first()
        detalles.append({
            "id": d.id,
            "id_repuesto": d.id_repuesto,
            "nombre_repuesto": rep.nombre if rep else "",
            "codigo_repuesto": rep.codigo if rep else "",
            "cantidad_solicitada": d.cantidad_solicitada,
            "cantidad_recibida": d.cantidad_recibida,
            "cantidad_pendiente": d.cantidad_solicitada - d.cantidad_recibida,
            "precio_unitario_estimado": float(d.precio_unitario_estimado),
            "precio_unitario_real": float(d.precio_unitario_real) if d.precio_unitario_real else None,
        })
    prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
    return {
        "id_orden_compra": oc.id_orden_compra,
        "numero": oc.numero,
        "id_proveedor": oc.id_proveedor,
        "nombre_proveedor": prov.nombre if prov else "",
        "estado": oc.estado.value if hasattr(oc.estado, "value") else str(oc.estado),
        "total_estimado": float(oc.total_estimado or 0),
        "fecha": oc.fecha.isoformat() if oc.fecha else None,
        "fecha_envio": oc.fecha_envio.isoformat() if oc.fecha_envio else None,
        "fecha_recepcion": oc.fecha_recepcion.isoformat() if oc.fecha_recepcion else None,
        "observaciones": oc.observaciones,
        "referencia_proveedor": oc.referencia_proveedor,
        "detalles": detalles,
    }
