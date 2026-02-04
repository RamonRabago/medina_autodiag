"""
Router para Repuestos
"""
import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.repuesto import Repuesto
from app.models.categoria_repuesto import CategoriaRepuesto
from app.models.proveedor import Proveedor
from app.models.ubicacion import Ubicacion
from app.models.registro_eliminacion_repuesto import RegistroEliminacionRepuesto
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

# Directorio de uploads (relativo a la raíz del proyecto)
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "repuestos"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE_MB = 5


@router.post("/upload-imagen")
def subir_imagen_repuesto(
    archivo: UploadFile = File(..., description="Imagen del repuesto"),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Sube una imagen para un repuesto.
    Acepta archivos desde el explorador o cámara del dispositivo.
    Retorna la URL para guardar en imagen_url.
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    contenido = archivo.file.read()
    if len(contenido) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La imagen no debe superar {MAX_SIZE_MB} MB"
        )
    nombre = f"{uuid.uuid4().hex}{ext}"
    ruta = UPLOADS_DIR / nombre
    with open(ruta, "wb") as f:
        f.write(contenido)
    url = f"/uploads/repuestos/{nombre}"
    return {"url": url}


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

    # Verificar que la ubicación existe (si se proporcionó)
    if repuesto.id_ubicacion:
        ubi = db.query(Ubicacion).filter(Ubicacion.id == repuesto.id_ubicacion).first()
        if not ubi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ubicación con ID {repuesto.id_ubicacion} no encontrada"
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
    incluir_eliminados: Optional[bool] = Query(False, description="Incluir repuestos eliminados (solo ADMIN)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista repuestos con filtros y paginación.
    Por defecto excluye repuestos marcados como eliminados (soft delete).
    """
    query = db.query(Repuesto).options(
        joinedload(Repuesto.categoria),
        joinedload(Repuesto.proveedor),
        joinedload(Repuesto.ubicacion_obj).joinedload(Ubicacion.bodega),
    )
    if not incluir_eliminados or getattr(current_user, "rol", None) != "ADMIN":
        query = query.filter(Repuesto.eliminado == False)
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
    pagina = skip // limit + 1 if limit > 0 else 1
    return {
        "repuestos": repuestos,
        "total": total,
        "total_paginas": total_paginas,
        "pagina": pagina,
        "limit": limit,
    }


@router.get("/buscar-codigo/{codigo}", response_model=RepuestoOut)
def buscar_por_codigo(
    codigo: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Busca un repuesto por su código exacto. Excluye eliminados (no se pueden agregar a ventas/órdenes).
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.codigo == codigo.upper(),
        Repuesto.eliminado == False,
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
    
    NOTA: No se puede editar un repuesto ya eliminado (solo consulta para historial).
    El stock no se puede modificar directamente, usa los endpoints de movimientos.
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.id_repuesto == id_repuesto
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {id_repuesto} no encontrado"
        )
    if getattr(repuesto, "eliminado", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede editar un repuesto eliminado. Los datos se conservan solo para historial de ventas y órdenes."
        )
    
    # Verificar que la ubicación existe (si se está cambiando)
    if repuesto_update.id_ubicacion is not None and repuesto_update.id_ubicacion:
        ubi = db.query(Ubicacion).filter(Ubicacion.id == repuesto_update.id_ubicacion).first()
        if not ubi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ubicación con ID {repuesto_update.id_ubicacion} no encontrada"
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
        if field == "id_ubicacion" and value in (None, 0, ""):
            value = None
        setattr(repuesto, field, value)
    
    db.commit()
    db.refresh(repuesto)
    
    # Si cambió el stock mínimo, verificar alertas
    if repuesto.stock_minimo != stock_anterior:
        InventarioService.verificar_alertas_stock(db, repuesto)
    
    logger.info(f"Repuesto actualizado: {repuesto.codigo} por usuario {current_user.email}")
    
    return repuesto


class EliminarRepuestoPermanenteBody(BaseModel):
    motivo: str = Field(..., min_length=10, description="Motivo de la eliminación permanente")


@router.delete("/{id_repuesto}/eliminar-permanentemente", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_repuesto_permanentemente(
    id_repuesto: int,
    body: EliminarRepuestoPermanenteBody = Body(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """
    Marca el repuesto como eliminado (soft delete).
    Deja de mostrarse en listado y en selección para ventas/órdenes nuevas,
    pero el registro se mantiene para historial y contabilidad.
    Registra auditoría en registro_eliminacion_repuesto.
    """
    repuesto = db.query(Repuesto).filter(
        Repuesto.id_repuesto == id_repuesto
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {id_repuesto} no encontrado"
        )
    if getattr(repuesto, "eliminado", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este repuesto ya está eliminado."
        )
    
    import datetime as dt
    motivo = body.motivo.strip()
    repuesto.activo = False
    repuesto.eliminado = True
    repuesto.fecha_eliminacion = dt.datetime.utcnow()
    repuesto.motivo_eliminacion = motivo
    repuesto.id_usuario_eliminacion = current_user.id_usuario
    
    datos = {
        "codigo": repuesto.codigo,
        "nombre": repuesto.nombre,
        "stock_actual": repuesto.stock_actual,
        "precio_compra": float(repuesto.precio_compra or 0),
        "precio_venta": float(repuesto.precio_venta or 0),
        "categoria_nombre": repuesto.categoria_nombre,
        "proveedor_nombre": repuesto.proveedor_nombre,
    }
    reg = RegistroEliminacionRepuesto(
        id_repuesto=id_repuesto,
        id_usuario=current_user.id_usuario,
        motivo=motivo,
        datos_repuesto=json.dumps(datos, ensure_ascii=False),
    )
    db.add(reg)
    db.commit()
    
    logger.info(f"Repuesto marcado como eliminado (soft delete): {repuesto.codigo} por {current_user.email}")
    return None


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
