"""
Router para Proveedores
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.database import get_db
from app.models.proveedor import Proveedor
from app.schemas.proveedor import (
    ProveedorCreate,
    ProveedorUpdate,
    ProveedorOut
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/proveedores",
    tags=["Inventario - Proveedores"]
)


@router.post("/", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    proveedor: ProveedorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Crea un nuevo proveedor.
    
    Requiere rol: ADMIN o CAJA
    """
    nuevo_proveedor = Proveedor(**proveedor.model_dump())
    db.add(nuevo_proveedor)
    db.commit()
    db.refresh(nuevo_proveedor)
    
    logger.info(f"Proveedor creado: {nuevo_proveedor.nombre} por usuario {current_user.email}")
    
    return nuevo_proveedor


@router.get("/")
def listar_proveedores(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    buscar: Optional[str] = Query(None, description="Buscar en nombre, teléfono, email"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista proveedores con paginación y filtros.
    """
    query = db.query(Proveedor)
    if activo is not None:
        query = query.filter(Proveedor.activo == activo)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        query = query.filter(
            (Proveedor.nombre.like(term)) |
            (Proveedor.telefono.like(term)) |
            (Proveedor.email.like(term))
        )
    total = query.count()
    proveedores = query.order_by(Proveedor.nombre).offset(skip).limit(limit).all()
    return {
        "proveedores": proveedores,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.get("/{id_proveedor}", response_model=ProveedorOut)
def obtener_proveedor(
    id_proveedor: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene un proveedor específico por ID.
    """
    proveedor = db.query(Proveedor).filter(
        Proveedor.id_proveedor == id_proveedor
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proveedor con ID {id_proveedor} no encontrado"
        )
    
    return proveedor


@router.put("/{id_proveedor}", response_model=ProveedorOut)
def actualizar_proveedor(
    id_proveedor: int,
    proveedor_update: ProveedorUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Actualiza un proveedor existente.
    
    Requiere rol: ADMIN o CAJA
    """
    proveedor = db.query(Proveedor).filter(
        Proveedor.id_proveedor == id_proveedor
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proveedor con ID {id_proveedor} no encontrado"
        )
    
    # Actualizar campos
    update_data = proveedor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(proveedor, field, value)
    
    db.commit()
    db.refresh(proveedor)
    
    logger.info(f"Proveedor actualizado: {proveedor.nombre} por usuario {current_user.email}")
    
    return proveedor


@router.delete("/{id_proveedor}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proveedor(
    id_proveedor: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """
    Desactiva un proveedor (soft delete).
    
    Requiere rol: ADMIN
    
    NOTA: No elimina el registro, solo lo marca como inactivo.
    """
    proveedor = db.query(Proveedor).filter(
        Proveedor.id_proveedor == id_proveedor
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proveedor con ID {id_proveedor} no encontrado"
        )
    
    proveedor.activo = False
    db.commit()
    
    logger.info(f"Proveedor desactivado: {proveedor.nombre} por usuario {current_user.email}")
    
    return None


@router.post("/{id_proveedor}/reactivar", response_model=ProveedorOut)
def reactivar_proveedor(
    id_proveedor: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """
    Reactiva un proveedor desactivado.
    
    Requiere rol: ADMIN
    """
    proveedor = db.query(Proveedor).filter(
        Proveedor.id_proveedor == id_proveedor
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proveedor con ID {id_proveedor} no encontrado"
        )
    
    if proveedor.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El proveedor '{proveedor.nombre}' ya está activo"
        )
    
    proveedor.activo = True
    db.commit()
    db.refresh(proveedor)
    
    logger.info(f"Proveedor reactivado: {proveedor.nombre} por usuario {current_user.email}")
    
    return proveedor
