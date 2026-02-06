"""Catálogos y estadísticas de órdenes de trabajo."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo
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
    total_facturado = db.query(func.coalesce(func.sum(Pago.monto), 0)).join(
        Venta, Pago.id_venta == Venta.id_venta
    ).filter(Venta.estado != "CANCELADA").scalar() or 0
    ordenes_urgentes = db.query(func.count(OrdenTrabajo.id)).filter(
        OrdenTrabajo.prioridad == "URGENTE",
        OrdenTrabajo.estado.in_(["PENDIENTE", "EN_PROCESO"])
    ).scalar()
    return {
        "ordenes_por_estado": [{"estado": estado, "total": total} for estado, total in ordenes_por_estado],
        "ordenes_hoy": ordenes_hoy,
        "total_facturado": float(total_facturado),
        "ordenes_urgentes": ordenes_urgentes
    }
