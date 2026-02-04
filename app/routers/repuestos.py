"""
Router para Repuestos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.repuesto import Repuesto
from app.models.categoria_repuesto import CategoriaRepuesto
from app.models.proveedor import Proveedor
from app.schemas.repuesto import (
    RepuestoCreate,
    RepuestoUpdate,
    RepuestoOut
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario
from app.services.inventario_service import InventarioService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/repuestos",
    tags=["Inventario - Repuestos"]
)


@router.post("/", response_model=RepuestoOut, status_code=status.HTTP_201_CREATED)
def crear_repuesto(
    repuesto: RepuestoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Crea un nuevo repuesto.
    
    Requiere rol: ADMIN o CAJA
    """
    # Verificar si ya existe un repuesto con ese código
    repuesto_existente = db.query(Repuesto).filter(
        Repuesto.codigo == repuesto.codigo.upper()
    ).first()
    
    if repuesto_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un repuesto con el código '{repuesto.codigo}'"
        )
    
    # Verificar que la categoría existe (si se proporcionó)
    if repuesto.id_categoria:
        categoria = db.query(CategoriaRepuesto).filter(
            CategoriaRepuesto.id_categoria == repuesto.id_categoria
        ).first()
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoría con ID {repuesto.id_categoria} no encontrada"
            )
    
    # Verificar que el proveedor existe (si se proporcionó)
    if repuesto.id_proveedor:
        proveedor = db.query(Proveedor).filter(
            Proveedor.id_proveedor == repuesto.id_proveedor
        ).first()
        if not proveedor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proveedor con ID {repuesto.id_proveedor} no encontrado"
            )
    
    nuevo_repuesto = Repuesto(**repuesto.model_dump())
    db.add(nuevo_repuesto)
    db.commit()
    db.refresh(nuevo_repuesto)
    
    # Verificar alertas de stock
    InventarioService.verificar_alertas_stock(db, nuevo_repuesto)
    
    logger.info(f"Repuesto creado: {nuevo_repuesto.codigo} - {nuevo_repuesto.nombre} por usuario {current_user.email}")
    
    return nuevo_repuesto


class RepuestoListResponse(BaseModel):
    repuestos: List[RepuestoOut]
    total: int
    total_paginas: int


@router.get("/", response_model=RepuestoListResponse)
def listar_repuestos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    id_categoria: Optional[int] = Query(None, description="Filtrar por categoría"),
    id_proveedor: Optional[int] = Query(None, description="Filtrar por proveedor"),
    stock_bajo: Optional[bool] = Query(None, description="Solo repuestos con stock bajo"),
    buscar: Optional[str] = Query(None, description="Buscar por código, nombre o marca"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista repuestos con filtros y paginación.
    """
    query = db.query(Repuesto).options(
        joinedload(Repuesto.categoria),
        joinedload(Repuesto.proveedor),
    )
    if activo is not None:
        query = query.filter(Repuesto.activo == activo)
    if id_categoria is not None:
        query = query.filter(Repuesto.id_categoria == id_categoria)
    if id_proveedor is not None:
        query = query.filter(Repuesto.id_proveedor == id_proveedor)
    if stock_bajo:
        query = query.filter(Repuesto.stock_actual <= Repuesto.stock_minimo)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        query = query.filter(
            or_(
                Repuesto.codigo.like(term),
                Repuesto.nombre.like(term),
                Repuesto.marca.like(term),
            )
        )
    total = query.count()
    repuestos = query.order_by(Repuesto.codigo).offset(skip).limit(limit).all()
    total_paginas = (total + limit - 1) // limit if limit > 0 else 1
    return {"repuestos": repuestos, "total": total, "total_paginas": total_paginas}


@router.get("/buscar-codigo/{codigo}", response_model=RepuestoOut)
def buscar_por_codigo(
    codigo: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Busca un repuesto por su código exacto.
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.codigo == codigo.upper()
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con código '{codigo}' no encontrado"
        )
    
    return repuesto


@router.get("/{id_repuesto}", response_model=RepuestoOut)
def obtener_repuesto(
    id_repuesto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene un repuesto específico por ID.
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.id_repuesto == id_repuesto
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {id_repuesto} no encontrado"
        )
    
    return repuesto


@router.put("/{id_repuesto}", response_model=RepuestoOut)
def actualizar_repuesto(
    id_repuesto: int,
    repuesto_update: RepuestoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Actualiza un repuesto existente.
    
    Requiere rol: ADMIN o CAJA
    
    NOTA: El stock no se puede modificar directamente, usa los endpoints de movimientos.
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.id_repuesto == id_repuesto
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {id_repuesto} no encontrado"
        )
    
    # Verificar código duplicado si se está cambiando
    if repuesto_update.codigo and repuesto_update.codigo.upper() != repuesto.codigo:
        codigo_existente = db.query(Repuesto).filter(
            Repuesto.codigo == repuesto_update.codigo.upper()
        ).first()
        
        if codigo_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un repuesto con el código '{repuesto_update.codigo}'"
            )
    
    # Actualizar campos
    update_data = repuesto_update.model_dump(exclude_unset=True)
    stock_anterior = repuesto.stock_minimo
    
    for field, value in update_data.items():
        setattr(repuesto, field, value)
    
    db.commit()
    db.refresh(repuesto)
    
    # Si cambió el stock mínimo, verificar alertas
    if repuesto.stock_minimo != stock_anterior:
        InventarioService.verificar_alertas_stock(db, repuesto)
    
    logger.info(f"Repuesto actualizado: {repuesto.codigo} por usuario {current_user.email}")
    
    return repuesto


@router.delete("/{id_repuesto}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_repuesto(
    id_repuesto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """
    Desactiva un repuesto (soft delete).
    
    Requiere rol: ADMIN
    
    NOTA: No elimina el registro, solo lo marca como inactivo.
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.id_repuesto == id_repuesto
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {id_repuesto} no encontrado"
        )
    
    repuesto.activo = False
    db.commit()

    logger.info(f"Repuesto desactivado: {repuesto.codigo} por usuario {current_user.email}")

    return None


@router.post("/{id_repuesto}/activar", response_model=RepuestoOut)
def activar_repuesto(
    id_repuesto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Reactivar un repuesto desactivado."""
    repuesto = db.query(Repuesto).options(
        joinedload(Repuesto.categoria),
        joinedload(Repuesto.proveedor),
    ).filter(Repuesto.id_repuesto == id_repuesto).first()
    if not repuesto:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    repuesto.activo = True
    db.commit()
    db.refresh(repuesto)
    return repuesto
