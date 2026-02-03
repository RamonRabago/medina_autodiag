# app/routers/servicios.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.servicio import Servicio
from app.schemas.servicio_schema import (
    ServicioCreate, ServicioUpdate, ServicioResponse, ServicioListResponse
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario
import logging

router = APIRouter(prefix="/servicios", tags=["Órdenes - Servicios"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=ServicioResponse, status_code=status.HTTP_201_CREATED)
def crear_servicio(
    servicio_data: ServicioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN"]))
):
    """
    Crear un nuevo servicio en el catálogo
    - **Solo ADMIN**
    """
    logger.info(f"Usuario {current_user.email} creando servicio: {servicio_data.nombre}")
    
    # Verificar que el código no exista
    servicio_existente = db.query(Servicio).filter(Servicio.codigo == servicio_data.codigo).first()
    if servicio_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un servicio con el código '{servicio_data.codigo}'"
        )
    
    # Crear servicio
    nuevo_servicio = Servicio(**servicio_data.model_dump())
    db.add(nuevo_servicio)
    db.commit()
    db.refresh(nuevo_servicio)
    
    logger.info(f"Servicio creado exitosamente: {nuevo_servicio.codigo}")
    return nuevo_servicio

@router.get("/", response_model=ServicioListResponse)
def listar_servicios(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    activo: Optional[bool] = Query(None, description="Filtrar por servicios activos/inactivos"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    buscar: Optional[str] = Query(None, description="Buscar en código o nombre"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar todos los servicios del catálogo con filtros opcionales
    """
    query = db.query(Servicio)
    
    # Filtros
    if activo is not None:
        query = query.filter(Servicio.activo == activo)
    
    if categoria:
        query = query.filter(Servicio.categoria == categoria)
    
    if buscar:
        buscar_pattern = f"%{buscar}%"
        query = query.filter(
            (Servicio.codigo.like(buscar_pattern)) |
            (Servicio.nombre.like(buscar_pattern))
        )
    
    total = query.count()
    servicios = query.offset(skip).limit(limit).all()
    
    return {
        "servicios": servicios,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1
    }

@router.get("/{servicio_id}", response_model=ServicioResponse)
def obtener_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener detalles de un servicio específico
    """
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {servicio_id} no encontrado"
        )
    
    return servicio

@router.put("/{servicio_id}", response_model=ServicioResponse)
def actualizar_servicio(
    servicio_id: int,
    servicio_data: ServicioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN"]))
):
    """
    Actualizar un servicio existente
    - **Solo ADMIN**
    """
    logger.info(f"Usuario {current_user.email} actualizando servicio ID: {servicio_id}")
    
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {servicio_id} no encontrado"
        )
    
    # Verificar código único si se está actualizando
    if servicio_data.codigo and servicio_data.codigo != servicio.codigo:
        codigo_existente = db.query(Servicio).filter(
            Servicio.codigo == servicio_data.codigo,
            Servicio.id != servicio_id
        ).first()
        if codigo_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro servicio con el código '{servicio_data.codigo}'"
            )
    
    # Actualizar solo los campos proporcionados
    update_data = servicio_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(servicio, field, value)
    
    db.commit()
    db.refresh(servicio)
    
    logger.info(f"Servicio actualizado: {servicio.codigo}")
    return servicio

@router.delete("/{servicio_id}", status_code=status.HTTP_200_OK)
def eliminar_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN"]))
):
    """
    Desactivar un servicio (soft delete)
    - **Solo ADMIN**
    """
    logger.info(f"Usuario {current_user.email} desactivando servicio ID: {servicio_id}")
    
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {servicio_id} no encontrado"
        )
    
    # Soft delete - solo desactivar
    servicio.activo = False
    db.commit()
    
    logger.info(f"Servicio desactivado: {servicio.codigo}")
    return {"message": f"Servicio '{servicio.nombre}' desactivado exitosamente"}

@router.post("/{servicio_id}/activar", response_model=ServicioResponse)
def activar_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["ADMIN"]))
):
    """
    Reactivar un servicio desactivado
    - **Solo ADMIN**
    """
    logger.info(f"Usuario {current_user.email} reactivando servicio ID: {servicio_id}")
    
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {servicio_id} no encontrado"
        )
    
    servicio.activo = True
    db.commit()
    db.refresh(servicio)
    
    logger.info(f"Servicio reactivado: {servicio.codigo}")
    return servicio

@router.get("/categorias/listar")
def listar_categorias(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar todas las categorías de servicios disponibles
    """
    categorias = [
        {"valor": "MANTENIMIENTO", "nombre": "Mantenimiento"},
        {"valor": "REPARACION", "nombre": "Reparación"},
        {"valor": "DIAGNOSTICO", "nombre": "Diagnóstico"},
        {"valor": "ELECTRICIDAD", "nombre": "Electricidad"},
        {"valor": "SUSPENSION", "nombre": "Suspensión"},
        {"valor": "FRENOS", "nombre": "Frenos"},
        {"valor": "MOTOR", "nombre": "Motor"},
        {"valor": "TRANSMISION", "nombre": "Transmisión"},
        {"valor": "AIRE_ACONDICIONADO", "nombre": "Aire Acondicionado"},
        {"valor": "CARROCERIA", "nombre": "Carrocería"},
        {"valor": "OTROS", "nombre": "Otros"}
    ]
    return {"categorias": categorias}
