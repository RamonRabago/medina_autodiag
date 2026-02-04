"""
Router para Alertas y Reportes de Inventario
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.alerta_inventario import AlertaInventario, TipoAlertaInventario
from app.models.repuesto import Repuesto
from app.schemas.alerta_inventario import (
    AlertaInventarioOut,
    ResumenAlertas
)
from app.utils.dependencies import get_current_user
from app.utils.roles import require_roles
from app.models.usuario import Usuario
from app.services.inventario_service import InventarioService
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inventario",
    tags=["Inventario - Reportes"]
)


# ========== ALERTAS ==========

@router.get("/alertas", response_model=List[AlertaInventarioOut])
def listar_alertas(
    activas_solo: bool = Query(True, description="Solo alertas activas"),
    tipo_alerta: Optional[TipoAlertaInventario] = Query(None, description="Filtrar por tipo"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todas las alertas de inventario.
    
    Filtros:
    - activas_solo: Solo alertas activas (default: true)
    - tipo_alerta: STOCK_BAJO, STOCK_CRITICO, SIN_STOCK, etc.
    """
    query = db.query(AlertaInventario)
    
    if activas_solo:
        query = query.filter(AlertaInventario.activa == True)
    
    if tipo_alerta:
        query = query.filter(AlertaInventario.tipo_alerta == tipo_alerta)
    
    alertas = query.order_by(
        AlertaInventario.fecha_creacion.desc()
    ).offset(skip).limit(limit).all()
    
    return alertas


@router.get("/alertas/resumen", response_model=ResumenAlertas)
def resumen_alertas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene un resumen de las alertas activas.
    """
    from sqlalchemy import func
    
    # Contar alertas por tipo
    alertas = db.query(
        AlertaInventario.tipo_alerta,
        func.count(AlertaInventario.id_alerta).label("cantidad")
    ).filter(
        AlertaInventario.activa == True
    ).group_by(
        AlertaInventario.tipo_alerta
    ).all()
    
    resumen = {
        "total_alertas": 0,
        "alertas_criticas": 0,
        "alertas_stock_bajo": 0,
        "alertas_sin_stock": 0,
        "alertas_sin_movimiento": 0,
        "alertas_sobre_stock": 0
    }
    
    for alerta in alertas:
        resumen["total_alertas"] += alerta.cantidad
        
        if alerta.tipo_alerta == TipoAlertaInventario.STOCK_CRITICO:
            resumen["alertas_criticas"] = alerta.cantidad
        elif alerta.tipo_alerta == TipoAlertaInventario.STOCK_BAJO:
            resumen["alertas_stock_bajo"] = alerta.cantidad
        elif alerta.tipo_alerta == TipoAlertaInventario.SIN_STOCK:
            resumen["alertas_sin_stock"] = alerta.cantidad
        elif alerta.tipo_alerta == TipoAlertaInventario.SIN_MOVIMIENTO:
            resumen["alertas_sin_movimiento"] = alerta.cantidad
        elif alerta.tipo_alerta == TipoAlertaInventario.SOBRE_STOCK:
            resumen["alertas_sobre_stock"] = alerta.cantidad
    
    return resumen


@router.post("/alertas/{id_alerta}/resolver", status_code=status.HTTP_200_OK)
def resolver_alerta(
    id_alerta: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Marca una alerta como resuelta manualmente.
    
    Requiere rol: ADMIN o CAJA
    """
    alerta = db.query(AlertaInventario).filter(
        AlertaInventario.id_alerta == id_alerta
    ).first()
    
    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta con ID {id_alerta} no encontrada"
        )
    
    if not alerta.activa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La alerta ya está resuelta"
        )
    
    alerta.activa = False
    alerta.fecha_resolucion = datetime.utcnow()
    alerta.resuelto_por = current_user.id_usuario
    db.commit()
    
    logger.info(f"Alerta {id_alerta} resuelta manualmente por {current_user.email}")
    
    return {
        "mensaje": "Alerta resuelta exitosamente",
        "id_alerta": id_alerta
    }


@router.post("/alertas/verificar-sin-movimiento", status_code=status.HTTP_200_OK)
def verificar_productos_sin_movimiento(
    dias: int = Query(90, ge=1, le=365, description="Días sin movimiento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN"))
):
    """
    Verifica y crea alertas para productos sin movimiento.
    
    Requiere rol: ADMIN
    """
    InventarioService.verificar_productos_sin_movimiento(db, dias)
    
    return {
        "mensaje": f"Verificación completada para productos sin movimiento en {dias} días"
    }


# ========== REPORTES ==========

