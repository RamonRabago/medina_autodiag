"""Router para Estantes (dentro de bodegas)"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models.estante import Estante
from app.models.ubicacion import Ubicacion
from app.schemas.estante import EstanteCreate, EstanteUpdate, EstanteOut
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estantes", tags=["Inventario - Estantes"])


@router.post("/", response_model=EstanteOut, status_code=status.HTTP_201_CREATED)
def crear_estante(
    data: EstanteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Crea un nuevo estante dentro de una ubicación. Requiere ADMIN o CAJA."""
    ubi = db.query(Ubicacion).filter(Ubicacion.id == data.id_ubicacion).first()
    if not ubi:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    existente = db.query(Estante).filter(
        Estante.id_ubicacion == data.id_ubicacion,
        Estante.codigo == data.codigo.strip()
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un estante con código '{data.codigo}' en esa ubicación")
    nuevo = Estante(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    db.refresh(nuevo.ubicacion)
    logger.info(f"Estante creado: {nuevo.codigo} - {nuevo.nombre} por {current_user.email}")
    return nuevo


@router.get("/", response_model=List[EstanteOut])
def listar_estantes(
    skip: int = Query(0, ge=0),
    limit: int = Query(300, ge=1, le=500),
    id_bodega: int | None = Query(None, description="Filtrar por bodega"),
    id_ubicacion: int | None = Query(None, description="Filtrar por ubicación"),
    activo: bool | None = Query(None, description="Filtrar por activos/inactivos"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todos los estantes."""
    q = db.query(Estante).options(
        joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega)
    ).order_by(Estante.id_ubicacion, Estante.codigo)
    if id_ubicacion is not None:
        q = q.filter(Estante.id_ubicacion == id_ubicacion)
    if id_bodega is not None:
        q = q.join(Estante.ubicacion).filter(Ubicacion.id_bodega == id_bodega)
    if activo is not None:
        q = q.filter(Estante.activo == activo)
    return q.offset(skip).limit(limit).all()


@router.get("/{id_estante}", response_model=EstanteOut)
def obtener_estante(
    id_estante: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene un estante por ID."""
    e = db.query(Estante).options(
        joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega)
    ).filter(Estante.id == id_estante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estante no encontrado")
    return e


@router.put("/{id_estante}", response_model=EstanteOut)
def actualizar_estante(
    id_estante: int,
    data: EstanteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Actualiza un estante."""
    e = db.query(Estante).options(
        joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega)
    ).filter(Estante.id == id_estante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estante no encontrado")
    if data.id_ubicacion is not None:
        ubi = db.query(Ubicacion).filter(Ubicacion.id == data.id_ubicacion).first()
        if not ubi:
            raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    codigo = (data.codigo or e.codigo).strip()
    id_ubicacion = data.id_ubicacion if data.id_ubicacion is not None else e.id_ubicacion
    if codigo != e.codigo or id_ubicacion != e.id_ubicacion:
        existente = db.query(Estante).filter(
            Estante.id_ubicacion == id_ubicacion,
            Estante.codigo == codigo,
            Estante.id != id_estante
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe un estante con código '{codigo}' en esa ubicación")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    db.refresh(e.ubicacion)
    logger.info(f"Estante actualizado: {e.codigo} por {current_user.email}")
    return e


@router.delete("/{id_estante}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_estante(
    id_estante: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """Desactiva un estante. Requiere ADMIN."""
    e = db.query(Estante).filter(Estante.id == id_estante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estante no encontrado")
    e.activo = False
    db.commit()
    logger.info(f"Estante desactivado: {e.codigo} por {current_user.email}")
    return None
