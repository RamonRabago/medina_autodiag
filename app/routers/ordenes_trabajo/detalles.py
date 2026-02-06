"""Agregar y eliminar servicios/repuestos de órdenes de trabajo."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.models.servicio import Servicio
from app.models.repuesto import Repuesto
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.models.movimiento_inventario import TipoMovimiento
from app.services.inventario_service import InventarioService
from app.schemas.orden_trabajo_schema import (
    AgregarServicioRequest,
    AgregarRepuestoRequest,
    OrdenTrabajoResponse,
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

router = APIRouter()
import logging

logger = logging.getLogger(__name__)


@router.post("/{orden_id}/servicios", response_model=OrdenTrabajoResponse)
def agregar_servicio_a_orden(
    orden_id: int,
    servicio_data: AgregarServicioRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"])),
):
    """Agregar un servicio a una orden de trabajo existente."""
    logger.info(f"Usuario {current_user.email} agregando servicio a orden ID: {orden_id}")
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden agregar servicios a una orden en estado {orden.estado}",
        )
    servicio = db.query(Servicio).filter(Servicio.id == servicio_data.servicio_id).first()
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {servicio_data.servicio_id} no encontrado",
        )
    precio_unitario = servicio_data.precio_unitario if servicio_data.precio_unitario else servicio.precio_base
    detalle = DetalleOrdenTrabajo(
        orden_trabajo_id=orden.id,
        servicio_id=servicio_data.servicio_id,
        descripcion=servicio_data.descripcion if servicio_data.descripcion else servicio.nombre,
        precio_unitario=precio_unitario,
        cantidad=servicio_data.cantidad,
        descuento=servicio_data.descuento,
        observaciones=servicio_data.observaciones,
    )
    detalle.calcular_subtotal()
    db.add(detalle)
    orden.subtotal_servicios += detalle.subtotal
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})",
        )
    orden.calcular_total()
    db.commit()
    db.refresh(orden)
    logger.info(f"Servicio agregado a orden: {orden.numero_orden}")
    return orden


@router.delete("/{orden_id}/servicios/{detalle_id}", response_model=OrdenTrabajoResponse)
def eliminar_servicio_de_orden(
    orden_id: int,
    detalle_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"])),
):
    """Eliminar un servicio de una orden de trabajo."""
    logger.info(f"Usuario {current_user.email} eliminando servicio {detalle_id} de orden ID: {orden_id}")
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden eliminar servicios de una orden en estado {orden.estado}",
        )
    detalle = db.query(DetalleOrdenTrabajo).filter(
        DetalleOrdenTrabajo.id == detalle_id,
        DetalleOrdenTrabajo.orden_trabajo_id == orden_id,
    ).first()
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {detalle_id} no encontrado en la orden",
        )
    orden.subtotal_servicios -= detalle.subtotal
    db.delete(detalle)
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tras eliminar, el descuento excede el subtotal. Reduzca el descuento a máximo {float(subtotal_base):.2f}",
        )
    orden.calcular_total()
    db.commit()
    db.refresh(orden)
    logger.info(f"Servicio eliminado de orden: {orden.numero_orden}")
    return orden


@router.post("/{orden_id}/repuestos", response_model=OrdenTrabajoResponse)
def agregar_repuesto_a_orden(
    orden_id: int,
    repuesto_data: AgregarRepuestoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"])),
):
    """Agregar un repuesto a una orden de trabajo existente."""
    logger.info(f"Usuario {current_user.email} agregando repuesto a orden ID: {orden_id}")
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado in ["ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden agregar repuestos a una orden en estado {orden.estado}",
        )
    repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == repuesto_data.repuesto_id).first()
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {repuesto_data.repuesto_id} no encontrado",
        )
    if getattr(repuesto, "eliminado", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El repuesto '{repuesto.nombre}' está eliminado y no puede agregarse",
        )
    cliente_proporciono = getattr(orden, "cliente_proporciono_refacciones", False)
    estado_str = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    if not cliente_proporciono and repuesto.stock_actual < repuesto_data.cantidad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock insuficiente para '{repuesto.nombre}'. Disponible: {repuesto.stock_actual}, Solicitado: {repuesto_data.cantidad}",
        )
    precio_unitario = repuesto_data.precio_unitario if repuesto_data.precio_unitario is not None else repuesto.precio_venta
    detalle = DetalleRepuestoOrden(
        orden_trabajo_id=orden.id,
        repuesto_id=repuesto_data.repuesto_id,
        cantidad=repuesto_data.cantidad,
        precio_unitario=precio_unitario,
        descuento=repuesto_data.descuento,
        observaciones=repuesto_data.observaciones,
    )
    detalle.calcular_subtotal()
    db.add(detalle)
    if estado_str == "EN_PROCESO" and not cliente_proporciono:
        try:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=repuesto.id_repuesto,
                    tipo_movimiento=TipoMovimiento.SALIDA,
                    cantidad=repuesto_data.cantidad,
                    precio_unitario=None,
                    referencia=orden.numero_orden,
                    motivo=f"Repuesto agregado a orden en proceso {orden.numero_orden}",
                ),
                current_user.id_usuario,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    orden.subtotal_repuestos += detalle.subtotal
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El descuento no puede exceder el subtotal (servicios + repuestos = {float(subtotal_base):.2f})",
        )
    orden.calcular_total()
    db.commit()
    db.refresh(orden)
    logger.info(f"Repuesto agregado a orden: {orden.numero_orden}")
    return orden


@router.delete("/{orden_id}/repuestos/{detalle_id}", response_model=OrdenTrabajoResponse)
def eliminar_repuesto_de_orden(
    orden_id: int,
    detalle_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"])),
):
    """Eliminar un repuesto de una orden de trabajo."""
    logger.info(f"Usuario {current_user.email} eliminando repuesto {detalle_id} de orden ID: {orden_id}")
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado in ["COMPLETADA", "ENTREGADA", "CANCELADA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden eliminar repuestos de una orden en estado {orden.estado}",
        )
    detalle = db.query(DetalleRepuestoOrden).filter(
        DetalleRepuestoOrden.id == detalle_id,
        DetalleRepuestoOrden.orden_trabajo_id == orden_id,
    ).first()
    if not detalle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {detalle_id} no encontrado en la orden",
        )
    orden.subtotal_repuestos -= detalle.subtotal
    db.delete(detalle)
    subtotal_base = (orden.subtotal_servicios or Decimal("0")) + (orden.subtotal_repuestos or Decimal("0"))
    if orden.descuento and float(orden.descuento) > float(subtotal_base):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tras eliminar, el descuento excede el subtotal. Reduzca el descuento a máximo {float(subtotal_base):.2f}",
        )
    orden.calcular_total()
    db.commit()
    db.refresh(orden)
    logger.info(f"Repuesto eliminado de orden: {orden.numero_orden}")
    return orden
