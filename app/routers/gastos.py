"""
Router para Gastos Operativos.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import Optional

from app.database import get_db
from app.models.gasto_operativo import GastoOperativo
from app.models.caja_turno import CajaTurno
from app.schemas.gasto_operativo import GastoOperativoCreate, GastoOperativoUpdate, GastoOperativoOut
from app.utils.roles import require_roles
from app.models.usuario import Usuario

router = APIRouter(
    prefix="/gastos",
    tags=["Gastos Operativos"],
)


@router.post("/", response_model=GastoOperativoOut, status_code=status.HTTP_201_CREATED)
def crear_gasto(
    data: GastoOperativoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Registra un gasto operativo. Si hay turno abierto, se vincula automáticamente."""
    id_turno = data.id_turno
    if id_turno is None:
        turno = db.query(CajaTurno).filter(
            CajaTurno.id_usuario == current_user.id_usuario,
            CajaTurno.estado == "ABIERTO",
        ).first()
        id_turno = turno.id_turno if turno else None

    gasto = GastoOperativo(
        fecha=data.fecha,
        concepto=data.concepto,
        monto=data.monto,
        categoria=data.categoria,
        id_turno=id_turno,
        id_usuario=current_user.id_usuario,
        observaciones=data.observaciones,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.get("/")
def listar_gastos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    fecha_desde: Optional[str] = Query(None, description="YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="YYYY-MM-DD"),
    categoria: Optional[str] = Query(None, description="RENTA, SERVICIOS, MATERIAL, NOMINA, OTROS"),
    buscar: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Lista gastos con paginación y filtros."""
    query = db.query(GastoOperativo)
    if fecha_desde:
        query = query.filter(GastoOperativo.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(GastoOperativo.fecha <= fecha_hasta)
    if categoria:
        query = query.filter(GastoOperativo.categoria == categoria)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        query = query.filter(GastoOperativo.concepto.like(term))

    total = query.count()
    gastos = query.order_by(GastoOperativo.fecha.desc(), GastoOperativo.creado_en.desc()).offset(skip).limit(limit).all()

    return {
        "gastos": gastos,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.get("/resumen")
def resumen_gastos(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Total de gastos en un período (para dashboard y reportes)."""
    query = db.query(func.coalesce(func.sum(GastoOperativo.monto), 0)).select_from(GastoOperativo)
    if fecha_desde:
        query = query.filter(GastoOperativo.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(GastoOperativo.fecha <= fecha_hasta)
    total = query.scalar()
    return {"total_gastos": float(total)}


@router.get("/{id_gasto}", response_model=GastoOperativoOut)
def obtener_gasto(
    id_gasto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Obtiene un gasto por ID."""
    gasto = db.query(GastoOperativo).filter(GastoOperativo.id_gasto == id_gasto).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


@router.patch("/{id_gasto}", response_model=GastoOperativoOut)
def actualizar_gasto(
    id_gasto: int,
    data: GastoOperativoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Actualiza un gasto."""
    gasto = db.query(GastoOperativo).filter(GastoOperativo.id_gasto == id_gasto).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(gasto, k, v)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/{id_gasto}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_gasto(
    id_gasto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """Elimina un gasto."""
    gasto = db.query(GastoOperativo).filter(GastoOperativo.id_gasto == id_gasto).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(gasto)
    db.commit()
