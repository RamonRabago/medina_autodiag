"""Acciones sobre órdenes: iniciar, finalizar, entregar, cancelar, autorizar."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import text, bindparam, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
from app.models.pago import Pago
from app.models.detalle_orden import DetalleRepuestoOrden
from app.models.repuesto import Repuesto
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.schemas.movimiento_inventario import MovimientoInventarioCreate
from app.models.movimiento_inventario import TipoMovimiento
from app.services.inventario_service import InventarioService
from app.schemas.orden_trabajo_schema import (
    OrdenTrabajoResponse,
    IniciarOrdenRequest,
    FinalizarOrdenRequest,
    EntregarOrdenRequest,
    AutorizarOrdenRequest,
)
from app.utils.decimal_utils import to_decimal, money_round
from app.utils.transaction import transaction
from app.config import settings
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter()
import logging

logger = logging.getLogger(__name__)


@router.post("/{orden_id}/iniciar", response_model=OrdenTrabajoResponse)
def iniciar_orden_trabajo(
    orden_id: int,
    request: IniciarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"])),
):
    """Iniciar el trabajo en una orden (cambiar estado a EN_PROCESO)."""
    logger.info(f"Usuario {current_user.email} iniciando orden ID: {orden_id}")
    orden = (
        db.query(OrdenTrabajo)
        .options(joinedload(OrdenTrabajo.detalles_repuesto))
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    estados_ini = {"PENDIENTE", "COTIZADA", "ESPERANDO_AUTORIZACION"}
    est = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    if est not in estados_ini:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede iniciar una orden en estado {orden.estado}",
        )
    if orden.requiere_autorizacion and not orden.autorizado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La orden requiere autorización del cliente antes de iniciar",
        )

    with transaction(db):
        if not getattr(orden, "cliente_proporciono_refacciones", False):
            for detalle_repuesto in orden.detalles_repuesto or []:
                if not detalle_repuesto.repuesto_id:
                    continue
                repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == detalle_repuesto.repuesto_id).first()
                if not repuesto:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repuesto con ID {detalle_repuesto.repuesto_id} no encontrado")
                if repuesto.stock_actual < detalle_repuesto.cantidad:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Stock insuficiente de {repuesto.nombre}. Disponible: {repuesto.stock_actual}, Necesario: {detalle_repuesto.cantidad}")
                try:
                    InventarioService.registrar_movimiento(
                        db,
                        MovimientoInventarioCreate(
                            id_repuesto=repuesto.id_repuesto,
                            tipo_movimiento=TipoMovimiento.SALIDA,
                            cantidad=detalle_repuesto.cantidad,
                            precio_unitario=None,
                            referencia=orden.numero_orden,
                            motivo=f"Inicio orden de trabajo {orden.numero_orden}",
                        ),
                        current_user.id_usuario,
                        autocommit=False,
                    )
                except ValueError as e:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        if not orden.tecnico_id and current_user.rol == "TECNICO":
            orden.tecnico_id = current_user.id_usuario
        if not orden.tecnico_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe asignar un técnico a la orden antes de iniciarla. Edita la orden y asigna un técnico.",
            )

        orden.estado = EstadoOrden.EN_PROCESO
        orden.fecha_inicio = datetime.utcnow()
        orden.id_usuario_inicio = current_user.id_usuario
        if request.observaciones_inicio:
            orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + f"\n[Inicio] {request.observaciones_inicio}"

    db.refresh(orden)
    registrar_auditoria(db, current_user.id_usuario, "INICIAR", "ORDEN_TRABAJO", orden_id, {"numero": orden.numero_orden})
    logger.info(f"Orden iniciada: {orden.numero_orden}")
    return orden


@router.post("/{orden_id}/finalizar", response_model=OrdenTrabajoResponse)
def finalizar_orden_trabajo(
    orden_id: int,
    request: FinalizarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "TECNICO"])),
):
    """Finalizar el trabajo en una orden (cambiar estado a COMPLETADA)."""
    logger.info(f"Usuario {current_user.email} finalizando orden ID: {orden_id}")
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para finalizar esta orden",
        )
    est = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    if est != "EN_PROCESO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden finalizar órdenes en proceso (estado actual: {est})",
        )
    with transaction(db):
        orden.estado = EstadoOrden.COMPLETADA
        orden.fecha_finalizacion = datetime.utcnow()
        orden.id_usuario_finalizacion = current_user.id_usuario
        if request.observaciones_finalizacion:
            orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + f"\n[Finalización] {request.observaciones_finalizacion}"
    db.refresh(orden)
    registrar_auditoria(db, current_user.id_usuario, "FINALIZAR", "ORDEN_TRABAJO", orden_id, {"numero": orden.numero_orden})
    logger.info(f"Orden finalizada: {orden.numero_orden}")
    return orden


@router.post("/{orden_id}/entregar", response_model=OrdenTrabajoResponse)
def entregar_orden_trabajo(
    orden_id: int,
    request: EntregarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"])),
):
    """Entregar la orden al cliente (cambiar estado a ENTREGADA)."""
    logger.info(f"Usuario {current_user.email} entregando orden ID: {orden_id}")
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado != "COMPLETADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden entregar órdenes completadas (estado actual: {orden.estado})",
        )
    venta = db.query(Venta).filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA").first()
    if not venta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes entregar: debes crear la venta y pagarla antes de entregar (Crea venta → registra pago en menú Ventas).",
        )
    total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == venta.id_venta).scalar()
    saldo = float(venta.total) - float(total_pagado or 0)
    if saldo > 0.001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes entregar: la venta aún no ha sido pagada. Registra el pago en menú Ventas antes de entregar.",
        )
    with transaction(db):
        orden.estado = EstadoOrden.ENTREGADA
        orden.fecha_entrega = datetime.utcnow()
        orden.id_usuario_entrega = current_user.id_usuario
        orden.observaciones_entrega = request.observaciones_entrega
    db.refresh(orden)
    registrar_auditoria(db, current_user.id_usuario, "ENTREGAR", "ORDEN_TRABAJO", orden_id, {"numero": orden.numero_orden})
    logger.info(f"Orden entregada: {orden.numero_orden}")
    return orden


@router.post("/{orden_id}/cancelar", response_model=OrdenTrabajoResponse)
def cancelar_orden_trabajo(
    orden_id: int,
    motivo: str = Query(..., min_length=10, description="Motivo de la cancelación"),
    devolver_repuestos: bool = Query(False, description="Devolver repuestos al inventario"),
    motivo_no_devolucion: Optional[str] = Query(None, description="Motivo por el que no se devuelven"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"])),
):
    """Cancelar una orden de trabajo."""
    logger.info(f"Usuario {current_user.email} cancelando orden ID: {orden_id}")
    orden = (
        db.query(OrdenTrabajo)
        .options(joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto))
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if orden.estado == "ENTREGADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar una orden ya entregada",
        )
    estado_str = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    cliente_proporciono = getattr(orden, "cliente_proporciono_refacciones", False)

    with transaction(db):
        if devolver_repuestos and estado_str == "EN_PROCESO" and not cliente_proporciono and orden.detalles_repuesto:
            for detalle_repuesto in orden.detalles_repuesto:
                if not detalle_repuesto.repuesto_id:
                    continue  # descripcion_libre: no está en inventario, nada que devolver
                try:
                    InventarioService.registrar_movimiento(
                        db,
                        MovimientoInventarioCreate(
                            id_repuesto=detalle_repuesto.repuesto_id,
                            tipo_movimiento=TipoMovimiento.ENTRADA,
                            cantidad=detalle_repuesto.cantidad,
                            precio_unitario=None,
                            referencia=orden.numero_orden,
                            motivo=f"Cancelación orden {orden.numero_orden} - repuestos no utilizados",
                        ),
                        current_user.id_usuario,
                        autocommit=False,
                    )
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
            logger.info(f"Repuestos devueltos al inventario por cancelación de orden {orden.numero_orden}")

        orden.estado = EstadoOrden.CANCELADA
        orden.motivo_cancelacion = motivo
        orden.fecha_cancelacion = datetime.utcnow()
        orden.id_usuario_cancelacion = current_user.id_usuario
        obs_cancel = f"\n[CANCELADA] {motivo}"
        if estado_str == "EN_PROCESO" and not devolver_repuestos and motivo_no_devolucion and orden.detalles_repuesto:
            repuestos_txt = ", ".join([
                f"{(d.repuesto.nombre if d.repuesto else f'Repuesto #{d.repuesto_id}')} x{d.cantidad}"
                for d in orden.detalles_repuesto
            ])
            obs_cancel += f". Repuestos no devueltos ({motivo_no_devolucion}): {repuestos_txt}"
        orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + obs_cancel

        venta_vinculada = db.query(Venta).filter(Venta.id_orden == orden_id, Venta.estado != "CANCELADA").first()
        if venta_vinculada:
            id_venta = venta_vinculada.id_venta
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
            venta_vinculada.total = money_round(subtotal * ivaf) if getattr(venta_vinculada, "requiere_factura", False) else money_round(subtotal)
            venta_vinculada.id_orden = None
            if not detalles_restantes:
                venta_vinculada.estado = "CANCELADA"
                venta_vinculada.motivo_cancelacion = f"Orden de trabajo {orden.numero_orden} cancelada. La venta quedó sin ítems."
                venta_vinculada.fecha_cancelacion = datetime.utcnow()
                venta_vinculada.id_usuario_cancelacion = current_user.id_usuario
                logger.info(f"Venta {id_venta} cancelada automáticamente (sin ítems tras cancelar orden {orden.numero_orden})")
            else:
                logger.info(f"Venta {id_venta} desvinculada y ítems de orden eliminados por cancelación de orden {orden.numero_orden}")

    db.refresh(orden)
    logger.info(f"Orden cancelada: {orden.numero_orden}")
    registrar_auditoria(db, current_user.id_usuario, "CANCELAR", "ORDEN_TRABAJO", orden_id, {"motivo": motivo[:200]})
    return orden


@router.post("/{orden_id}/autorizar", response_model=OrdenTrabajoResponse)
def autorizar_orden_trabajo(
    orden_id: int,
    request: AutorizarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"])),
):
    """Autorizar (o rechazar) una orden que requiere aprobación del cliente."""
    logger.info(f"Usuario {current_user.email} {'autorizando' if request.autorizado else 'rechazando'} orden ID: {orden_id}")
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    if not orden.requiere_autorizacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta orden no requiere autorización",
        )
    with transaction(db):
        orden.autorizado = request.autorizado
        orden.fecha_autorizacion = datetime.utcnow()
        orden.id_usuario_autorizacion = current_user.id_usuario
        if request.autorizado:
            orden.estado = EstadoOrden.PENDIENTE
        else:
            orden.estado = EstadoOrden.CANCELADA
            orden.motivo_cancelacion = (request.observaciones or "Rechazada por el cliente").strip()
            orden.fecha_cancelacion = datetime.utcnow()
            orden.id_usuario_cancelacion = current_user.id_usuario
        if request.observaciones:
            orden.observaciones_tecnico = (orden.observaciones_tecnico or "") + f"\n[Autorización] {request.observaciones}"
    db.refresh(orden)
    logger.info(f"Orden {'autorizada' if request.autorizado else 'rechazada'}: {orden.numero_orden}")
    registrar_auditoria(db, current_user.id_usuario, "AUTORIZAR" if request.autorizado else "RECHAZAR", "ORDEN_TRABAJO", orden_id, {"autorizado": request.autorizado})
    return orden
