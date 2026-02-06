"""Endpoints CRUD de ventas: listar, obtener, actualizar, crear."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, bindparam

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.cliente import Cliente
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.pago import Pago
from app.models.repuesto import Repuesto
from app.schemas.venta import VentaCreate, VentaUpdate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.models.movimiento_inventario import TipoMovimiento
from app.services.inventario_service import InventarioService
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_decimal, money_round, to_float_money
from app.config import settings

from .helpers import serializar_detalles_venta

router = APIRouter()


@router.get("/")
def listar_ventas(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    estado: str | None = Query(None, description="Filtrar por estado"),
    id_cliente: int | None = Query(None, description="Filtrar por cliente"),
    fecha_desde: str | None = Query(None, description="Fecha desde YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha hasta YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    query = db.query(Venta)
    if estado:
        query = query.filter(Venta.estado == estado)
    if id_cliente:
        query = query.filter(Venta.id_cliente == id_cliente)
    if fecha_desde:
        query = query.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(Venta.fecha) <= fecha_hasta)
    total = query.count()
    ventas = query.order_by(Venta.fecha.desc()).offset(skip).limit(limit).all()
    resultado = []
    for v in ventas:
        cliente = db.query(Cliente).filter(Cliente.id_cliente == v.id_cliente).first() if v.id_cliente else None
        total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == v.id_venta).scalar()
        saldo = float(v.total) - float(total_pagado or 0)
        resultado.append({
            "id_venta": v.id_venta,
            "fecha": v.fecha.isoformat() if v.fecha else None,
            "nombre_cliente": cliente.nombre if cliente else None,
            "total": float(v.total),
            "saldo_pendiente": max(0, saldo),
            "estado": v.estado.value if hasattr(v.estado, "value") else str(v.estado),
        })
    return {
        "ventas": resultado,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get("/{id_venta}")
def obtener_venta(
    id_venta: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    cliente = db.query(Cliente).filter(Cliente.id_cliente == venta.id_cliente).first() if venta.id_cliente else None
    total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == venta.id_venta).scalar()
    detalles = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
    pagos = db.query(Pago).filter(Pago.id_venta == id_venta).order_by(Pago.fecha.asc()).all()
    orden_vinculada = None
    if getattr(venta, "id_orden", None):
        orden = db.query(OrdenTrabajo).options(
            joinedload(OrdenTrabajo.cliente), joinedload(OrdenTrabajo.vehiculo)
        ).filter(OrdenTrabajo.id == venta.id_orden).first()
        if orden:
            orden_vinculada = {
                "id": orden.id,
                "numero_orden": orden.numero_orden,
                "cliente_nombre": orden.cliente.nombre if orden.cliente else None,
                "vehiculo_info": f"{orden.vehiculo.marca} {orden.vehiculo.modelo} {orden.vehiculo.anio}" if orden.vehiculo else None,
                "estado": orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado),
            }
    return {
        "id_venta": venta.id_venta,
        "fecha": venta.fecha.isoformat() if venta.fecha else None,
        "id_cliente": venta.id_cliente,
        "id_vehiculo": venta.id_vehiculo,
        "nombre_cliente": cliente.nombre if cliente else None,
        "total": float(venta.total),
        "saldo_pendiente": max(0, float(venta.total) - float(total_pagado or 0)),
        "estado": venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado),
        "requiere_factura": bool(getattr(venta, "requiere_factura", False)),
        "comentarios": getattr(venta, "comentarios", None),
        "motivo_cancelacion": getattr(venta, "motivo_cancelacion", None),
        "fecha_cancelacion": venta.fecha_cancelacion.isoformat() if getattr(venta, "fecha_cancelacion", None) else None,
        "id_usuario_cancelacion": getattr(venta, "id_usuario_cancelacion", None),
        "id_orden": getattr(venta, "id_orden", None),
        "orden_vinculada": orden_vinculada,
        "detalles": serializar_detalles_venta(db, detalles),
        "pagos": [
            {
                "id_pago": p.id_pago,
                "fecha": p.fecha.isoformat() if p.fecha else None,
                "metodo": p.metodo.value if hasattr(p.metodo, "value") else str(p.metodo),
                "monto": float(p.monto),
                "referencia": p.referencia or None,
            }
            for p in pagos
        ],
    }


@router.put("/{id_venta}")
def actualizar_venta(
    id_venta: int,
    data: VentaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == "CANCELADA":
        raise HTTPException(status_code=400, detail="No se puede editar una venta cancelada")
    if not data.detalles or len(data.detalles) == 0:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos un detalle")

    total_pagado = to_float_money(db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == id_venta).scalar() or 0)
    subtotal = sum(to_decimal(item.cantidad) * to_decimal(item.precio_unitario) for item in data.detalles)
    ivaf = to_decimal(settings.IVA_FACTOR)
    total_nuevo = money_round(subtotal * ivaf) if data.requiere_factura else money_round(subtotal)
    tol = Decimal("0.01")
    if total_pagado > 0 and to_decimal(total_nuevo) < to_decimal(total_pagado) - tol:
        raise HTTPException(
            status_code=400,
            detail=f"El total no puede ser menor a lo ya pagado (${total_pagado:.2f})"
        )

    for item in data.detalles:
        if item.tipo == "PRODUCTO":
            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_item).first()
            if not rep:
                raise HTTPException(status_code=404, detail=f"Repuesto con ID {item.id_item} no encontrado")
            if not rep.activo or getattr(rep, "eliminado", False):
                raise HTTPException(status_code=400, detail=f"El repuesto '{rep.nombre}' no está disponible (inactivo o eliminado)")

    venta.id_cliente = data.id_cliente
    venta.id_vehiculo = data.id_vehiculo
    venta.requiere_factura = data.requiere_factura
    venta.comentarios = getattr(data, "comentarios", None)
    venta.total = total_nuevo

    detalles_actuales = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
    firma_actual = sorted((d.tipo, d.id_item, d.cantidad, float(d.precio_unitario or 0)) for d in detalles_actuales)
    firma_nueva = sorted((item.tipo, item.id_item, item.cantidad, float(item.precio_unitario or 0)) for item in data.detalles)
    if firma_actual == firma_nueva:
        db.commit()
        return {"id_venta": id_venta, "total": to_float_money(total_nuevo)}

    if not getattr(venta, "id_orden", None):
        detalles_antiguos = db.query(DetalleVenta).filter(
            DetalleVenta.id_venta == id_venta,
            DetalleVenta.tipo == "PRODUCTO"
        ).all()
        for det_ant in detalles_antiguos:
            try:
                InventarioService.registrar_movimiento(
                    db,
                    MovimientoInventarioCreate(
                        id_repuesto=det_ant.id_item,
                        tipo_movimiento=TipoMovimiento.ENTRADA,
                        cantidad=det_ant.cantidad,
                        precio_unitario=None,
                        referencia=f"Venta#{id_venta}",
                        motivo="Devolución por actualización de venta (productos removidos)",
                        id_venta=id_venta,
                    ),
                    current_user.id_usuario,
                )
            except ValueError as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

        for item in data.detalles:
            if item.tipo == "PRODUCTO":
                rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_item).first()
                if not rep:
                    raise HTTPException(status_code=400, detail=f"Repuesto {item.id_item} no encontrado")
                if not rep.activo or getattr(rep, "eliminado", False):
                    raise HTTPException(status_code=400, detail=f"El repuesto '{rep.nombre}' no está disponible")
                if rep.stock_actual < item.cantidad:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente para '{rep.nombre}'. Disponible: {rep.stock_actual}, solicitado: {item.cantidad}"
                    )

    try:
        ids_detalle = [r[0] for r in db.query(DetalleVenta.id_detalle).filter(DetalleVenta.id_venta == id_venta).all()]
        if ids_detalle:
            stmt = text("UPDATE detalles_devolucion SET id_detalle_venta = NULL WHERE id_detalle_venta IN :ids").bindparams(bindparam("ids", expanding=True))
            db.execute(stmt, {"ids": ids_detalle})
    except Exception:
        pass
    db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).delete()
    for item in data.detalles:
        sub = money_round(to_decimal(item.cantidad) * to_decimal(item.precio_unitario))
        db.add(DetalleVenta(
            id_venta=id_venta,
            tipo=item.tipo,
            id_item=item.id_item,
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=sub,
        ))

    if not getattr(venta, "id_orden", None):
        for item in data.detalles:
            if item.tipo == "PRODUCTO":
                try:
                    InventarioService.registrar_movimiento(
                        db,
                        MovimientoInventarioCreate(
                            id_repuesto=item.id_item,
                            tipo_movimiento=TipoMovimiento.SALIDA,
                            cantidad=item.cantidad,
                            precio_unitario=None,
                            referencia=f"Venta#{id_venta}",
                            motivo="Venta manual (actualización)",
                            id_venta=id_venta,
                        ),
                        current_user.id_usuario,
                    )
                except ValueError as e:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    return {"id_venta": id_venta, "total": to_float_money(total_nuevo)}


@router.post("/desde-orden/{orden_id}", status_code=status.HTTP_201_CREATED)
def crear_venta_desde_orden(
    orden_id: int,
    requiere_factura: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    """Crear una venta a partir de una orden de trabajo ENTREGADA o COMPLETADA."""
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.cliente),
            joinedload(OrdenTrabajo.vehiculo),
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    estado = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    if estado not in ("ENTREGADA", "COMPLETADA"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede crear venta desde órdenes ENTREGADAS o COMPLETADAS (estado actual: {estado})"
        )
    existente = db.query(Venta).filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA").first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Esta orden ya tiene una venta asociada (ID venta: {existente.id_venta})"
        )

    subtotal = to_decimal(orden.total)
    ivaf = to_decimal(settings.IVA_FACTOR)
    total_venta = money_round(subtotal * ivaf) if requiere_factura else money_round(subtotal)

    venta = Venta(
        id_cliente=orden.cliente_id,
        id_vehiculo=orden.vehiculo_id,
        id_usuario=current_user.id_usuario,
        id_orden=orden_id,
        total=total_venta,
        requiere_factura=requiere_factura,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)

    for d in orden.detalles_servicio or []:
        desc = d.descripcion or f"Servicio #{d.servicio_id}"
        sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(to_decimal(d.precio_unitario or 0) * (d.cantidad or 1))
        det = DetalleVenta(
            id_venta=venta.id_venta,
            tipo="SERVICIO",
            id_item=d.servicio_id,
            descripcion=desc[:150] if desc else None,
            cantidad=int(d.cantidad or 1),
            precio_unitario=to_decimal(d.precio_unitario or 0),
            subtotal=sub,
            id_orden_origen=orden_id,
        )
        db.add(det)

    for d in orden.detalles_repuesto or []:
        desc = (d.repuesto.nombre if d.repuesto else f"Repuesto #{d.repuesto_id}") or f"Repuesto #{d.repuesto_id}"
        sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(to_decimal(d.precio_unitario or 0) * (d.cantidad or 1))
        det = DetalleVenta(
            id_venta=venta.id_venta,
            tipo="PRODUCTO",
            id_item=d.repuesto_id,
            descripcion=desc[:150] if desc else None,
            cantidad=int(d.cantidad or 1),
            precio_unitario=to_decimal(d.precio_unitario or 0),
            subtotal=sub,
            id_orden_origen=orden_id,
        )
        db.add(det)

    db.commit()
    db.refresh(venta)
    return {
        "id_venta": venta.id_venta,
        "total": float(venta.total),
        "estado": venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado),
        "id_orden": orden_id,
        "numero_orden": orden.numero_orden,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_venta(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO"))
):
    if not data.detalles or len(data.detalles) == 0:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos un detalle")

    for item in data.detalles:
        if item.tipo == "PRODUCTO":
            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_item).first()
            if not rep:
                raise HTTPException(status_code=400, detail=f"Repuesto {item.id_item} no encontrado")
            if not rep.activo or getattr(rep, "eliminado", False):
                raise HTTPException(status_code=400, detail=f"El repuesto '{rep.nombre}' no está disponible")
            if rep.stock_actual < item.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para '{rep.nombre}'. Disponible: {rep.stock_actual}, solicitado: {item.cantidad}"
                )

    subtotal = sum(
        to_decimal(item.cantidad) * to_decimal(item.precio_unitario)
        for item in data.detalles
    )
    ivaf = to_decimal(settings.IVA_FACTOR)
    total_venta = money_round(subtotal * ivaf) if getattr(data, "requiere_factura", False) else money_round(subtotal)

    venta = Venta(
        id_cliente=data.id_cliente,
        id_vehiculo=data.id_vehiculo,
        id_usuario=current_user.id_usuario,
        total=total_venta,
        requiere_factura=getattr(data, "requiere_factura", False),
        comentarios=getattr(data, "comentarios", None),
    )

    db.add(venta)
    db.commit()
    db.refresh(venta)

    for item in data.detalles:
        subtotal_item = money_round(to_decimal(item.cantidad) * to_decimal(item.precio_unitario))
        detalle = DetalleVenta(
            id_venta=venta.id_venta,
            tipo=item.tipo,
            id_item=item.id_item,
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=subtotal_item
        )
        db.add(detalle)

    db.flush()

    for item in data.detalles:
        if item.tipo == "PRODUCTO":
            try:
                InventarioService.registrar_movimiento(
                    db,
                    MovimientoInventarioCreate(
                        id_repuesto=item.id_item,
                        tipo_movimiento=TipoMovimiento.SALIDA,
                        cantidad=item.cantidad,
                        precio_unitario=None,
                        referencia=f"Venta#{venta.id_venta}",
                        motivo="Venta manual",
                        id_venta=venta.id_venta,
                    ),
                    current_user.id_usuario,
                )
            except ValueError as e:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    db.commit()

    return {
        "id_venta": venta.id_venta,
        "total": float(venta.total),
        "estado": venta.estado
    }
