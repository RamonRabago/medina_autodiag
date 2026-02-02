"""
Router para Categorías de Repuestos
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.categoria_repuesto import CategoriaRepuesto
from app.schemas.categoria_repuesto import (
    CategoriaRepuestoCreate,
    CategoriaRepuestoUpdate,
    CategoriaRepuestoOut
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/categorias-repuestos",
    tags=["Inventario - Categorías"]
)


@router.post("/", response_model=CategoriaRepuestoOut, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    categoria: CategoriaRepuestoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Crea una nueva categoría de repuestos.
    
    Requiere rol: ADMIN o CAJA
    """
    # Verificar si ya existe una categoría con ese nombre
    categoria_existente = db.query(CategoriaRepuesto).filter(
        CategoriaRepuesto.nombre == categoria.nombre
    ).first()
    
    if categoria_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una categoría con el nombre '{categoria.nombre}'"
        )
    
    nueva_categoria = CategoriaRepuesto(**categoria.model_dump())
    db.add(nueva_categoria)
    db.commit()
    db.refresh(nueva_categoria)
    
    logger.info(f"Categoría creada: {nueva_categoria.nombre} por usuario {current_user.email}")
    
    return nueva_categoria


@router.get("/", response_model=List[CategoriaRepuestoOut])
def listar_categorias(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todas las categorías de repuestos.
    """
    categorias = db.query(CategoriaRepuesto).offset(skip).limit(limit).all()
    return categorias


@router.get("/{id_categoria}", response_model=CategoriaRepuestoOut)
def obtener_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene una categoría específica por ID.
    """
    categoria = db.query(CategoriaRepuesto).filter(
        CategoriaRepuesto.id_categoria == id_categoria
    ).first()
    
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoría con ID {id_categoria} no encontrada"
        )
    
    return categoria


@router.put("/{id_categoria}", response_model=CategoriaRepuestoOut)
def actualizar_categoria(
    id_categoria: int,
    categoria_update: CategoriaRepuestoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Actualiza una categoría existente.
    
    Requiere rol: ADMIN o CAJA
    """
    categoria = db.query(CategoriaRepuesto).filter(
        CategoriaRepuesto.id_categoria == id_categoria
    ).first()
    
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoría con ID {id_categoria} no encontrada"
        )
    
    # Verificar nombre duplicado si se está cambiando
    if categoria_update.nombre and categoria_update.nombre != categoria.nombre:
        nombre_existente = db.query(CategoriaRepuesto).filter(
            CategoriaRepuesto.nombre == categoria_update.nombre
        ).first()
        
        if nombre_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una categoría con el nombre '{categoria_update.nombre}'"
            )
    
    # Actualizar campos
    update_data = categoria_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(categoria, field, value)
    
    db.commit()
    db.refresh(categoria)
    
    logger.info(f"Categoría actualizada: {categoria.nombre} por usuario {current_user.email}")
    
    return categoria


@router.delete("/{id_categoria}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """
    Elimina una categoría.
    
    Requiere rol: ADMIN
    
    NOTA: Solo se puede eliminar si no tiene repuestos asociados.
    """
    categoria = db.query(CategoriaRepuesto).filter(
        CategoriaRepuesto.id_categoria == id_categoria
    ).first()
    
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoría con ID {id_categoria} no encontrada"
        )
    
    # Verificar si tiene repuestos asociados
    if categoria.repuestos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la categoría porque tiene {len(categoria.repuestos)} repuestos asociados"
        )
    
    db.delete(categoria)
    db.commit()
    
    logger.info(f"Categoría eliminada: {categoria.nombre} por usuario {current_user.email}")
    
    return None
