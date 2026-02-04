"""
Router para Ubicaciones (posiciones dentro de bodegas)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models.ubicacion import Ubicacion
from app.models.bodega import Bodega
from app.schemas.ubicacion import UbicacionCreate, UbicacionUpdate, UbicacionOut
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ubicaciones",
    tags=["Inventario - Ubicaciones"]
)


@router.post("/", response_model=UbicacionOut, status_code=status.HTTP_201_CREATED)
def crear_ubicacion(
    data: UbicacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Crea una nueva ubicación. Requiere ADMIN o CAJA."""
    bodega = db.query(Bodega).filter(Bodega.id == data.id_bodega).first()
    if not bodega:
        raise HTTPException(status_code=404, detail="Bodega no encontrada")
    existente = db.query(Ubicacion).filter(
        Ubicacion.id_bodega == data.id_bodega,
        Ubicacion.codigo == data.codigo.strip()
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe una ubicación con código '{data.codigo}' en esa bodega")
    nueva = Ubicacion(**data.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    db.refresh(nueva.bodega)
    logger.info(f"Ubicación creada: {nueva.codigo} - {nueva.nombre} por {current_user.email}")
    return nueva


@router.get("/", response_model=List[UbicacionOut])
def listar_ubicaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    id_bodega: int | None = Query(None, description="Filtrar por bodega"),
    activo: bool | None = Query(None, description="Filtrar por activas/inactivas"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todas las ubicaciones."""
    q = db.query(Ubicacion).options(joinedload(Ubicacion.bodega)).order_by(Ubicacion.id_bodega, Ubicacion.codigo)
    if id_bodega is not None:
        q = q.filter(Ubicacion.id_bodega == id_bodega)
    if activo is not None:
        q = q.filter(Ubicacion.activo == activo)
    return q.offset(skip).limit(limit).all()


@router.get("/{id_ubicacion}", response_model=UbicacionOut)
def obtener_ubicacion(
    id_ubicacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene una ubicación por ID."""
    u = db.query(Ubicacion).options(joinedload(Ubicacion.bodega)).filter(Ubicacion.id == id_ubicacion).first()
    if not u:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    return u


@router.put("/{id_ubicacion}", response_model=UbicacionOut)
def actualizar_ubicacion(
    id_ubicacion: int,
    data: UbicacionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Actualiza una ubicación."""
    u = db.query(Ubicacion).options(joinedload(Ubicacion.bodega)).filter(Ubicacion.id == id_ubicacion).first()
    if not u:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    if data.id_bodega is not None:
        bodega = db.query(Bodega).filter(Bodega.id == data.id_bodega).first()
        if not bodega:
            raise HTTPException(status_code=404, detail="Bodega no encontrada")
    codigo = (data.codigo or u.codigo).strip()
    id_bodega = data.id_bodega if data.id_bodega is not None else u.id_bodega
    if codigo != u.codigo or id_bodega != u.id_bodega:
        existente = db.query(Ubicacion).filter(
            Ubicacion.id_bodega == id_bodega,
            Ubicacion.codigo == codigo,
            Ubicacion.id != id_ubicacion
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe una ubicación con código '{codigo}' en esa bodega")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    db.refresh(u.bodega)
    logger.info(f"Ubicación actualizada: {u.codigo} por {current_user.email}")
    return u


@router.delete("/{id_ubicacion}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_ubicacion(
    id_ubicacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """Desactiva una ubicación. Requiere ADMIN."""
    u = db.query(Ubicacion).filter(Ubicacion.id == id_ubicacion).first()
    if not u:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    u.activo = False
    db.commit()
    logger.info(f"Ubicación desactivada: {u.codigo} por {current_user.email}")
    return None
