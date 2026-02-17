"""
Router para Repuestos
"""
import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Body
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import or_, and_
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.repuesto import Repuesto
from app.models.repuesto_compatibilidad import RepuestoCompatibilidad
from app.models.categoria_repuesto import CategoriaRepuesto
from app.models.proveedor import Proveedor
from app.models.ubicacion import Ubicacion
from app.models.estante import Estante
from app.models.nivel import Nivel
from app.models.fila import Fila
from app.models.registro_eliminacion_repuesto import RegistroEliminacionRepuesto
from app.schemas.repuesto import (
    RepuestoCreate,
    RepuestoUpdate,
    RepuestoOut,
    RepuestoCompatibilidadCreate,
    RepuestoCompatibilidadOut,
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.utils.upload import read_file_with_limit
from app.models.usuario import Usuario
from app.models.usuario_bodega import UsuarioBodega
from app.services.inventario_service import InventarioService

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/repuestos",
    tags=["Inventario - Repuestos"]
)

# Directorio de uploads (relativo a la raíz del proyecto)
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "repuestos"
UPLOADS_COMPROBANTES = Path(__file__).resolve().parent.parent.parent / "uploads" / "comprobantes"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_COMPROBANTE = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}
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
    max_bytes = MAX_SIZE_MB * 1024 * 1024
    contenido = read_file_with_limit(archivo.file, max_bytes, MAX_SIZE_MB)
    nombre = f"{uuid.uuid4().hex}{ext}"
    ruta = UPLOADS_DIR / nombre
    with open(ruta, "wb") as f:
        f.write(contenido)
    url = f"/uploads/repuestos/{nombre}"
    return {"url": url}


