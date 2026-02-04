"""Router para Niveles (catálogo global de niveles verticales)"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.nivel import Nivel
from app.schemas.nivel import NivelCreate, NivelUpdate, NivelOut
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/niveles", tags=["Inventario - Niveles"])


@router.post("/", response_model=NivelOut, status_code=status.HTTP_201_CREATED)
def crear_nivel(
    data: NivelCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Crea un nuevo nivel. Requiere ADMIN o CAJA."""
    existente = db.query(Nivel).filter(Nivel.codigo == data.codigo.strip()).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un nivel con código '{data.codigo}'")
    nuevo = Nivel(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    logger.info(f"Nivel creado: {nuevo.codigo} por {current_user.email}")
    return nuevo


@router.get("/", response_model=List[NivelOut])
def listar_niveles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    activo: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todos los niveles."""
    q = db.query(Nivel).order_by(Nivel.codigo)
    if activo is not None:
        q = q.filter(Nivel.activo == activo)
    return q.offset(skip).limit(limit).all()


@router.get("/{id_nivel}", response_model=NivelOut)
def obtener_nivel(
    id_nivel: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene un nivel por ID."""
    n = db.query(Nivel).filter(Nivel.id == id_nivel).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nivel no encontrado")
    return n


@router.put("/{id_nivel}", response_model=NivelOut)
def actualizar_nivel(
    id_nivel: int,
    data: NivelUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Actualiza un nivel."""
    n = db.query(Nivel).filter(Nivel.id == id_nivel).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nivel no encontrado")
    if data.codigo and data.codigo.strip() != n.codigo:
        existente = db.query(Nivel).filter(Nivel.codigo == data.codigo.strip()).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe un nivel con código '{data.codigo}'")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    logger.info(f"Nivel actualizado: {n.codigo} por {current_user.email}")
    return n


@router.delete("/{id_nivel}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_nivel(
    id_nivel: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """Desactiva un nivel. Requiere ADMIN."""
    n = db.query(Nivel).filter(Nivel.id == id_nivel).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nivel no encontrado")
    n.activo = False
    db.commit()
    logger.info(f"Nivel desactivado: {n.codigo} por {current_user.email}")
    return None