@router.get("/reportes/valor-inventario")
def reporte_valor_inventario(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Calcula el valor total del inventario.
    
    Requiere rol: ADMIN o CAJA
    """
    valor = InventarioService.calcular_valor_inventario(db)
    
    return {
        "fecha_reporte": datetime.utcnow().isoformat(),
        **valor
    }


@router.get("/reportes/productos-mas-vendidos")
def reporte_productos_mas_vendidos(
    limite: int = Query(10, ge=1, le=50, description="Número de productos"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Lista los productos más vendidos.
    
    Requiere rol: ADMIN o CAJA
    """
    productos = InventarioService.obtener_productos_mas_vendidos(db, limite)
    
    return {
        "fecha_reporte": datetime.utcnow().isoformat(),
        "productos": productos
    }


@router.get("/reportes/stock-bajo")
def reporte_stock_bajo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista todos los productos con stock bajo o crítico.
    """
    productos_stock_bajo = db.query(Repuesto).filter(
        Repuesto.activo == True,
        Repuesto.eliminado == False,
        Repuesto.stock_actual <= Repuesto.stock_minimo
    ).order_by(
        Repuesto.stock_actual.asc()
    ).all()
    
    resultado = []
    for producto in productos_stock_bajo:
        resultado.append({
            "id_repuesto": producto.id_repuesto,
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "stock_actual": producto.stock_actual,
            "stock_minimo": producto.stock_minimo,
            "diferencia": producto.stock_minimo - producto.stock_actual,
            "precio_compra": float(producto.precio_compra),
            "costo_reposicion": float(producto.precio_compra * (producto.stock_minimo - producto.stock_actual))
        })
    
    return {
        "fecha_reporte": datetime.utcnow().isoformat(),
        "total_productos": len(resultado),
        "productos": resultado
    }


@router.get("/reportes/rotacion-inventario")
def reporte_rotacion_inventario(
    dias: int = Query(30, ge=1, le=365, description="Período en días"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Calcula la rotación de inventario por producto.
    
    Requiere rol: ADMIN o CAJA
    """
    from sqlalchemy import func
    from datetime import timedelta
    from app.models.movimiento_inventario import TipoMovimiento
    
    fecha_inicio = datetime.utcnow() - timedelta(days=dias)
    
    # Obtener ventas por producto en el período
    ventas = db.query(
        Repuesto.id_repuesto,
        Repuesto.codigo,
        Repuesto.nombre,
        Repuesto.stock_actual,
        func.sum(MovimientoInventario.cantidad).label("cantidad_vendida")
    ).join(
        MovimientoInventario,
        Repuesto.id_repuesto == MovimientoInventario.id_repuesto
    ).filter(
        MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
        MovimientoInventario.fecha_movimiento >= fecha_inicio,
        Repuesto.activo == True,
        Repuesto.eliminado == False
    ).group_by(
        Repuesto.id_repuesto
    ).all()
    
    resultado = []
    for venta in ventas:
        if venta.stock_actual > 0:
            rotacion = (venta.cantidad_vendida / venta.stock_actual) * (30 / dias)  # Normalizado a 30 días
        else:
            rotacion = 0
        
        resultado.append({
            "id_repuesto": venta.id_repuesto,
            "codigo": venta.codigo,
            "nombre": venta.nombre,
            "stock_actual": venta.stock_actual,
            "cantidad_vendida": venta.cantidad_vendida,
            "rotacion_mensual": round(rotacion, 2),
            "velocidad": "Alta" if rotacion > 2 else "Media" if rotacion > 0.5 else "Baja"
        })
    
    # Ordenar por rotación descendente
    resultado.sort(key=lambda x: x["rotacion_mensual"], reverse=True)
    
    return {
        "fecha_reporte": datetime.utcnow().isoformat(),
        "periodo_dias": dias,
        "total_productos": len(resultado),
        "productos": resultado
    }


@router.get("/reportes/dashboard")
def dashboard_inventario(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA"))
):
    """
    Dashboard con métricas clave de inventario.
    
    Requiere rol: ADMIN o CAJA
    """
    from sqlalchemy import func
    
    # Valor del inventario
    valor_inventario = InventarioService.calcular_valor_inventario(db)
    
    # Resumen de alertas
    total_alertas = db.query(func.count(AlertaInventario.id_alerta)).filter(
        AlertaInventario.activa == True
    ).scalar()
    
    # Productos sin stock (solo no eliminados)
    sin_stock = db.query(func.count(Repuesto.id_repuesto)).filter(
        Repuesto.activo == True,
        Repuesto.eliminado == False,
        Repuesto.stock_actual == 0
    ).scalar()
    
    # Productos con stock bajo
    stock_bajo = db.query(func.count(Repuesto.id_repuesto)).filter(
        Repuesto.activo == True,
        Repuesto.eliminado == False,
        Repuesto.stock_actual <= Repuesto.stock_minimo,
        Repuesto.stock_actual > 0
    ).scalar()
    
    # Total de productos activos (no eliminados)
    total_productos = db.query(func.count(Repuesto.id_repuesto)).filter(
        Repuesto.activo == True,
        Repuesto.eliminado == False
    ).scalar()
    
    return {
        "fecha_reporte": datetime.utcnow().isoformat(),
        "metricas": {
            "valor_inventario": valor_inventario,
            "productos_activos": total_productos,
            "productos_sin_stock": sin_stock,
            "productos_stock_bajo": stock_bajo,
            "total_alertas": total_alertas
        }
    }