@router.post("/upload-comprobante")
def subir_comprobante_repuesto(
    archivo: UploadFile = File(..., description="Imagen o PDF del comprobante (factura, recibo, orden de compra)"),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Sube imagen o PDF de comprobante para un repuesto.
    Retorna la URL para guardar en comprobante_url.
    """
    UPLOADS_COMPROBANTES.mkdir(parents=True, exist_ok=True)
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in ALLOWED_COMPROBANTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no permitido. Use: {', '.join(ALLOWED_COMPROBANTE)}"
        )
    max_bytes = MAX_SIZE_MB * 1024 * 1024
    contenido = read_file_with_limit(archivo.file, max_bytes, MAX_SIZE_MB)
    nombre = f"{uuid.uuid4().hex}{ext}"
    ruta = UPLOADS_COMPROBANTES / nombre
    with open(ruta, "wb") as f:
        f.write(contenido)
    url = f"/uploads/comprobantes/{nombre}"
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
    # Verificar si ya existe un repuesto activo con ese código (excluir eliminados para permitir reutilizar código)
    repuesto_existente = db.query(Repuesto).filter(
        Repuesto.codigo == repuesto.codigo.upper(),
        Repuesto.eliminado == False
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
    if repuesto.id_estante:
        e = db.query(Estante).filter(Estante.id == repuesto.id_estante).first()
        if not e:
            raise HTTPException(status_code=404, detail=f"Estante con ID {repuesto.id_estante} no encontrado")
    if repuesto.id_nivel:
        n = db.query(Nivel).filter(Nivel.id == repuesto.id_nivel).first()
        if not n:
            raise HTTPException(status_code=404, detail=f"Nivel con ID {repuesto.id_nivel} no encontrado")
    if repuesto.id_fila:
        f = db.query(Fila).filter(Fila.id == repuesto.id_fila).first()
        if not f:
            raise HTTPException(status_code=404, detail=f"Fila con ID {repuesto.id_fila} no encontrada")

    nuevo_repuesto = Repuesto(**repuesto.model_dump())
    db.add(nuevo_repuesto)
    db.commit()
    db.refresh(nuevo_repuesto)
    
    # Verificar alertas de stock (no bloquear creación si falla)
    try:
        InventarioService.verificar_alertas_stock(db, nuevo_repuesto)
    except Exception as e:
        logger.warning(f"Alerta stock no verificada para {nuevo_repuesto.codigo}: {e}")
    
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
    id_bodega: Optional[int] = Query(None, description="Filtrar por bodega (cubre ubicaciones y estantes)"),
    id_ubicacion: Optional[int] = Query(None, description="Filtrar por ubicación (zona/pasillo)"),
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
        joinedload(Repuesto.estante).joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega),
        joinedload(Repuesto.nivel),
        joinedload(Repuesto.fila),
    )

    # Aliases para poder filtrar por bodega tanto en ubicaciones directas como en estantes
    ubi_directa = aliased(Ubicacion)
    ubi_estante = aliased(Ubicacion)

    query = query.outerjoin(ubi_directa, Repuesto.ubicacion_obj)
    query = query.outerjoin(Estante, Repuesto.estante)
    query = query.outerjoin(ubi_estante, Estante.ubicacion)

    # Restricción por bodegas permitidas (usuarios no-ADMIN con bodegas asignadas)
    # Si el usuario tiene bodegas asignadas, solo ve repuestos en esas bodegas O sin ubicación asignada
    if getattr(current_user, "rol", None) != "ADMIN":
        ids_bodega = [r[0] for r in db.query(UsuarioBodega.id_bodega).filter(
            UsuarioBodega.id_usuario == current_user.id_usuario
        ).all()]
        if ids_bodega:
            query = query.filter(
                or_(
                    ubi_directa.id_bodega.in_(ids_bodega),
                    ubi_estante.id_bodega.in_(ids_bodega),
                    # Incluir repuestos sin ubicación física (id_ubicacion e id_estante NULL)
                    (Repuesto.id_ubicacion.is_(None) & Repuesto.id_estante.is_(None)),
                )
            )

    if not incluir_eliminados or getattr(current_user, "rol", None) != "ADMIN":
        query = query.filter(Repuesto.eliminado == False)
    if activo is not None:
        query = query.filter(Repuesto.activo == activo)
    if id_categoria is not None:
        query = query.filter(Repuesto.id_categoria == id_categoria)
    if id_proveedor is not None:
        query = query.filter(Repuesto.id_proveedor == id_proveedor)
    if id_ubicacion is not None:
        # Coincidencia por ubicación legacy (id_ubicacion en repuesto) o por ubicación del estante
        query = query.filter(
            or_(
                Repuesto.id_ubicacion == id_ubicacion,
                Estante.id_ubicacion == id_ubicacion,
            )
        )
    if id_bodega is not None:
        # Bodega puede venir de una ubicación directa o de la ubicación del estante
        # También incluir repuestos sin ubicación asignada
        query = query.filter(
            or_(
                ubi_directa.id_bodega == id_bodega,
                ubi_estante.id_bodega == id_bodega,
                (Repuesto.id_ubicacion.is_(None) & Repuesto.id_estante.is_(None)),
            )
        )
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
    repuesto = db.query(Repuesto).options(
        joinedload(Repuesto.estante).joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega),
        joinedload(Repuesto.nivel),
        joinedload(Repuesto.fila),
        joinedload(Repuesto.ubicacion_obj).joinedload(Ubicacion.bodega),
    ).filter(
        Repuesto.codigo == codigo.upper(),
        Repuesto.eliminado == False,
    ).first()
    
    if not repuesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repuesto con código '{codigo}' no encontrado"
        )
    
    return repuesto


@router.get("/{id_repuesto}/compatibilidad", response_model=List[RepuestoCompatibilidadOut])
def listar_compatibilidad_repuesto(
    id_repuesto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista vehículos compatibles con el repuesto."""
    rep = db.query(Repuesto).filter(Repuesto.id_repuesto == id_repuesto).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    comp = db.query(RepuestoCompatibilidad).filter(
        RepuestoCompatibilidad.id_repuesto == id_repuesto
    ).order_by(
        RepuestoCompatibilidad.marca,
        RepuestoCompatibilidad.modelo,
        RepuestoCompatibilidad.anio_desde,
    ).all()
    return comp


@router.post("/{id_repuesto}/compatibilidad", response_model=RepuestoCompatibilidadOut, status_code=status.HTTP_201_CREATED)
def agregar_compatibilidad_repuesto(
    id_repuesto: int,
    data: RepuestoCompatibilidadCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Agrega un vehículo compatible al repuesto."""
    rep = db.query(Repuesto).filter(Repuesto.id_repuesto == id_repuesto).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    if rep.eliminado:
        raise HTTPException(status_code=400, detail="No se puede editar compatibilidad de repuesto eliminado")
    if data.anio_desde and data.anio_hasta and data.anio_desde > data.anio_hasta:
        raise HTTPException(status_code=400, detail="anio_desde no puede ser mayor que anio_hasta")
    comp = RepuestoCompatibilidad(
        id_repuesto=id_repuesto,
        marca=data.marca.strip().title(),
        modelo=data.modelo.strip().title(),
        anio_desde=data.anio_desde,
        anio_hasta=data.anio_hasta,
        motor=data.motor.strip() if data.motor else None,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


@router.delete("/{id_repuesto}/compatibilidad/{id_compat}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_compatibilidad_repuesto(
    id_repuesto: int,
    id_compat: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """Quita un vehículo compatible del repuesto."""
    comp = db.query(RepuestoCompatibilidad).filter(
        RepuestoCompatibilidad.id == id_compat,
        RepuestoCompatibilidad.id_repuesto == id_repuesto,
    ).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Compatibilidad no encontrada")
    db.delete(comp)
    db.commit()
    return None


@router.get("/{id_repuesto}", response_model=RepuestoOut)
def obtener_repuesto(
    id_repuesto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene un repuesto específico por ID.
    """
    repuesto = db.query(Repuesto).options(
        joinedload(Repuesto.categoria),
        joinedload(Repuesto.proveedor),
        joinedload(Repuesto.ubicacion_obj).joinedload(Ubicacion.bodega),
        joinedload(Repuesto.estante).joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega),
        joinedload(Repuesto.nivel),
        joinedload(Repuesto.fila),
    ).filter(Repuesto.id_repuesto == id_repuesto).first()
    
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
    
    # Verificar ubicación legacy
    if repuesto_update.id_ubicacion is not None and repuesto_update.id_ubicacion:
        ubi = db.query(Ubicacion).filter(Ubicacion.id == repuesto_update.id_ubicacion).first()
        if not ubi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ubicación con ID {repuesto_update.id_ubicacion} no encontrada"
            )
    # Verificar estante, nivel, fila
    if repuesto_update.id_estante is not None and repuesto_update.id_estante:
        e = db.query(Estante).filter(Estante.id == repuesto_update.id_estante).first()
        if not e:
            raise HTTPException(status_code=404, detail=f"Estante con ID {repuesto_update.id_estante} no encontrado")
    if repuesto_update.id_nivel is not None and repuesto_update.id_nivel:
        n = db.query(Nivel).filter(Nivel.id == repuesto_update.id_nivel).first()
        if not n:
            raise HTTPException(status_code=404, detail=f"Nivel con ID {repuesto_update.id_nivel} no encontrado")
    if repuesto_update.id_fila is not None and repuesto_update.id_fila:
        f = db.query(Fila).filter(Fila.id == repuesto_update.id_fila).first()
        if not f:
            raise HTTPException(status_code=404, detail=f"Fila con ID {repuesto_update.id_fila} no encontrada")

    # Verificar código duplicado si se está cambiando (excluir eliminados)
    if repuesto_update.codigo and repuesto_update.codigo.upper() != repuesto.codigo:
        codigo_existente = db.query(Repuesto).filter(
            Repuesto.codigo == repuesto_update.codigo.upper(),
            Repuesto.eliminado == False
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
        if field in ("id_ubicacion", "id_estante", "id_nivel", "id_fila") and value in (None, 0, ""):
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
    codigo_original = repuesto.codigo
    # Liberar el código para permitir reutilizarlo al crear un nuevo repuesto
    repuesto.codigo = f"{repuesto.codigo}_ELIM_{repuesto.id_repuesto}"
    repuesto.activo = False
    repuesto.eliminado = True
    repuesto.fecha_eliminacion = dt.datetime.utcnow()
    repuesto.motivo_eliminacion = motivo
    repuesto.id_usuario_eliminacion = current_user.id_usuario
    
    datos = {
        "codigo": codigo_original,
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
    Desactiva un repuesto (solo activo=False).
    
    Requiere rol: ADMIN
    
    NOTA: Conserva el código para permitir reactivación con POST /{id}/activar.
    El código solo se libera al usar eliminar-permanentemente.
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

    logger.info(f"Repuesto desactivado por usuario {current_user.email}")

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
