"""
Router para Alertas y Reportes de Inventario
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.alerta_inventario import AlertaInventario, TipoAlertaInventario
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.repuesto import Repuesto
from app.models.proveedor import Proveedor
from sqlalchemy.orm import joinedload
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


@router.get("/usuarios-en-ajustes")
def listar_usuarios_en_ajustes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Lista los usuarios que han realizado ajustes de inventario (para filtro en auditoría).
    Requiere rol ADMIN o CAJA.
    """
    subq = (
        db.query(MovimientoInventario.id_usuario)
        .filter(
            MovimientoInventario.tipo_movimiento.in_([
                TipoMovimiento.AJUSTE_POSITIVO,
                TipoMovimiento.AJUSTE_NEGATIVO,
            ]),
            MovimientoInventario.id_usuario.isnot(None),
        )
        .distinct()
    )
    ids = [r[0] for r in subq.all() if r[0]]
    if not ids:
        return []
    usuarios = db.query(Usuario).filter(Usuario.id_usuario.in_(ids)).order_by(Usuario.nombre).all()
    return [{"id_usuario": u.id_usuario, "nombre": u.nombre} for u in usuarios]


@router.get("/auditoria-ajustes")
def listar_auditoria_ajustes(
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    id_usuario: Optional[int] = Query(None, description="Filtrar por usuario"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Devuelve usuarios y movimientos de ajustes en una sola petición (para modal de auditoría).
    Requiere rol ADMIN o CAJA.
    """
    from sqlalchemy import func

    # Usuarios que han hecho ajustes
    subq = (
        db.query(MovimientoInventario.id_usuario)
        .filter(
            MovimientoInventario.tipo_movimiento.in_([
                TipoMovimiento.AJUSTE_POSITIVO,
                TipoMovimiento.AJUSTE_NEGATIVO,
            ]),
            MovimientoInventario.id_usuario.isnot(None),
        )
        .distinct()
    )
    ids = [r[0] for r in subq.all() if r[0]]
    usuarios = []
    if ids:
        usrs = db.query(Usuario).filter(Usuario.id_usuario.in_(ids)).order_by(Usuario.nombre).all()
        usuarios = [{"id_usuario": u.id_usuario, "nombre": u.nombre} for u in usrs]

    # Movimientos de ajuste
    query = db.query(MovimientoInventario).filter(
        MovimientoInventario.tipo_movimiento.in_([
            TipoMovimiento.AJUSTE_POSITIVO,
            TipoMovimiento.AJUSTE_NEGATIVO,
        ])
    ).options(
        joinedload(MovimientoInventario.repuesto),
        joinedload(MovimientoInventario.usuario),
    )
    if fecha_desde:
        query = query.filter(func.date(MovimientoInventario.fecha_movimiento) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(MovimientoInventario.fecha_movimiento) <= fecha_hasta)
    if id_usuario:
        query = query.filter(MovimientoInventario.id_usuario == id_usuario)

    movimientos = query.order_by(MovimientoInventario.fecha_movimiento.desc()).limit(limit).all()

    def _serializar_mov(m):
        return {
            "id_movimiento": m.id_movimiento,
            "fecha_movimiento": m.fecha_movimiento.isoformat() if m.fecha_movimiento else None,
            "tipo_movimiento": m.tipo_movimiento.value if m.tipo_movimiento else None,
            "cantidad": m.cantidad,
            "stock_anterior": m.stock_anterior,
            "stock_nuevo": m.stock_nuevo,
            "costo_total": float(m.costo_total) if m.costo_total is not None else 0,
            "referencia": m.referencia,
            "motivo": m.motivo,
            "repuesto_nombre": m.repuesto.nombre if m.repuesto else None,
            "repuesto_codigo": m.repuesto.codigo if m.repuesto else None,
            "usuario": {"nombre": m.usuario.nombre} if m.usuario else None,
        }

    return {
        "usuarios": usuarios,
        "movimientos": [_serializar_mov(m) for m in movimientos],
    }


@router.get("/sugerencia-compra")
def listar_sugerencia_compra(
    id_proveedor: Optional[int] = Query(None, description="Filtrar por proveedor"),
    incluir_cercanos: bool = Query(False, description="Incluir productos con stock cercano al mínimo (≤120%)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Sugerencia de compra: productos con stock bajo o crítico.
    Agrupa por proveedor con cantidad sugerida (hasta stock_maximo) y costo estimado.
    Requiere rol ADMIN o CAJA.
    """
    query = db.query(Repuesto).filter(
        Repuesto.activo == True,
        Repuesto.eliminado == False,
    )
    if incluir_cercanos:
        query = query.filter(Repuesto.stock_actual <= Repuesto.stock_minimo * 1.2)
    else:
        query = query.filter(Repuesto.stock_actual < Repuesto.stock_minimo)
    if id_proveedor:
        query = query.filter(Repuesto.id_proveedor == id_proveedor)
    repuestos = query.order_by(Repuesto.id_proveedor.asc(), Repuesto.nombre.asc()).all()

    # Agrupar por proveedor
    por_proveedor = {}
    sin_proveedor = []
    for r in repuestos:
        cant_min = max(0, r.stock_minimo - r.stock_actual)
        cant_max = max(0, r.stock_maximo - r.stock_actual)
        cantidad_sugerida = cant_max if cant_max > 0 else cant_min
        precio = float(r.precio_compra or 0)
        item = {
            "id_repuesto": r.id_repuesto,
            "codigo": r.codigo,
            "nombre": r.nombre,
            "stock_actual": r.stock_actual,
            "stock_minimo": r.stock_minimo,
            "stock_maximo": r.stock_maximo,
            "cantidad_sugerida": cantidad_sugerida,
            "precio_compra": precio,
            "costo_estimado": round(precio * cantidad_sugerida, 2),
        }
        if r.id_proveedor:
            prov_nombre = r.proveedor.nombre if r.proveedor else "Proveedor"
            key = (r.id_proveedor, prov_nombre)
            if key not in por_proveedor:
                por_proveedor[key] = {"id_proveedor": r.id_proveedor, "nombre": prov_nombre, "items": [], "total_estimado": 0}
            por_proveedor[key]["items"].append(item)
            por_proveedor[key]["total_estimado"] += item["costo_estimado"]
        else:
            sin_proveedor.append(item)

    # Ordenar proveedores y armar respuesta
    grupos = []
    for (_, nom), g in sorted(por_proveedor.items(), key=lambda x: x[0][1]):
        g["total_estimado"] = round(g["total_estimado"], 2)
        grupos.append(g)
    if sin_proveedor:
        total_sin = sum(i["costo_estimado"] for i in sin_proveedor)
        grupos.append({"id_proveedor": None, "nombre": "Sin proveedor", "items": sin_proveedor, "total_estimado": round(total_sin, 2)})

    return {"grupos": grupos, "total_productos": len(repuestos)}


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
    query = db.query(AlertaInventario).join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto).filter(
        Repuesto.eliminado == False
    )
    
    if activas_solo:
        query = query.filter(AlertaInventario.activa == True)
    
    if tipo_alerta:
        query = query.filter(AlertaInventario.tipo_alerta == tipo_alerta)
    
    alertas = query.options(
        joinedload(AlertaInventario.repuesto)
    ).order_by(
        AlertaInventario.fecha_creacion.desc()
    ).offset(skip).limit(limit).all()
    
    # Incluir datos básicos del repuesto para la UI
    result = []
    for a in alertas:
        item = {
            "id_alerta": a.id_alerta,
            "id_repuesto": a.id_repuesto,
            "tipo_alerta": a.tipo_alerta,
            "mensaje": a.mensaje,
            "stock_actual": a.stock_actual,
            "stock_minimo": a.stock_minimo,
            "stock_maximo": a.stock_maximo,
            "activa": a.activa,
            "fecha_creacion": a.fecha_creacion,
            "fecha_resolucion": a.fecha_resolucion,
            "resuelto_por": a.resuelto_por,
        }
        if a.repuesto:
            item["repuesto"] = {"codigo": a.repuesto.codigo, "nombre": a.repuesto.nombre}
        else:
            item["repuesto"] = None
        result.append(item)
    return result


@router.get("/alertas/resumen", response_model=ResumenAlertas)
def resumen_alertas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene un resumen de las alertas activas.
    """
    from sqlalchemy import func
    
    # Contar alertas por tipo (solo de repuestos no eliminados)
    alertas = db.query(
        AlertaInventario.tipo_alerta,
        func.count(AlertaInventario.id_alerta).label("cantidad")
    ).join(Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto).filter(
        AlertaInventario.activa == True,
        Repuesto.eliminado == False
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
    
    # Resumen de alertas (solo de repuestos no eliminados)
    total_alertas = db.query(func.count(AlertaInventario.id_alerta)).join(
        Repuesto, AlertaInventario.id_repuesto == Repuesto.id_repuesto
    ).filter(
        AlertaInventario.activa == True,
        Repuesto.eliminado == False
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
