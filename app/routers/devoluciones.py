"""
Router para Devoluciones - movimientos de inventario por devolución
(cancelación de venta, cancelación de orden, etc.)
"""
import re
from typing import Optional, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.movimiento_inventario import MovimientoInventario
from app.models.repuesto import Repuesto
from app.services.devoluciones_service import query_devoluciones
from app.utils.roles import require_roles
from app.models.usuario import Usuario


def _serializar_devolucion(m: MovimientoInventario) -> dict[str, Any]:
    """Serializa un movimiento y deriva id_venta de referencia si falta (registros antiguos)."""
    repuesto_data = None
    if m.repuesto:
        repuesto_data = {
            "id_repuesto": m.repuesto.id_repuesto,
            "nombre": m.repuesto.nombre,
            "codigo": getattr(m.repuesto, "codigo", None),
        }
    id_venta = m.id_venta
    if id_venta is None and m.referencia:
        match = re.search(r"Venta#(\d+)", str(m.referencia))
        if match:
            id_venta = int(match.group(1))
    return {
        "id_movimiento": m.id_movimiento,
        "id_repuesto": m.id_repuesto,
        "cantidad": m.cantidad,
        "motivo": m.motivo,
        "referencia": m.referencia,
        "id_venta": id_venta,
        "fecha_movimiento": m.fecha_movimiento,
        "repuesto": repuesto_data,
    }

router = APIRouter(
    prefix="/devoluciones",
    tags=["Devoluciones"],
)


@router.get("/")
def listar_devoluciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    id_repuesto: Optional[int] = Query(None, description="Filtrar por ID de repuesto"),
    buscar: Optional[str] = Query(None, description="Buscar en repuesto (nombre/código), referencia o motivo"),
    tipo_motivo: Optional[str] = Query(
        None,
        description="Filtrar por tipo: venta (devolución por venta) u orden (cancelación de orden)",
    ),
    orden_por: Optional[str] = Query(
        "fecha",
        description="Ordenar por: fecha, repuesto, cantidad, motivo, referencia, venta",
    ),
    direccion: Optional[str] = Query("desc", description="Dirección: asc o desc"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("ADMIN", "CAJA", "TECNICO")),
):
    """
    Lista devoluciones al inventario (entradas por cancelación de venta u orden).
    Incluye movimientos con motivo: "Devolución por cancelación de venta...",
    "Devolución por actualización de venta...", "Cancelación orden...".
    """
    query = query_devoluciones(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        buscar=buscar,
        tipo_motivo=tipo_motivo,
        id_repuesto=id_repuesto,
    )

    buscar_term = buscar.strip() if buscar and buscar.strip() else None
    if not buscar_term and orden_por == "repuesto":
        query = query.outerjoin(Repuesto, MovimientoInventario.id_repuesto == Repuesto.id_repuesto)

    # Ordenamiento
    desc = direccion and str(direccion).lower() == "desc"
    col_map = {
        "fecha": MovimientoInventario.fecha_movimiento,
        "cantidad": MovimientoInventario.cantidad,
        "motivo": MovimientoInventario.motivo,
        "referencia": MovimientoInventario.referencia,
        "venta": MovimientoInventario.id_venta,
    }
    order_col = col_map.get((orden_por or "fecha").lower(), MovimientoInventario.fecha_movimiento)
    if orden_por == "repuesto":
        order_col = Repuesto.nombre
    query = query.order_by(order_col.desc() if desc else order_col.asc())

    total = query.count()
    movimientos = (
        query.options(
            joinedload(MovimientoInventario.repuesto),
            joinedload(MovimientoInventario.usuario),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "devoluciones": [_serializar_devolucion(m) for m in movimientos],
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }
