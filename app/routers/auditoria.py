"""
Router para el registro de auditoría: consulta de acciones realizadas por usuarios.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.auditoria import Auditoria
from app.utils.roles import require_roles

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get("")
def listar_auditoria(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    modulo: Optional[str] = Query(None, description="Filtrar por módulo"),
    id_usuario: Optional[int] = Query(None, description="Filtrar por usuario"),
    skip: int = Query(0, ge=0, description="Registros a saltar (paginación)"),
    limit: int = Query(50, ge=1, le=500, description="Registros por página"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Lista registros de auditoría (acciones de usuarios sobre módulos).
    Solo ADMIN o CAJA. Soporta paginación con skip/limit.
    """
    query = db.query(Auditoria)
    if fecha_desde:
        try:
            f = datetime.strptime(fecha_desde[:10], "%Y-%m-%d")
            query = query.filter(Auditoria.fecha >= f)
        except (ValueError, TypeError):
            pass
    if fecha_hasta:
        try:
            f = datetime.strptime(fecha_hasta[:10], "%Y-%m-%d")
            f_end = f + timedelta(days=1)
            query = query.filter(Auditoria.fecha < f_end)
        except (ValueError, TypeError):
            pass
    if modulo:
        query = query.filter(Auditoria.modulo.ilike(f"%{modulo}%"))
    if id_usuario:
        query = query.filter(Auditoria.id_usuario == id_usuario)
    total = query.count()
    registros = query.order_by(desc(Auditoria.fecha)).offset(skip).limit(limit).all()
    items = []
    for r in registros:
        u = r.usuario if hasattr(r, "usuario") and r.usuario else None
        items.append({
            "id_auditoria": r.id_auditoria,
            "fecha": r.fecha.isoformat() if r.fecha else None,
            "usuario_email": u.email if u else None,
            "usuario_nombre": u.nombre if u else None,
            "modulo": r.modulo,
            "accion": r.accion,
            "id_referencia": r.id_referencia,
            "descripcion": r.descripcion,
        })
    return {
        "registros": items,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }
