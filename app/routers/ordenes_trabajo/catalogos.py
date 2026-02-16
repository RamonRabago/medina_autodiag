"""Catálogos y estadísticas de órdenes de trabajo."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden, PrioridadOrden
from app.models.venta import Venta
from app.models.pago import Pago
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

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
