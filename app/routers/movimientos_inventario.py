"""
Router para Movimientos de Inventario
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.repuesto import Repuesto
from app.schemas.movimiento_inventario import (
    MovimientoInventarioCreate,
    MovimientoInventarioOut,
    AjusteInventario
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario
from app.services.inventario_service import InventarioService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inventario/movimientos",
    tags=["Inventario - Movimientos"]
)

UPLOADS_COMPROBANTES = Path(__file__).resolve().parent.parent.parent / "uploads" / "comprobantes"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}
MAX_SIZE_MB = 5


@router.post("/upload-comprobante")
def subir_comprobante(
    archivo: UploadFile = File(..., description="Imagen o PDF del comprobante de compra"),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA", "TECNICO"))
):
    """Sube imagen o PDF de comprobante (factura, recibo). Retorna la URL."""
    UPLOADS_COMPROBANTES.mkdir(parents=True, exist_ok=True)
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no permitido. Use: {', '.join(ALLOWED_EXT)}"
        )
    contenido = archivo.file.read()
    if len(contenido) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo no debe superar {MAX_SIZE_MB} MB"
        )
    nombre = f"{uuid.uuid4().hex}{ext}"
    ruta = UPLOADS_COMPROBANTES / nombre
    with open(ruta, "wb") as f:
        f.write(contenido)
    url = f"/uploads/comprobantes/{nombre}"
    return {"url": url}


@router.post("/", response_model=MovimientoInventarioOut, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(
    movimiento: MovimientoInventarioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA", "TECNICO"))
):
    """
    Registra un movimiento de inventario (entrada, salida, merma, etc.).
    
    Requiere rol: ADMIN, CAJA o TECNICO
    
    Tipos de movimiento:
    - ENTRADA: Compra o devolución
    - SALIDA: Venta o uso en servicio
    - AJUSTE+: Corrección al alza
    - AJUSTE-: Corrección a la baja
    - MERMA: Pérdida o daño
    """
    try:
        nuevo_movimiento = InventarioService.registrar_movimiento(
            db=db,
            movimiento=movimiento,
            id_usuario=current_user.id_usuario
        )
        
        return nuevo_movimiento
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al registrar movimiento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar el movimiento de inventario"
        )


@router.post("/ajuste", response_model=MovimientoInventarioOut, status_code=status.HTTP_201_CREATED)
def ajustar_inventario(
    ajuste: AjusteInventario,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Ajusta el inventario a un valor específico.
    
    Requiere rol: ADMIN o CAJA
    
    Útil para correcciones de inventario físico.
    """
    try:
        movimiento_ajuste = InventarioService.ajustar_inventario(
            db=db,
            ajuste=ajuste,
            id_usuario=current_user.id_usuario
        )
        
        return movimiento_ajuste
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al ajustar inventario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al ajustar el inventario"
        )


@router.get("/")
def listar_movimientos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    id_repuesto: Optional[int] = Query(None, description="Filtrar por repuesto"),
    tipo_movimiento: Optional[TipoMovimiento] = Query(None, description="Filtrar por tipo"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    id_usuario: Optional[int] = Query(None, description="Filtrar por usuario"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los movimientos de inventario con filtros opcionales.
    
    Filtros disponibles:
    - id_repuesto: Movimientos de un repuesto específico
    - tipo_movimiento: ENTRADA, SALIDA, AJUSTE+, AJUSTE-, MERMA
    - fecha_desde: Movimientos desde esta fecha
    - fecha_hasta: Movimientos hasta esta fecha
    - id_usuario: Movimientos realizados por un usuario
    """
    query = db.query(MovimientoInventario)
    
    # Aplicar filtros
    if id_repuesto:
        query = query.filter(MovimientoInventario.id_repuesto == id_repuesto)
    
    if tipo_movimiento:
        query = query.filter(MovimientoInventario.tipo_movimiento == tipo_movimiento)
    
    if fecha_desde:
        query = query.filter(MovimientoInventario.fecha_movimiento >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(MovimientoInventario.fecha_movimiento <= fecha_hasta)
    
    if id_usuario:
        query = query.filter(MovimientoInventario.id_usuario == id_usuario)
    
    # Ordenar por fecha descendente
    total = query.count()
    movimientos = query.order_by(
        MovimientoInventario.fecha_movimiento.desc()
    ).offset(skip).limit(limit).all()

    return {
        "movimientos": movimientos,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.get("/repuesto/{id_repuesto}", response_model=List[MovimientoInventarioOut])
def historial_repuesto(
    id_repuesto: int,
    limite: int = Query(50, le=200, description="Número máximo de registros"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el historial completo de movimientos de un repuesto específico.
    """
    # Verificar que el repuesto existe
    repuesto = db.query(Repuesto).filter(
        Repuesto.id_repuesto == id_repuesto
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con ID {id_repuesto} no encontrado"
        )
    
    movimientos = db.query(MovimientoInventario).filter(
        MovimientoInventario.id_repuesto == id_repuesto
    ).order_by(
        MovimientoInventario.fecha_movimiento.desc()
    ).limit(limite).all()
    
    return movimientos


@router.get("/{id_movimiento}", response_model=MovimientoInventarioOut)
def obtener_movimiento(
    id_movimiento: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene los detalles de un movimiento específico.
    """
    movimiento = db.query(MovimientoInventario).filter(
        MovimientoInventario.id_movimiento == id_movimiento
    ).first()
    
    if not movimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movimiento con ID {id_movimiento} no encontrado"
        )
    
    return movimiento


@router.get("/estadisticas/resumen")
def obtener_estadisticas_movimientos(
    fecha_desde: Optional[datetime] = Query(None),
    fecha_hasta: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Obtiene estadísticas de movimientos de inventario.
    
    Requiere rol: ADMIN o CAJA
    """
    from sqlalchemy import func
    
    query = db.query(
        MovimientoInventario.tipo_movimiento,
        func.count(MovimientoInventario.id_movimiento).label("total_movimientos"),
        func.sum(MovimientoInventario.cantidad).label("total_cantidad"),
        func.sum(MovimientoInventario.costo_total).label("total_costo")
    )
    
    if fecha_desde:
        query = query.filter(MovimientoInventario.fecha_movimiento >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(MovimientoInventario.fecha_movimiento <= fecha_hasta)
    
    estadisticas = query.group_by(
        MovimientoInventario.tipo_movimiento
    ).all()
    
    resultado = {
        "periodo": {
            "desde": fecha_desde.isoformat() if fecha_desde else None,
            "hasta": fecha_hasta.isoformat() if fecha_hasta else None
        },
        "por_tipo": [
            {
                "tipo": stat.tipo_movimiento,
                "total_movimientos": stat.total_movimientos,
                "total_cantidad": stat.total_cantidad,
                "total_costo": float(stat.total_costo) if stat.total_costo else 0
            }
            for stat in estadisticas
        ]
    }
    
    return resultado
