"""Endpoints de acciones sobre ventas: vincular orden, cancelar."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, bindparam, func

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.pago import Pago
from app.models.cancelacion_producto import CancelacionProducto
from app.models.repuesto import Repuesto
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.models.movimiento_inventario import TipoMovimiento
from app.services.inventario_service import InventarioService
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_decimal, money_round
from app.config import settings

router = APIRouter()


@router.get("/ordenes-disponibles")
def ordenes_disponibles_para_vincular(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    """Órdenes ENTREGADAS o COMPLETADAS que aún no tienen venta vinculada (excluye ventas canceladas)."""
    ids_ocupados = [
        r[0] for r in db.query(Venta.id_orden).filter(
            Venta.id_orden.isnot(None),
            Venta.estado != "CANCELADA"
        ).distinct().all()
    ]
    query = db.query(OrdenTrabajo).filter(
        OrdenTrabajo.estado.in_(["ENTREGADA", "COMPLETADA"]),
    )
    if ids_ocupados:
        query = query.filter(OrdenTrabajo.id.notin_(ids_ocupados))
    ordenes = (
        query.options(joinedload(OrdenTrabajo.cliente), joinedload(OrdenTrabajo.vehiculo))
        .order_by(OrdenTrabajo.fecha_ingreso.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": o.id,
            "numero_orden": o.numero_orden,
            "cliente_nombre": o.cliente.nombre if o.cliente else None,
            "vehiculo_info": f"{o.vehiculo.marca} {o.vehiculo.modelo} {o.vehiculo.anio}" if o.vehiculo else None,
            "estado": o.estado.value if hasattr(o.estado, "value") else str(o.estado),
            "total": float(o.total),
        }
        for o in ordenes
    ]


class VincularOrdenBody(BaseModel):
    id_orden: int | None = None


@router.put("/{id_venta}/vincular-orden")
def vincular_orden_venta(
    id_venta: int,
    body: VincularOrdenBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == "CANCELADA":
        raise HTTPException(status_code=400, detail="No se puede vincular orden a una venta cancelada")
    if body.id_orden is None:
        orden_id = venta.id_orden
        if orden_id:
            ids_a_eliminar = [
                r[0] for r in db.query(DetalleVenta.id_detalle).filter(
                    DetalleVenta.id_venta == id_venta,
                    DetalleVenta.id_orden_origen == orden_id
                ).all()
            ]
            if ids_a_eliminar:
                try:
                    stmt = text(
                        "UPDATE detalles_devolucion SET id_detalle_venta = NULL WHERE id_detalle_venta IN :ids"
                    ).bindparams(bindparam("ids", expanding=True))
                    db.execute(stmt, {"ids": ids_a_eliminar})
                except Exception:
                    pass
                db.query(DetalleVenta).filter(
                    DetalleVenta.id_venta == id_venta,
                    DetalleVenta.id_orden_origen == orden_id
                ).delete(synchronize_session=False)
            detalles_restantes = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
            subtotal = sum(to_decimal(d.subtotal) for d in detalles_restantes)
            ivaf = to_decimal(settings.IVA_FACTOR)
            venta.total = money_round(subtotal * ivaf) if getattr(venta, "requiere_factura", False) else money_round(subtotal)
        venta.id_orden = None
        db.commit()
        return {"id_venta": id_venta, "id_orden": None, "mensaje": "Orden desvinculada. Se eliminaron los ítems de la orden de la venta."}

    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == body.id_orden)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    if orden.estado not in ("ENTREGADA", "COMPLETADA"):
        raise HTTPException(status_code=400, detail="Solo se pueden vincular órdenes ENTREGADAS o COMPLETADAS")
    ya_vinculada = db.query(Venta).filter(Venta.id_orden == body.id_orden, Venta.id_venta != id_venta).first()
    if ya_vinculada:
        raise HTTPException(status_code=400, detail="Esta orden ya está vinculada a otra venta")

    venta.id_orden = body.id_orden

    for d in orden.detalles_servicio or []:
        desc = d.descripcion or f"Servicio #{d.servicio_id}"
        sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(to_decimal(d.precio_unitario or 0) * (d.cantidad or 1))
        det = DetalleVenta(
            id_venta=id_venta,
            tipo="SERVICIO",
            id_item=d.servicio_id,
            descripcion=desc[:150] if desc else None,
            cantidad=int(d.cantidad or 1),
            precio_unitario=to_decimal(d.precio_unitario or 0),
            subtotal=sub,
            id_orden_origen=body.id_orden,
        )
        db.add(det)

    for d in orden.detalles_repuesto or []:
        desc = (d.repuesto.nombre if d.repuesto else f"Repuesto #{d.repuesto_id}") or f"Repuesto #{d.repuesto_id}"
        sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(to_decimal(d.precio_unitario or 0) * (d.cantidad or 1))
        det = DetalleVenta(
            id_venta=id_venta,
            tipo="PRODUCTO",
            id_item=d.repuesto_id,
            descripcion=desc[:150] if desc else None,
            cantidad=int(d.cantidad or 1),
            precio_unitario=to_decimal(d.precio_unitario or 0),
            subtotal=sub,
            id_orden_origen=body.id_orden,
        )
        db.add(det)

    db.flush()
    detalles = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
    subtotal = sum(to_decimal(d.subtotal) for d in detalles)
    ivaf = to_decimal(settings.IVA_FACTOR)
    venta.total = money_round(subtotal * ivaf) if getattr(venta, "requiere_factura", False) else money_round(subtotal)

    db.commit()
    return {"id_venta": id_venta, "id_orden": body.id_orden, "mensaje": "Orden vinculada. Se agregaron los ítems de la orden a la venta."}


class ProductoCancelacionItem(BaseModel):
    id_detalle: int
    cantidad_reutilizable: int = Field(0, ge=0)
    cantidad_mer: int = Field(0, ge=0)
    motivo_mer: str | None = None


class CancelarVentaBody(BaseModel):
    motivo: str = Field(..., min_length=5)
    categoria_motivo: str | None = None
    productos: list[ProductoCancelacionItem] | None = None


@router.post("/{id_venta}/cancelar")
def cancelar_venta(
    id_venta: int,
    body: CancelarVentaBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == "CANCELADA":
        raise HTTPException(status_code=400, detail="La venta ya está cancelada")

    total_pagado = float(db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == id_venta).scalar() or 0)
    total_venta = float(venta.total)
    venta_pagada = total_pagado >= total_venta - 0.01

    detalles_prod = db.query(DetalleVenta).filter(
        DetalleVenta.id_venta == id_venta,
        DetalleVenta.tipo == "PRODUCTO"
    ).all()

    repuestos_no_devolver = set()
    if venta.id_orden:
        orden = (
            db.query(OrdenTrabajo)
            .options(joinedload(OrdenTrabajo.detalles_repuesto))
            .filter(OrdenTrabajo.id == venta.id_orden)
            .first()
        )
        if orden:
            if getattr(orden, "cliente_proporciono_refacciones", False):
                repuestos_no_devolver = {d.repuesto_id for d in (orden.detalles_repuesto or [])}
            else:
                repuestos_no_devolver = {
                    d.repuesto_id for d in (orden.detalles_repuesto or [])
                    if getattr(d, "cliente_provee", False)
                }

    productos_decidibles = [d for d in detalles_prod if d.id_item not in repuestos_no_devolver]
    if productos_decidibles and not body.productos:
        raise HTTPException(
            status_code=400,
            detail="Para ventas con productos, debes indicar por cada uno si es REUTILIZABLE o MERMA (productos requerido)."
        )
    if productos_decidibles and body.productos:
        ids_enviados = {p.id_detalle for p in body.productos}
        ids_requeridos = {d.id_detalle for d in productos_decidibles}
        faltantes = ids_requeridos - ids_enviados
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan decisiones para {len(faltantes)} producto(s). Indica cantidad_reutilizable y cantidad_mer para cada uno."
            )

    map_productos = {p.id_detalle: p for p in (body.productos or [])}
    motivo_base = body.motivo.strip()[:200]

    for det in detalles_prod:
        if det.id_item in repuestos_no_devolver:
            continue

        pitem = map_productos.get(det.id_detalle)
        if pitem is not None:
            cant_reutil = max(0, min(pitem.cantidad_reutilizable, det.cantidad))
            cant_mer = max(0, min(pitem.cantidad_mer, det.cantidad))
            if cant_reutil + cant_mer != det.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Producto '{det.descripcion}': cantidad_reutilizable ({cant_reutil}) + cantidad_mer ({cant_mer}) debe ser {det.cantidad}"
                )
            if cant_mer > 0 and not (pitem.motivo_mer or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"Producto '{det.descripcion}': motivo_mer obligatorio cuando cantidad_mer > 0"
                )

            rep = db.query(Repuesto).filter(Repuesto.id_repuesto == det.id_item).first()
            costo_u = to_decimal(rep.precio_compra or 0) if rep else to_decimal(0)
            costo_total_mer = money_round(costo_u * cant_mer) if cant_mer else None

            if cant_reutil > 0:
                try:
                    InventarioService.registrar_movimiento(
                        db,
                        MovimientoInventarioCreate(
                            id_repuesto=det.id_item,
                            tipo_movimiento=TipoMovimiento.ENTRADA,
                            cantidad=cant_reutil,
                            precio_unitario=None,
                            referencia=f"Venta#{id_venta}",
                            motivo=f"Devolución por cancelación de venta: {motivo_base}",
                        ),
                        current_user.id_usuario,
                    )
                except ValueError as e:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=str(e))

            if cant_mer > 0:
                db.add(CancelacionProducto(
                    id_venta=id_venta,
                    id_detalle_venta=det.id_detalle,
                    id_repuesto=det.id_item,
                    cantidad_reutilizable=cant_reutil,
                    cantidad_mer=cant_mer,
                    motivo_mer=(pitem.motivo_mer or "")[:500],
                    costo_unitario=costo_u,
                    costo_total_mer=costo_total_mer,
                    id_usuario=current_user.id_usuario,
                ))
            continue

        cant_reutil = det.cantidad
        try:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=det.id_item,
                    tipo_movimiento=TipoMovimiento.ENTRADA,
                    cantidad=cant_reutil,
                    precio_unitario=None,
                    referencia=f"Venta#{id_venta}",
                    motivo=f"Devolución por cancelación de venta: {motivo_base}",
                ),
                current_user.id_usuario,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    venta.estado = "CANCELADA"
    venta.motivo_cancelacion = body.motivo.strip()
    venta.fecha_cancelacion = datetime.utcnow()
    venta.id_usuario_cancelacion = current_user.id_usuario
    db.commit()
    return {"id_venta": id_venta, "estado": "CANCELADA"}
