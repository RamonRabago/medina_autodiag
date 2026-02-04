"""
Router para Bodegas (Almacenes)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.bodega import Bodega
from app.schemas.bodega import BodegaCreate, BodegaUpdate, BodegaOut
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bodegas",
    tags=["Inventario - Bodegas"]
)


@router.post("/", response_model=BodegaOut, status_code=status.HTTP_201_CREATED)
def crear_bodega(
    bodega: BodegaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Crea una nueva bodega. Requiere ADMIN o CAJA."""
    existente = db.query(Bodega).filter(Bodega.nombre == bodega.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una bodega con el nombre '{bodega.nombre}'")
    nueva = Bodega(**bodega.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    logger.info(f"Bodega creada: {nueva.nombre} por {current_user.email}")
    return nueva


@router.get("/", response_model=List[BodegaOut])
def listar_bodegas(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    activo: bool | None = Query(None, description="Filtrar por activas/inactivas"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todas las bodegas."""
    q = db.query(Bodega).order_by(Bodega.nombre)
    if activo is not None:
        q = q.filter(Bodega.activo == activo)
    return q.offset(skip).limit(limit).all()


@router.get("/{id_bodega}", response_model=BodegaOut)
def obtener_bodega(
    id_bodega: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene una bodega por ID."""
    b = db.query(Bodega).filter(Bodega.id == id_bodega).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    return b


@router.put("/{id_bodega}", response_model=BodegaOut)
def actualizar_bodega(
    id_bodega: int,
    data: BodegaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Actualiza una bodega."""
    b = db.query(Bodega).filter(Bodega.id == id_bodega).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    if data.nombre and data.nombre != b.nombre:
        existente = db.query(Bodega).filter(Bodega.nombre == data.nombre).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe una bodega con el nombre '{data.nombre}'")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    logger.info(f"Bodega actualizada: {b.nombre} por {current_user.email}")
    return b


@router.delete("/{id_bodega}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_bodega(
    id_bodega: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """Elimina (o desactiva) una bodega. Requiere ADMIN."""
    b = db.query(Bodega).filter(Bodega.id == id_bodega).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    b.activo = False
    db.commit()
    logger.info(f"Bodega desactivada: {b.nombre} por {current_user.email}")
    return None
