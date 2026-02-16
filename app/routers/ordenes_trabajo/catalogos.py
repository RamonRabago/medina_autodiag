"""Catálogos y estadísticas de órdenes de trabajo."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden, PrioridadOrden
from app.models.detalle_orden import DetalleRepuestoOrden
from app.models.venta import Venta
from app.models.pago import Pago
from app.schemas.orden_trabajo_schema import OrdenTrabajoResponse
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.utils.transaction import transaction
from app.models.usuario import Usuario
from app.services.auditoria_service import registrar as registrar_auditoria

router = APIRouter()


@router.get("/estados/listar")
def listar_estados(current_user: Usuario = Depends(get_current_user)):
    estados = [
        {"valor": "PENDIENTE", "nombre": "Pendiente"},
        {"valor": "COTIZADA", "nombre": "Cotizada"},
        {"valor": "EN_PROCESO", "nombre": "En Proceso"},
        {"valor": "ESPERANDO_REPUESTOS", "nombre": "Esperando Repuestos"},
        {"valor": "ESPERANDO_AUTORIZACION", "nombre": "Esperando Autorización"},
        {"valor": "COMPLETADA", "nombre": "Completada"},
        {"valor": "ENTREGADA", "nombre": "Entregada"},
        {"valor": "CANCELADA", "nombre": "Cancelada"}
    ]
    return {"estados": estados}


@router.get("/prioridades/listar")
def listar_prioridades(current_user: Usuario = Depends(get_current_user)):
    prioridades = [
        {"valor": "BAJA", "nombre": "Baja"},
        {"valor": "NORMAL", "nombre": "Normal"},
        {"valor": "ALTA", "nombre": "Alta"},
        {"valor": "URGENTE", "nombre": "Urgente"}
    ]
    return {"prioridades": prioridades}


@router.get("/estadisticas/dashboard")
def obtener_estadisticas_dashboard(
    fecha_desde: str | None = Query(None, description="YYYY-MM-DD para filtrar total facturado"),
    fecha_hasta: str | None = Query(None, description="YYYY-MM-DD para filtrar total facturado"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA"]))
):
    ordenes_por_estado = db.query(
        OrdenTrabajo.estado,
        func.count(OrdenTrabajo.id).label('total')
    ).group_by(OrdenTrabajo.estado).all()
    hoy = datetime.now().date()
    ordenes_hoy = db.query(func.count(OrdenTrabajo.id)).filter(
        func.date(OrdenTrabajo.fecha_ingreso) == hoy
    ).scalar()
    q_facturado = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .join(Venta, Pago.id_venta == Venta.id_venta)
        .filter(Venta.estado != "CANCELADA")
    )
    if fecha_desde:
        q_facturado = q_facturado.filter(func.date(Pago.fecha) >= fecha_desde)
    if fecha_hasta:
        q_facturado = q_facturado.filter(func.date(Pago.fecha) <= fecha_hasta)
    total_facturado = q_facturado.scalar() or 0

    # Ventas del periodo (total Venta.total por fecha de venta) vs cobrado (pagos por fecha de pago)
    q_ventas = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(Venta.estado != "CANCELADA")
    if fecha_desde:
        q_ventas = q_ventas.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        q_ventas = q_ventas.filter(func.date(Venta.fecha) <= fecha_hasta)
    total_ventas_periodo = q_ventas.scalar() or 0

    ordenes_urgentes = db.query(func.count(OrdenTrabajo.id)).filter(
        OrdenTrabajo.prioridad == PrioridadOrden.URGENTE,
        OrdenTrabajo.estado.in_([EstadoOrden.PENDIENTE, EstadoOrden.EN_PROCESO])
    ).scalar()
    return {
        "ordenes_por_estado": [{"estado": estado, "total": total} for estado, total in ordenes_por_estado],
        "ordenes_hoy": ordenes_hoy,
        "total_facturado": float(total_facturado),
        "total_ventas_periodo": float(total_ventas_periodo),
        "ordenes_urgentes": ordenes_urgentes,
        "periodo_facturado": {"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta} if (fecha_desde or fecha_hasta) else None
    }


@router.post("/marcar-cotizacion-enviada", response_model=OrdenTrabajoResponse)
def marcar_cotizacion_enviada(
    orden_id: int = Query(..., description="ID de la orden"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN", "CAJA", "TECNICO"])),
):
    """Marcar que la cotización fue enviada al cliente (ruta alternativa para evitar 404)."""
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
            joinedload(OrdenTrabajo.usuario_cotizacion_enviada),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Orden de trabajo con ID {orden_id} no encontrada",
        )
    est = orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado)
    if est != "PENDIENTE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede marcar cotización enviada en órdenes PENDIENTE (estado actual: {est})",
        )
    with transaction(db):
        orden.fecha_cotizacion_enviada = datetime.utcnow()
        orden.id_usuario_cotizacion_enviada = current_user.id_usuario
        orden.estado = EstadoOrden.ESPERANDO_AUTORIZACION if orden.requiere_autorizacion else EstadoOrden.COTIZADA
    db.refresh(orden)
    registrar_auditoria(db, current_user.id_usuario, "COTIZACION_ENVIADA", "ORDEN_TRABAJO", orden_id, {})
    return orden
