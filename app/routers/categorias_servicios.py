"""
Router para Categorías de Servicios
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models.categoria_servicio import CategoriaServicio
from app.models.servicio import Servicio
from app.schemas.categoria_servicio import (
    CategoriaServicioCreate,
    CategoriaServicioUpdate,
    CategoriaServicioOut,
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/categorias-servicios",
    tags=["Servicios - Categorías"],
)


@router.post("/", response_model=CategoriaServicioOut, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    data: CategoriaServicioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    nombre_norm = data.nombre.strip()
    existente = db.query(CategoriaServicio).filter(
        func.lower(CategoriaServicio.nombre) == nombre_norm.lower()
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una categoría con el nombre '{nombre_norm}'"
        )
    cat = CategoriaServicio(
        nombre=nombre_norm,
        descripcion=data.descripcion and data.descripcion.strip() or None,
        activo=data.activo,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    logger.info(f"Categoría de servicio creada: {cat.nombre} por {current_user.email}")
    return cat


@router.get("/", response_model=List[CategoriaServicioOut])
def listar_categorias(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    activo: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(CategoriaServicio)
    if activo is not None:
        q = q.filter(CategoriaServicio.activo == activo)
    return q.order_by(CategoriaServicio.nombre).offset(skip).limit(limit).all()


@router.get("/{id_categoria}", response_model=CategoriaServicioOut)
def obtener_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cat = db.query(CategoriaServicio).filter(CategoriaServicio.id == id_categoria).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return cat


@router.put("/{id_categoria}", response_model=CategoriaServicioOut)
def actualizar_categoria(
    id_categoria: int,
    data: CategoriaServicioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    cat = db.query(CategoriaServicio).filter(CategoriaServicio.id == id_categoria).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if data.nombre is not None:
        nombre_norm = data.nombre.strip()
        otro = db.query(CategoriaServicio).filter(
            func.lower(CategoriaServicio.nombre) == nombre_norm.lower(),
            CategoriaServicio.id != id_categoria,
        ).first()
        if otro:
            raise HTTPException(status_code=400, detail=f"Ya existe una categoría '{nombre_norm}'")
        cat.nombre = nombre_norm
    if data.descripcion is not None:
        cat.descripcion = data.descripcion.strip() or None
    if data.activo is not None:
        cat.activo = data.activo
    db.commit()
    db.refresh(cat)
    logger.info(f"Categoría actualizada: {cat.nombre} por {current_user.email}")
    return cat


@router.delete("/{id_categoria}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN")),
):
    cat = db.query(CategoriaServicio).filter(CategoriaServicio.id == id_categoria).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    n = db.query(Servicio).filter(Servicio.id_categoria == id_categoria).count()
    if n > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {n} servicio(s) con esta categoría. Asigna otra categoría primero."
        )
    db.delete(cat)
    db.commit()
    logger.info(f"Categoría eliminada: {cat.nombre} por {current_user.email}")
    return None
