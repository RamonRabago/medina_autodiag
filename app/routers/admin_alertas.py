from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.models.caja_alerta import CajaAlerta
from app.utils.roles import require_roles

TIPO_VALIDOS = ("DIFERENCIA_CAJA", "TURNO_LARGO")
NIVEL_VALIDOS = ("CRITICO", "WARNING", "INFO")

# =========================
# SCHEMAS
# =========================

class ResolverAlertasIn(BaseModel):
    ids_alertas: List[int]

# =========================
# ROUTER
# =========================

router = APIRouter()

# =========================
# LISTAR ALERTAS (ADMIN)
# =========================

@router.get("/alertas")
def listar_alertas(
    resueltas: Optional[bool] = Query(None),
    tipo: Optional[str] = Query(None, description=f"Filtrar por tipo: {', '.join(TIPO_VALIDOS)}"),
    nivel: Optional[str] = Query(None, description=f"Filtrar por nivel: {', '.join(NIVEL_VALIDOS)}"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    if tipo and tipo.strip().upper() not in TIPO_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido: '{tipo}'. Use: {', '.join(TIPO_VALIDOS)}",
        )
    if nivel and nivel.strip().upper() not in NIVEL_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Nivel inválido: '{nivel}'. Use: {', '.join(NIVEL_VALIDOS)}",
        )

    query = db.query(CajaAlerta)

    if resueltas is not None:
        query = query.filter(CajaAlerta.resuelta == resueltas)

    if tipo:
        query = query.filter(CajaAlerta.tipo == tipo.strip().upper())

    if nivel:
        query = query.filter(CajaAlerta.nivel == nivel.strip().upper())

    alertas = query.order_by(desc(CajaAlerta.fecha_creacion)).all()

    return [
        {
            "id_alerta": a.id_alerta,
            "id_turno": a.id_turno,
            "id_usuario": a.id_usuario,
            "tipo": a.tipo,
            "nivel": a.nivel,
            "mensaje": a.mensaje,
            "resuelta": a.resuelta,
            "fecha_creacion": a.fecha_creacion,
            "fecha_resolucion": a.fecha_resolucion,
            "resuelta_por": a.resuelta_por
        }
        for a in alertas
    ]

# =========================
# DASHBOARD RESUMEN
# =========================

@router.get("/dashboard/resumen")
def resumen_alertas(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    totales = db.query(
        func.count(CajaAlerta.id_alerta).label("total"),
        func.sum(case((CajaAlerta.resuelta == False, 1), else_=0)).label("pendientes"),
        func.sum(case((CajaAlerta.nivel == "CRITICO", 1), else_=0)).label("criticas"),
        func.sum(case((CajaAlerta.nivel == "WARNING", 1), else_=0)).label("warning"),
    ).one()

    return {
        "total": totales.total or 0,
        "pendientes": totales.pendientes or 0,
        "criticas": totales.criticas or 0,
        "warning": totales.warning or 0
    }

# =========================
# DASHBOARD ÚLTIMAS ALERTAS
# =========================

@router.get("/dashboard/ultimas")
def ultimas_alertas(
    limite: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    alertas = (
        db.query(CajaAlerta)
        .order_by(desc(CajaAlerta.fecha_creacion))
        .limit(limite)
        .all()
    )

    return [
        {
            "id_alerta": a.id_alerta,
            "tipo": a.tipo,
            "nivel": a.nivel,
            "mensaje": a.mensaje,
            "fecha_creacion": a.fecha_creacion,
            "resuelta": a.resuelta
        }
        for a in alertas
    ]

# =========================
# RESOLVER ALERTA INDIVIDUAL
# =========================

@router.post("/{id_alerta}/resolver")
def resolver_alerta(
    id_alerta: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    alerta = db.query(CajaAlerta).filter(
        CajaAlerta.id_alerta == id_alerta,
        CajaAlerta.resuelta == False
    ).first()

    if not alerta:
        raise HTTPException(
            status_code=404,
            detail="Alerta no encontrada o ya resuelta"
        )

    alerta.resuelta = True
    alerta.fecha_resolucion = datetime.utcnow()
    alerta.resuelta_por = current_user.id_usuario

    db.commit()
    db.refresh(alerta)

    return {
        "ok": True,
        "id_alerta": alerta.id_alerta,
        "fecha_resolucion": alerta.fecha_resolucion
    }

# =========================
# RESOLVER ALERTAS MÚLTIPLES (BATCH)
# =========================

@router.post("/resolver-multiples")
def resolver_alertas_multiples(
    data: ResolverAlertasIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    alertas = db.query(CajaAlerta).filter(
        CajaAlerta.id_alerta.in_(data.ids_alertas),
        CajaAlerta.resuelta == False
    ).all()

    if not alertas:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron alertas pendientes"
        )

    for alerta in alertas:
        alerta.resuelta = True
        alerta.fecha_resolucion = datetime.utcnow()
        alerta.resuelta_por = current_user.id_usuario

    db.commit()

    return {
        "ok": True,
        "resueltas": len(alertas)
    }


