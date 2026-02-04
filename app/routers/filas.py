"""Router para Filas (catálogo global de posiciones horizontales)"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.fila import Fila
from app.schemas.fila import FilaCreate, FilaUpdate, FilaOut
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/filas", tags=["Inventario - Filas"])


@router.post("/", response_model=FilaOut, status_code=status.HTTP_201_CREATED)
def crear_fila(
    data: FilaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Crea una nueva fila. Requiere ADMIN o CAJA."""
    existente = db.query(Fila).filter(Fila.codigo == data.codigo.strip()).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una fila con código '{data.codigo}'")
    nueva = Fila(**data.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    logger.info(f"Fila creada: {nueva.codigo} por {current_user.email}")
    return nueva


@router.get("/", response_model=List[FilaOut])
def listar_filas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    activo: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todas las filas."""
    q = db.query(Fila).order_by(Fila.codigo)
    if activo is not None:
        q = q.filter(Fila.activo == activo)
    return q.offset(skip).limit(limit).all()


@router.get("/{id_fila}", response_model=FilaOut)
def obtener_fila(
    id_fila: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene una fila por ID."""
    f = db.query(Fila).filter(Fila.id == id_fila).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fila no encontrada")
    return f


@router.put("/{id_fila}", response_model=FilaOut)
def actualizar_fila(
    id_fila: int,
    data: FilaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Actualiza una fila."""
    f = db.query(Fila).filter(Fila.id == id_fila).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fila no encontrada")
    if data.codigo and data.codigo.strip() != f.codigo:
        existente = db.query(Fila).filter(Fila.codigo == data.codigo.strip()).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe una fila con código '{data.codigo}'")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    db.commit()
    db.refresh(f)
    logger.info(f"Fila actualizada: {f.codigo} por {current_user.email}")
    return f


@router.delete("/{id_fila}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_fila(
    id_fila: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """Desactiva una fila. Requiere ADMIN."""
    f = db.query(Fila).filter(Fila.id == id_fila).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fila no encontrada")
    f.activo = False
    db.commit()
    logger.info(f"Fila desactivada: {f.codigo} por {current_user.email}")
    return None
