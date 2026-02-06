"""
Router para órdenes de compra a proveedores.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.orden_compra import OrdenCompra, DetalleOrdenCompra, EstadoOrdenCompra
from app.models.vehiculo import Vehiculo
from app.models.catalogo_vehiculo import CatalogoVehiculo
from app.models.pago_orden_compra import PagoOrdenCompra
from app.models.proveedor import Proveedor
from app.models.repuesto import Repuesto
from app.models.movimiento_inventario import TipoMovimiento
from app.schemas.orden_compra import OrdenCompraCreate, OrdenCompraUpdate, RecepcionMercanciaRequest, ItemsOrdenCompra, PagoOrdenCompraCreate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.services.inventario_service import InventarioService
from app.services.email_service import enviar_orden_compra_a_proveedor
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_decimal, money_round, to_float_money
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
    if data.id_catalogo_vehiculo is not None:
        cv = db.query(CatalogoVehiculo).filter(CatalogoVehiculo.id == data.id_catalogo_vehiculo).first()
        if not cv:
            raise HTTPException(404, detail="Vehículo del catálogo no encontrado")
    if not prov.activo:
        raise HTTPException(400, detail="Proveedor inactivo")

    total = Decimal("0")
    for item in data.items:
        if item.id_repuesto is not None:
            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_repuesto).first()
            if not rep:
                raise HTTPException(404, detail=f"Repuesto {item.id_repuesto} no encontrado")
            if getattr(rep, "eliminado", False):
                raise HTTPException(400, detail=f"El repuesto '{rep.nombre}' está eliminado y no puede agregarse a la orden")
        else:
            cod = (item.codigo_nuevo or "").strip()
            if cod and db.query(Repuesto).filter(Repuesto.codigo == cod).first():
                raise HTTPException(400, detail=f"El código '{cod}' ya existe en inventario. Usa el repuesto existente.")
        total += Decimal(str(item.cantidad_solicitada)) * Decimal(str(item.precio_unitario_estimado or 0))

    fecha_est = None
    if data.fecha_estimada_entrega and data.fecha_estimada_entrega.strip():
        try:
            from datetime import datetime as dt
            fecha_est = dt.strptime(data.fecha_estimada_entrega.strip()[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    numero = _generar_numero(db)
    oc = OrdenCompra(
        numero=numero,
        id_proveedor=data.id_proveedor,
        id_usuario=current_user.id_usuario,
        id_catalogo_vehiculo=data.id_catalogo_vehiculo,
        estado=EstadoOrdenCompra.BORRADOR,
        total_estimado=total,
        observaciones=data.observaciones,
        comprobante_url=data.comprobante_url,
        fecha_estimada_entrega=fecha_est,
    )
    db.add(oc)
    db.flush()
    for item in data.items:
        det = DetalleOrdenCompra(
            id_orden_compra=oc.id_orden_compra,
            id_repuesto=item.id_repuesto,
            codigo_nuevo=item.codigo_nuevo.strip() if item.codigo_nuevo else None,
            nombre_nuevo=item.nombre_nuevo.strip() if item.nombre_nuevo else None,
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
    pendientes_recibir: bool = Query(False, description="Solo órdenes ENVIADA o RECIBIDA_PARCIAL (pendientes de recibir)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Lista órdenes de compra con filtros y paginación."""
    query = db.query(OrdenCompra).order_by(desc(OrdenCompra.fecha))
    if pendientes_recibir:
        query = query.filter(OrdenCompra.estado.in_([
            EstadoOrdenCompra.ENVIADA,
            EstadoOrdenCompra.RECIBIDA_PARCIAL,
        ]))
    elif estado:
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


