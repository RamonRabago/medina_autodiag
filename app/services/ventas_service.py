"""
Servicio de Ventas - Lógica de negocio
Vincular/desvincular orden, cancelar, crear, actualizar.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, bindparam

from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.comision_devengada import ComisionDevengada
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.pago import Pago
from app.models.cancelacion_producto import CancelacionProducto
from app.models.repuesto import Repuesto
from app.schemas.venta import VentaCreate, VentaUpdate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.models.movimiento_inventario import TipoMovimiento
from app.services.inventario_service import InventarioService
from app.utils.decimal_utils import to_decimal, money_round, to_float_money
from app.config import settings

import logging

logger = logging.getLogger(__name__)


class VentasService:
    """Servicio para operaciones de ventas."""

    @staticmethod
    def ordenes_disponibles_para_vincular(db: Session, limit: int = 50) -> list[dict]:
        """Órdenes ENTREGADAS o COMPLETADAS sin venta vinculada."""
        ids_ocupados = [
            r[0] for r in db.query(Venta.id_orden).filter(
                Venta.id_orden.isnot(None),
                Venta.estado != "CANCELADA",
            ).distinct().all()
        ]
        query = db.query(OrdenTrabajo).filter(
            OrdenTrabajo.estado.in_(["ENTREGADA", "COMPLETADA"]),
        )
        if ids_ocupados:
            query = query.filter(OrdenTrabajo.id.notin_(ids_ocupados))
        ordenes = (
            query.options(
                joinedload(OrdenTrabajo.cliente),
                joinedload(OrdenTrabajo.vehiculo),
            )
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

    @staticmethod
    def vincular_orden_venta(
        db: Session, id_venta: int, id_orden: int | None, id_usuario: int
    ) -> dict:
        """Vincula o desvincula una orden a una venta. id_orden=None = desvincular."""
        try:
            venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
            if not venta:
                raise ValueError("Venta no encontrada")
            if venta.estado == "CANCELADA":
                raise ValueError("No se puede vincular orden a una venta cancelada")

            if id_orden is None:
                result = VentasService._desvincular_orden(db, venta, id_venta)
                return result

            orden = (
                db.query(OrdenTrabajo)
                .options(
                    joinedload(OrdenTrabajo.detalles_servicio),
                    joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
                )
                .filter(OrdenTrabajo.id == id_orden)
                .first()
            )
            if not orden:
                raise ValueError("Orden de trabajo no encontrada")
            if orden.estado not in ("ENTREGADA", "COMPLETADA"):
                raise ValueError("Solo se pueden vincular órdenes ENTREGADAS o COMPLETADAS")
            ya_vinculada = db.query(Venta).filter(
                Venta.id_orden == id_orden, Venta.id_venta != id_venta
            ).first()
            if ya_vinculada:
                raise ValueError("Esta orden ya está vinculada a otra venta")

            venta.id_orden = id_orden
            for d in orden.detalles_servicio or []:
                desc = d.descripcion or f"Servicio #{d.servicio_id}"
                sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(
                    to_decimal(d.precio_unitario or 0) * (d.cantidad or 1)
                )
                det = DetalleVenta(
                    id_venta=id_venta,
                    tipo="SERVICIO",
                    id_item=d.servicio_id,
                    descripcion=desc[:150] if desc else None,
                    cantidad=to_decimal(d.cantidad or 1),
                    precio_unitario=to_decimal(d.precio_unitario or 0),
                    subtotal=sub,
                    id_orden_origen=id_orden,
                )
                db.add(det)
            for d in orden.detalles_repuesto or []:
                desc = (d.repuesto.nombre if d.repuesto else f"Repuesto #{d.repuesto_id}") or f"Repuesto #{d.repuesto_id}"
                sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(
                    to_decimal(d.precio_unitario or 0) * (d.cantidad or 1)
                )
                det = DetalleVenta(
                    id_venta=id_venta,
                    tipo="PRODUCTO",
                    id_item=d.repuesto_id,
                    descripcion=desc[:150] if desc else None,
                    cantidad=to_decimal(d.cantidad or 1),
                    precio_unitario=to_decimal(d.precio_unitario or 0),
                    subtotal=sub,
                    id_orden_origen=id_orden,
                )
                db.add(det)
            db.flush()
            detalles = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
            subtotal = sum(to_decimal(d.subtotal) for d in detalles)
            ivaf = to_decimal(settings.IVA_FACTOR)
            venta.total = money_round(subtotal * ivaf) if getattr(venta, "requiere_factura", False) else money_round(subtotal)
            db.commit()
            return {"id_venta": id_venta, "id_orden": id_orden, "mensaje": "Orden vinculada. Se agregaron los ítems de la orden a la venta."}
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _desvincular_orden(db: Session, venta: Venta, id_venta: int) -> dict:
        orden_id = venta.id_orden
        if not orden_id:
            return {"id_venta": id_venta, "id_orden": None, "mensaje": "La venta no tenía orden vinculada."}
        ids_a_eliminar = [
            r[0] for r in db.query(DetalleVenta.id_detalle).filter(
                DetalleVenta.id_venta == id_venta,
                DetalleVenta.id_orden_origen == orden_id,
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
                DetalleVenta.id_orden_origen == orden_id,
            ).delete(synchronize_session=False)
        detalles_restantes = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
        subtotal = sum(to_decimal(d.subtotal) for d in detalles_restantes)
        ivaf = to_decimal(settings.IVA_FACTOR)
        venta.total = money_round(subtotal * ivaf) if getattr(venta, "requiere_factura", False) else money_round(subtotal)
        venta.id_orden = None
        db.commit()
        return {"id_venta": id_venta, "id_orden": None, "mensaje": "Orden desvinculada. Se eliminaron los ítems de la orden de la venta."}

    @staticmethod
    def cancelar_venta(
        db: Session,
        id_venta: int,
        motivo: str,
        id_usuario: int,
        productos: list[dict] | None = None,
    ) -> dict:
        """Cancela una venta. productos: [{id_detalle, cantidad_reutilizable, cantidad_mer, motivo_mer}]."""
        try:
            venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
            if not venta:
                raise ValueError("Venta no encontrada")
            if venta.estado == "CANCELADA":
                raise ValueError("La venta ya está cancelada")

            detalles_prod = db.query(DetalleVenta).filter(
                DetalleVenta.id_venta == id_venta,
                DetalleVenta.tipo == "PRODUCTO",
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
            if productos_decidibles and not productos:
                raise ValueError(
                    "Para ventas con productos, debes indicar por cada uno si es REUTILIZABLE o MERMA (productos requerido)."
                )
            if productos_decidibles and productos:
                ids_enviados = {p["id_detalle"] for p in productos}
                ids_requeridos = {d.id_detalle for d in productos_decidibles}
                faltantes = ids_requeridos - ids_enviados
                if faltantes:
                    raise ValueError(
                        f"Faltan decisiones para {len(faltantes)} producto(s). Indica cantidad_reutilizable y cantidad_mer para cada uno."
                    )

            map_productos = {p["id_detalle"]: p for p in (productos or [])}
            motivo_base = motivo.strip()[:200]

            for det in detalles_prod:
                if det.id_item in repuestos_no_devolver:
                    continue
                pitem = map_productos.get(det.id_detalle)
                if pitem is not None:
                    det_cant = to_decimal(det.cantidad)
                    cant_reutil = max(Decimal("0"), min(to_decimal(pitem.get("cantidad_reutilizable", 0)), det_cant))
                    cant_mer = max(Decimal("0"), min(to_decimal(pitem.get("cantidad_mer", 0)), det_cant))
                    if cant_reutil + cant_mer != det_cant:
                        raise ValueError(
                            f"Producto '{det.descripcion}': cantidad_reutilizable ({cant_reutil}) + cantidad_mer ({cant_mer}) debe ser {det.cantidad}"
                        )
                    if cant_mer > 0 and not (pitem.get("motivo_mer") or "").strip():
                        raise ValueError(
                            f"Producto '{det.descripcion}': motivo_mer obligatorio cuando cantidad_mer > 0"
                        )
                    rep = db.query(Repuesto).filter(Repuesto.id_repuesto == det.id_item).first()
                    costo_u = to_decimal(rep.precio_compra or 0) if rep else to_decimal(0)
                    costo_total_mer = money_round(costo_u * cant_mer) if cant_mer else None
                    if cant_reutil > 0:
                        InventarioService.registrar_movimiento(
                            db,
                            MovimientoInventarioCreate(
                                id_repuesto=det.id_item,
                                tipo_movimiento=TipoMovimiento.ENTRADA,
                                cantidad=cant_reutil,
                                precio_unitario=None,
                                referencia=f"Venta#{id_venta}",
                                motivo=f"Devolución por cancelación de venta: {motivo_base}",
                                id_venta=id_venta,
                            ),
                            id_usuario,
                            autocommit=False,
                        )
                    if cant_mer > 0:
                        db.add(CancelacionProducto(
                            id_venta=id_venta,
                            id_detalle_venta=det.id_detalle,
                            id_repuesto=det.id_item,
                            cantidad_reutilizable=cant_reutil,
                            cantidad_mer=cant_mer,
                            motivo_mer=(pitem.get("motivo_mer") or "")[:500],
                            costo_unitario=costo_u,
                            costo_total_mer=costo_total_mer,
                            id_usuario=id_usuario,
                        ))
                    continue
                cant_reutil = det.cantidad
                InventarioService.registrar_movimiento(
                    db,
                    MovimientoInventarioCreate(
                        id_repuesto=det.id_item,
                        tipo_movimiento=TipoMovimiento.ENTRADA,
                        cantidad=cant_reutil,
                        precio_unitario=None,
                        referencia=f"Venta#{id_venta}",
                        motivo=f"Devolución por cancelación de venta: {motivo_base}",
                        id_venta=id_venta,
                    ),
                    id_usuario,
                    autocommit=False,
                )

            venta.estado = "CANCELADA"
            venta.motivo_cancelacion = motivo.strip()
            venta.fecha_cancelacion = datetime.utcnow()
            venta.id_usuario_cancelacion = id_usuario
            db.query(ComisionDevengada).filter(ComisionDevengada.id_venta == id_venta).delete(synchronize_session=False)
            db.commit()
            return {"id_venta": id_venta, "estado": "CANCELADA"}
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def crear_venta(db: Session, data: VentaCreate, id_usuario: int) -> dict:
        """Crea una venta manual y descuenta stock."""
        try:
            if not data.detalles or len(data.detalles) == 0:
                raise ValueError("La venta debe tener al menos un detalle")
            for item in data.detalles:
                if item.tipo == "PRODUCTO":
                    rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_item).first()
                    if not rep:
                        raise ValueError(f"Repuesto {item.id_item} no encontrado")
                    if not rep.activo or getattr(rep, "eliminado", False):
                        raise ValueError(f"El repuesto '{rep.nombre}' no está disponible")
                    if rep.stock_actual < item.cantidad:
                        raise ValueError(
                            f"Stock insuficiente para '{rep.nombre}'. Disponible: {rep.stock_actual}, solicitado: {item.cantidad}"
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
                id_usuario=id_usuario,
                id_vendedor=getattr(data, "id_vendedor", None) or id_usuario,
                total=total_venta,
                requiere_factura=getattr(data, "requiere_factura", False),
                comentarios=getattr(data, "comentarios", None),
            )
            db.add(venta)
            db.flush()
            for item in data.detalles:
                subtotal_item = money_round(to_decimal(item.cantidad) * to_decimal(item.precio_unitario))
                detalle = DetalleVenta(
                    id_venta=venta.id_venta,
                    tipo=item.tipo,
                    id_item=item.id_item,
                    descripcion=item.descripcion,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    subtotal=subtotal_item,
                )
                db.add(detalle)
            db.flush()
            for item in data.detalles:
                if item.tipo == "PRODUCTO":
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
                        id_usuario,
                        autocommit=False,
                    )
            db.commit()
            db.refresh(venta)
            return {
                "id_venta": venta.id_venta,
                "total": float(venta.total),
                "estado": venta.estado,
            }
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def crear_venta_desde_orden(
        db: Session, orden_id: int, requiere_factura: bool, id_usuario: int
    ) -> dict:
        """Crea una venta a partir de una orden ENTREGADA o COMPLETADA."""
        try:
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
                raise ValueError("Orden de trabajo no encontrada")
            estado = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
            if estado not in ("ENTREGADA", "COMPLETADA"):
                raise ValueError(
                    f"Solo se puede crear venta desde órdenes ENTREGADAS o COMPLETADAS (estado actual: {estado})"
                )
            existente = db.query(Venta).filter(
                Venta.id_orden == orden_id, Venta.estado != "CANCELADA"
            ).first()
            if existente:
                raise ValueError(f"Esta orden ya tiene una venta asociada (ID venta: {existente.id_venta})")
            subtotal = to_decimal(orden.total)
            ivaf = to_decimal(settings.IVA_FACTOR)
            total_venta = money_round(subtotal * ivaf) if requiere_factura else money_round(subtotal)
            venta = Venta(
                id_cliente=orden.cliente_id,
                id_vehiculo=orden.vehiculo_id,
                id_usuario=id_usuario,
                id_vendedor=getattr(orden, "id_vendedor", None) or id_usuario,
                id_orden=orden_id,
                total=total_venta,
                requiere_factura=requiere_factura,
            )
            db.add(venta)
            db.flush()
            for d in orden.detalles_servicio or []:
                desc = d.descripcion or f"Servicio #{d.servicio_id}"
                sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(
                    to_decimal(d.precio_unitario or 0) * (d.cantidad or 1)
                )
                det = DetalleVenta(
                    id_venta=venta.id_venta,
                    tipo="SERVICIO",
                    id_item=d.servicio_id,
                    descripcion=desc[:150] if desc else None,
                    cantidad=to_decimal(d.cantidad or 1),
                    precio_unitario=to_decimal(d.precio_unitario or 0),
                    subtotal=sub,
                    id_orden_origen=orden_id,
                )
                db.add(det)
            for d in orden.detalles_repuesto or []:
                desc = (d.repuesto.nombre if d.repuesto else f"Repuesto #{d.repuesto_id}") or f"Repuesto #{d.repuesto_id}"
                sub = money_round(to_decimal(d.subtotal)) if d.subtotal else money_round(
                    to_decimal(d.precio_unitario or 0) * (d.cantidad or 1)
                )
                det = DetalleVenta(
                    id_venta=venta.id_venta,
                    tipo="PRODUCTO",
                    id_item=d.repuesto_id,
                    descripcion=desc[:150] if desc else None,
                    cantidad=to_decimal(d.cantidad or 1),
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
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def actualizar_venta(
        db: Session, id_venta: int, data: VentaUpdate, id_usuario: int
    ) -> dict:
        """Actualiza una venta y ajusta stock si es manual (sin id_orden)."""
        try:
            venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
            if not venta:
                raise ValueError("Venta no encontrada")
            if venta.estado == "CANCELADA":
                raise ValueError("No se puede editar una venta cancelada")
            if not data.detalles or len(data.detalles) == 0:
                raise ValueError("La venta debe tener al menos un detalle")

            total_pagado = to_float_money(
                db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == id_venta).scalar() or 0
            )
            subtotal = sum(to_decimal(item.cantidad) * to_decimal(item.precio_unitario) for item in data.detalles)
            ivaf = to_decimal(settings.IVA_FACTOR)
            total_nuevo = money_round(subtotal * ivaf) if data.requiere_factura else money_round(subtotal)
            tol = Decimal("0.01")
            if total_pagado > 0 and to_decimal(total_nuevo) < to_decimal(total_pagado) - tol:
                raise ValueError(f"El total no puede ser menor a lo ya pagado (${total_pagado:.2f})")

            for item in data.detalles:
                if item.tipo == "PRODUCTO":
                    rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_item).first()
                    if not rep:
                        raise ValueError(f"Repuesto con ID {item.id_item} no encontrado")
                    if not rep.activo or getattr(rep, "eliminado", False):
                        raise ValueError(f"El repuesto '{rep.nombre}' no está disponible (inactivo o eliminado)")

            venta.id_cliente = data.id_cliente
            venta.id_vehiculo = data.id_vehiculo
            venta.requiere_factura = data.requiere_factura
            venta.comentarios = getattr(data, "comentarios", None)
            venta.total = total_nuevo
            if data.id_vendedor is not None:
                venta.id_vendedor = data.id_vendedor

            # Si estaba PAGADA y el total aumentó (saldo > 0), pasar a PENDIENTE
            saldo_pendiente = to_float_money(to_decimal(total_nuevo) - to_decimal(total_pagado))
            estado_str = venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado)
            estado_actualizado = False
            mensaje_estado = None
            if estado_str == "PAGADA" and saldo_pendiente > 0:
                venta.estado = "PENDIENTE"
                estado_actualizado = True
                mensaje_estado = (
                    f"El total de la venta aumentó. Hay un saldo de ${saldo_pendiente:.2f} por cobrar. "
                    "La venta pasó a PENDIENTE."
                )

            detalles_actuales = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
            firma_actual = sorted((d.tipo, d.id_item, d.cantidad, float(d.precio_unitario or 0)) for d in detalles_actuales)
            firma_nueva = sorted((item.tipo, item.id_item, item.cantidad, float(item.precio_unitario or 0)) for item in data.detalles)
            if firma_actual == firma_nueva:
                db.commit()
                r = {"id_venta": id_venta, "total": to_float_money(total_nuevo)}
                if estado_actualizado:
                    r["estado_actualizado"] = True
                    r["saldo_pendiente"] = saldo_pendiente
                    r["mensaje"] = mensaje_estado
                return r

            if not getattr(venta, "id_orden", None):
                for det_ant in db.query(DetalleVenta).filter(
                    DetalleVenta.id_venta == id_venta, DetalleVenta.tipo == "PRODUCTO"
                ).all():
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
                        id_usuario,
                        autocommit=False,
                    )
                for item in data.detalles:
                    if item.tipo == "PRODUCTO":
                        rep = db.query(Repuesto).filter(Repuesto.id_repuesto == item.id_item).first()
                        if not rep:
                            raise ValueError(f"Repuesto {item.id_item} no encontrado")
                        if not rep.activo or getattr(rep, "eliminado", False):
                            raise ValueError(f"El repuesto '{rep.nombre}' no está disponible")
                        if rep.stock_actual < item.cantidad:
                            raise ValueError(
                                f"Stock insuficiente para '{rep.nombre}'. Disponible: {rep.stock_actual}, solicitado: {item.cantidad}"
                            )

            try:
                ids_detalle = [r[0] for r in db.query(DetalleVenta.id_detalle).filter(DetalleVenta.id_venta == id_venta).all()]
                if ids_detalle:
                    stmt = text("UPDATE detalles_devolucion SET id_detalle_venta = NULL WHERE id_detalle_venta IN :ids").bindparams(
                        bindparam("ids", expanding=True)
                    )
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
                            id_usuario,
                            autocommit=False,
                        )
            db.commit()
            r = {"id_venta": id_venta, "total": to_float_money(total_nuevo)}
            if estado_actualizado:
                r["estado_actualizado"] = True
                r["saldo_pendiente"] = saldo_pendiente
                r["mensaje"] = mensaje_estado
            return r
        except Exception:
            db.rollback()
            raise
