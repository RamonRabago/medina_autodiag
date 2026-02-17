"""
Lógica compartida para consultas de devoluciones al inventario.
"""
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import or_, func
from sqlalchemy.orm import Session, Query

from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.repuesto import Repuesto


def _parse_fecha(val: Union[str, datetime, None]) -> Optional[datetime]:
    """Parsea str (YYYY-MM-DD) o datetime a date para comparación."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date() if hasattr(val, "date") else val
    if isinstance(val, str):
        s = val.strip()[:10]
        if not s or len(s) < 10:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def _motivo_filter(tipo_motivo: Optional[str]):
    """Retorna el filtro de motivo según tipo_motivo."""
    if tipo_motivo == "venta":
        return MovimientoInventario.motivo.ilike("Devolución%")
    if tipo_motivo == "orden":
        return MovimientoInventario.motivo.ilike("Cancelación orden%")
    return or_(
        MovimientoInventario.motivo.ilike("Devolución%"),
        MovimientoInventario.motivo.ilike("Cancelación orden%"),
    )


def query_devoluciones(
    db: Session,
    fecha_desde: Union[str, datetime, None] = None,
    fecha_hasta: Union[str, datetime, None] = None,
    buscar: Optional[str] = None,
    tipo_motivo: Optional[str] = None,
    id_repuesto: Optional[int] = None,
) -> Query:
    """
    Construye el query base de devoluciones con filtros aplicados.
    Usado por listado y exportación.
    """
    motivo_filter = _motivo_filter(tipo_motivo)
    query = (
        db.query(MovimientoInventario)
        .filter(MovimientoInventario.tipo_movimiento == TipoMovimiento.ENTRADA)
        .filter(motivo_filter)
    )

    fd = _parse_fecha(fecha_desde)
    if fd is not None:
        query = query.filter(func.date(MovimientoInventario.fecha_movimiento) >= fd)

    fh = _parse_fecha(fecha_hasta)
    if fh is not None:
        query = query.filter(func.date(MovimientoInventario.fecha_movimiento) <= fh)

    if id_repuesto is not None:
        query = query.filter(MovimientoInventario.id_repuesto == id_repuesto)

    buscar_term = buscar.strip() if buscar and buscar.strip() else None
    if buscar_term:
        term = f"%{buscar_term}%"
        query = query.outerjoin(Repuesto, MovimientoInventario.id_repuesto == Repuesto.id_repuesto).filter(
            or_(
                Repuesto.nombre.ilike(term),
                Repuesto.codigo.ilike(term),
                MovimientoInventario.referencia.ilike(term),
                MovimientoInventario.motivo.ilike(term),
            )
        )

    return query