@router.get("/alertas")
def alertas_ordenes_sin_recibir(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Resumen de órdenes pendientes de recibir (ENVIADA, RECIBIDA_PARCIAL) para seguimiento.
    Incluye órdenes vencidas y próximas.
    """
    hoy = datetime.utcnow().date()
    base = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_([
            EstadoOrdenCompra.ENVIADA,
            EstadoOrdenCompra.RECIBIDA_PARCIAL,
        ])
    )
    ordenes_sin_recibir = base.count()
    hoy_dt = datetime.combine(hoy, datetime.min.time())
    ordenes_vencidas = base.filter(
        OrdenCompra.fecha_estimada_entrega.isnot(None),
        OrdenCompra.fecha_estimada_entrega < hoy_dt,
    ).count()

    # MySQL no soporta NULLS LAST; usar COALESCE para que NULLs queden al final
    ordenes = base.order_by(
        func.coalesce(OrdenCompra.fecha_estimada_entrega, datetime(9999, 12, 31)).asc()
    ).limit(limit * 3).all()

    items = []
    for oc in ordenes:
        fecha_est = getattr(oc, "fecha_estimada_entrega", None)
        vencida = False
        if fecha_est:
            try:
                fecha_est_date = fecha_est.date() if hasattr(fecha_est, "date") else fecha_est
                vencida = fecha_est_date < hoy
            except (AttributeError, TypeError):
                pass

        prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
        items.append({
            "id_orden_compra": oc.id_orden_compra,
            "numero": oc.numero,
            "nombre_proveedor": prov.nombre if prov else "",
            "estado": oc.estado.value if hasattr(oc.estado, "value") else str(oc.estado),
            "fecha_estimada_entrega": fecha_est.isoformat()[:10] if fecha_est else None,
            "vencida": vencida,
            "total_estimado": float(oc.total_estimado or 0),
        })

    # ordenar: vencidas primero, luego por fecha
    items.sort(key=lambda x: (0 if x["vencida"] else 1, x["fecha_estimada_entrega"] or "9999"))
    items = items[:limit]

    return {
        "ordenes_sin_recibir": ordenes_sin_recibir,
        "ordenes_vencidas": ordenes_vencidas,
        "items": items,
    }


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
        total_pagado = sum(to_decimal(p.monto) for p in pagos)
        saldo = money_round(max(Decimal("0"), total_a_pagar - total_pagado))
        if saldo <= 0:
            continue
        prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
        items.append({
            "id_orden_compra": oc.id_orden_compra,
            "numero": oc.numero,
            "nombre_proveedor": prov.nombre if prov else "",
            "id_proveedor": oc.id_proveedor,
            "total_a_pagar": to_float_money(total_a_pagar),
            "total_pagado": to_float_money(total_pagado),
            "saldo_pendiente": to_float_money(saldo),
            "fecha_recepcion": oc.fecha_recepcion.isoformat() if oc.fecha_recepcion else None,
            "estado": oc.estado.value if hasattr(oc.estado, "value") else str(oc.estado),
        })
    return {
        "items": items,
        "total_cuentas": len(items),
        "total_saldo_pendiente": to_float_money(sum(to_decimal(i["saldo_pendiente"]) for i in items)),
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
    # En BORRADOR/AUTORIZADA: edición de observaciones, comprobante (cotización), fecha estimada. En ENVIADA/RECIBIDA_PARCIAL: igual.
    campos_permitidos = {"observaciones", "referencia_proveedor", "comprobante_url", "fecha_estimada_entrega", "id_catalogo_vehiculo"}
    if oc.estado in (EstadoOrdenCompra.BORRADOR, EstadoOrdenCompra.AUTORIZADA, EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.RECIBIDA_PARCIAL):
        permitidos = campos_permitidos
    else:
        raise HTTPException(400, detail="No se puede editar la orden en este estado")
    dump = data.model_dump(exclude_unset=True)
    for k, v in dump.items():
        if k not in permitidos:
            continue
        if k == "id_catalogo_vehiculo":
            if v is not None:
                cv = db.query(CatalogoVehiculo).filter(CatalogoVehiculo.id == v).first()
                if not cv:
                    raise HTTPException(404, detail="Vehículo del catálogo no encontrado")
            oc.id_catalogo_vehiculo = v
        elif k == "fecha_estimada_entrega":
            if v and str(v).strip():
                try:
                    oc.fecha_estimada_entrega = datetime.strptime(str(v).strip()[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    oc.fecha_estimada_entrega = None
            else:
                oc.fecha_estimada_entrega = None
        else:
            setattr(oc, k, v)
    db.commit()
    db.refresh(oc)
    return _orden_a_dict(db, oc)


@router.post("/{id_orden}/autorizar")
def autorizar_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Autoriza la orden después de recibir la cotización del proveedor (ENVIADA → AUTORIZADA)."""
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado != EstadoOrdenCompra.ENVIADA:
        raise HTTPException(
            400,
            detail="Solo se puede autorizar una orden ENVIADA (después de que el proveedor haya respondido).",
        )
    if not oc.comprobante_url or not str(oc.comprobante_url).strip():
        raise HTTPException(
            400,
            detail="Debe subir la cotización formal del proveedor antes de autorizar la orden.",
        )
    oc.estado = EstadoOrdenCompra.AUTORIZADA
    db.commit()
    db.refresh(oc)
    registrar_auditoria(db, current_user.id_usuario, "AUTORIZAR", "ORDEN_COMPRA", id_orden, {})
    return _orden_a_dict(db, oc)


@router.post("/{id_orden}/enviar")
def enviar_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """Cambia estado a ENVIADA y envía email al proveedor (si tiene email y SMTP está configurado)."""
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado != EstadoOrdenCompra.BORRADOR:
        raise HTTPException(
            400,
            detail="Solo se puede enviar una orden en BORRADOR. Cree la orden y envíela al proveedor para solicitar cotización.",
        )

    prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
    email_enviado = False
    mensaje_email = None

    oc.estado = EstadoOrdenCompra.ENVIADA
    oc.fecha_envio = datetime.utcnow()
    db.commit()
    db.refresh(oc)

    # Intentar enviar email al proveedor
    if prov and prov.email and prov.email.strip():
        cv = db.query(CatalogoVehiculo).filter(CatalogoVehiculo.id == oc.id_catalogo_vehiculo).first() if getattr(oc, "id_catalogo_vehiculo", None) else None
        vh = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == oc.id_vehiculo).first() if getattr(oc, "id_vehiculo", None) else None
        vehiculo_info = None
        if cv:
            vehiculo_info = " ".join(filter(None, [cv.marca, cv.modelo, str(cv.anio), cv.version_trim, cv.motor]))
        elif vh:
            vehiculo_info = f"{vh.marca} {vh.modelo} {vh.anio}"

        lineas = []
        for d in oc.detalles:
            if d.id_repuesto is not None:
                rep = db.query(Repuesto).filter(Repuesto.id_repuesto == d.id_repuesto).first()
                nombre_repuesto = rep.nombre if rep else ""
                codigo_repuesto = rep.codigo if rep else ""
            else:
                nombre_repuesto = d.nombre_nuevo or ""
                codigo_repuesto = d.codigo_nuevo or ""
            lineas.append({
                "nombre_repuesto": nombre_repuesto or codigo_repuesto,
                "codigo_repuesto": codigo_repuesto,
                "cantidad_solicitada": d.cantidad_solicitada,
            })
        ok, err = enviar_orden_compra_a_proveedor(
            email_destino=prov.email,
            nombre_proveedor=prov.nombre,
            numero_orden=oc.numero,
            lineas=lineas,
            observaciones=oc.observaciones,
            vehiculo_info=vehiculo_info,
        )
        email_enviado = ok
        mensaje_email = None if ok else err

    result = _orden_a_dict(db, oc)
    result["email_enviado"] = email_enviado
    if mensaje_email:
        result["mensaje_email"] = mensaje_email
    return result


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
    if oc.estado not in (EstadoOrdenCompra.AUTORIZADA, EstadoOrdenCompra.RECIBIDA_PARCIAL):
        raise HTTPException(
            400,
            detail="Solo se puede recibir en órdenes AUTORIZADA o RECIBIDA_PARCIAL (después de autorizar).",
        )

    if data.referencia_proveedor:
        oc.referencia_proveedor = data.referencia_proveedor

    ids_detalle = {d.id: d for d in oc.detalles}
    for item in data.items:
        if item.id_detalle not in ids_detalle:
            raise HTTPException(400, detail=f"Detalle {item.id_detalle} no pertenece a esta orden")
        if item.cantidad_recibida <= 0:
            continue
        det = ids_detalle[item.id_detalle]
        pendiente = det.cantidad_solicitada - det.cantidad_recibida
        if item.cantidad_recibida > pendiente:
            raise HTTPException(
                400,
                detail=f"Cantidad recibida excede lo pendiente en línea {det.id}"
            )
        precio = item.precio_unitario_real if item.precio_unitario_real is not None else float(det.precio_unitario_estimado or 0)
        if float(precio) <= 0:
            raise HTTPException(
                400,
                detail="Indique el precio real (mayor a 0) para cada ítem antes de recibir.",
            )

        # Si es repuesto nuevo (sin id_repuesto), crear el repuesto en inventario antes de registrar entrada
        id_repuesto = det.id_repuesto
        if id_repuesto is None:
            cod = (det.codigo_nuevo or "").strip()
            nom = (det.nombre_nuevo or "").strip()
            if not nom:
                raise HTTPException(400, detail=f"Detalle {det.id}: falta nombre_nuevo para repuesto nuevo")
            if not cod:
                base = "PDTE EDITAR"
                cod = base
                n = 1
                while db.query(Repuesto).filter(Repuesto.codigo == cod).first():
                    n += 1
                    cod = f"{base}-{n}"
            elif db.query(Repuesto).filter(Repuesto.codigo == cod).first():
                raise HTTPException(400, detail=f"El código '{cod}' ya existe en inventario. No se puede crear repuesto nuevo.")
            precio_venta = round(float(precio) * 1.2, 2)
            nuevo = Repuesto(
                codigo=cod,
                nombre=nom,
                id_proveedor=oc.id_proveedor,
                precio_compra=Decimal(str(precio)),
                precio_venta=Decimal(str(precio_venta)),
                stock_actual=0,
                stock_minimo=5,
                stock_maximo=100,
                activo=True,
            )
            db.add(nuevo)
            db.flush()
            id_repuesto = nuevo.id_repuesto
            det.id_repuesto = id_repuesto
            det.codigo_nuevo = None
            det.nombre_nuevo = None

        try:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=id_repuesto,
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
        if item.id_repuesto is not None:
            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_repuesto).first()
            if not rep:
                raise HTTPException(404, detail=f"Repuesto {item.id_repuesto} no encontrado")
            if getattr(rep, "eliminado", False):
                raise HTTPException(400, detail=f"El repuesto '{rep.nombre}' está eliminado y no puede agregarse")
        else:
            cod = (item.codigo_nuevo or "").strip()
            if cod and db.query(Repuesto).filter(Repuesto.codigo == cod).first():
                raise HTTPException(400, detail=f"El código '{cod}' ya existe en inventario. Usa el repuesto existente.")
        total_extra += Decimal(str(item.cantidad_solicitada)) * Decimal(str(item.precio_unitario_estimado or 0))
        det = DetalleOrdenCompra(
            id_orden_compra=oc.id_orden_compra,
            id_repuesto=item.id_repuesto,
            codigo_nuevo=item.codigo_nuevo.strip() if item.codigo_nuevo else None,
            nombre_nuevo=item.nombre_nuevo.strip() if item.nombre_nuevo else None,
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
    total_pagado = sum(to_decimal(p.monto) for p in pagos_existentes)
    saldo = total_a_pagar - total_pagado

    monto = to_decimal(data.monto)
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
    registrar_auditoria(db, current_user.id_usuario, "CREAR", "PAGO_ORDEN_COMPRA", pago.id_pago, {"monto": to_float_money(monto)})
    saldo_nuevo = money_round(saldo - to_decimal(pago.monto))
    return {
        "id_pago": pago.id_pago,
        "id_orden_compra": id_orden,
        "monto": to_float_money(pago.monto),
        "saldo_anterior": to_float_money(saldo),
        "saldo_nuevo": to_float_money(saldo_nuevo),
    }


class CancelarOrdenCompraBody(BaseModel):
    motivo: str = Field(..., min_length=5, description="Motivo obligatorio de la cancelación")


@router.post("/{id_orden}/cancelar")
def cancelar_orden(
    id_orden: int,
    body: CancelarOrdenCompraBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    oc = db.query(OrdenCompra).filter(OrdenCompra.id_orden_compra == id_orden).first()
    if not oc:
        raise HTTPException(404, detail="Orden de compra no encontrada")
    if oc.estado not in (EstadoOrdenCompra.BORRADOR, EstadoOrdenCompra.AUTORIZADA, EstadoOrdenCompra.ENVIADA):
        raise HTTPException(400, detail="Solo se puede cancelar órdenes BORRADOR, AUTORIZADA o ENVIADA")
    oc.estado = EstadoOrdenCompra.CANCELADA
    oc.motivo_cancelacion = body.motivo.strip()
    oc.fecha_cancelacion = datetime.utcnow()
    oc.id_usuario_cancelacion = current_user.id_usuario
    db.commit()
    db.refresh(oc)
    registrar_auditoria(db, current_user.id_usuario, "CANCELAR", "ORDEN_COMPRA", id_orden, {"motivo": body.motivo.strip()[:200]})
    return _orden_a_dict(db, oc)


def _orden_a_dict(db: Session, oc: OrdenCompra) -> dict:
    detalles = []
    for d in oc.detalles:
        if d.id_repuesto is not None:
            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == d.id_repuesto).first()
            nombre_repuesto = rep.nombre if rep else ""
            codigo_repuesto = rep.codigo if rep else ""
        else:
            nombre_repuesto = d.nombre_nuevo or ""
            codigo_repuesto = d.codigo_nuevo or ""
        detalles.append({
            "id": d.id,
            "id_repuesto": d.id_repuesto,
            "codigo_nuevo": d.codigo_nuevo,
            "nombre_nuevo": d.nombre_nuevo,
            "nombre_repuesto": nombre_repuesto,
            "codigo_repuesto": codigo_repuesto,
            "cantidad_solicitada": d.cantidad_solicitada,
            "cantidad_recibida": d.cantidad_recibida,
            "cantidad_pendiente": d.cantidad_solicitada - d.cantidad_recibida,
            "precio_unitario_estimado": float(d.precio_unitario_estimado),
            "precio_unitario_real": float(d.precio_unitario_real) if d.precio_unitario_real else None,
        })
    prov = db.query(Proveedor).filter(Proveedor.id_proveedor == oc.id_proveedor).first()
    cv = db.query(CatalogoVehiculo).filter(CatalogoVehiculo.id == oc.id_catalogo_vehiculo).first() if getattr(oc, "id_catalogo_vehiculo", None) else None
    vh = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == oc.id_vehiculo).first() if getattr(oc, "id_vehiculo", None) else None
    fecha_est = getattr(oc, "fecha_estimada_entrega", None)
    hoy = datetime.utcnow().date()
    vencida = False
    if fecha_est and oc.estado in (EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.RECIBIDA_PARCIAL):
        try:
            fecha_est_date = fecha_est.date() if hasattr(fecha_est, "date") else fecha_est
            vencida = fecha_est_date < hoy
        except (AttributeError, TypeError):
            pass

    return {
        "id_orden_compra": oc.id_orden_compra,
        "numero": oc.numero,
        "id_proveedor": oc.id_proveedor,
        "nombre_proveedor": prov.nombre if prov else "",
        "email_proveedor": prov.email if prov and prov.email else None,
        "estado": oc.estado.value if hasattr(oc.estado, "value") else str(oc.estado),
        "total_estimado": float(oc.total_estimado or 0),
        "fecha": oc.fecha.isoformat() if oc.fecha else None,
        "fecha_envio": oc.fecha_envio.isoformat() if oc.fecha_envio else None,
        "fecha_recepcion": oc.fecha_recepcion.isoformat() if oc.fecha_recepcion else None,
        "fecha_estimada_entrega": fecha_est.isoformat()[:10] if fecha_est else None,
        "vencida": vencida,
        "observaciones": oc.observaciones,
        "id_catalogo_vehiculo": getattr(oc, "id_catalogo_vehiculo", None),
        "vehiculo_info": (
            " ".join(filter(None, [cv.marca, cv.modelo, str(cv.anio), cv.version_trim, cv.motor]))
            if cv else (f"{vh.marca} {vh.modelo} {vh.anio}" if vh else None)
        ),
        "referencia_proveedor": oc.referencia_proveedor,
        "comprobante_url": getattr(oc, "comprobante_url", None),
        "motivo_cancelacion": getattr(oc, "motivo_cancelacion", None),
        "fecha_cancelacion": oc.fecha_cancelacion.isoformat() if getattr(oc, "fecha_cancelacion", None) else None,
        "id_usuario_cancelacion": getattr(oc, "id_usuario_cancelacion", None),
        "detalles": detalles,
    }
