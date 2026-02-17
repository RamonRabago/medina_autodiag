"""
Lógica compartida para consultas de gastos operativos.
"""
from datetime import datetime, date
from typing import Optional, Union

from sqlalchemy.orm import Session, Query
from sqlalchemy import func

from app.models.gasto_operativo import GastoOperativo

CATEGORIAS_VALIDAS = ("RENTA", "SERVICIOS", "MATERIAL", "NOMINA", "OTROS", "DEVOLUCION_VENTA")


def _parse_fecha(val: Union[str, date, datetime, None]) -> Optional[date]:
    """Parsea str (YYYY-MM-DD) o datetime a date para comparación."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        s = val.strip()[:10]
        if not s or len(s) < 10:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def query_gastos(
    db: Session,
    fecha_desde: Union[str, date, None] = None,
    fecha_hasta: Union[str, date, None] = None,
    categoria: Optional[str] = None,
    buscar: Optional[str] = None,
) -> Query:
    """
    Construye el query base de gastos con filtros aplicados.
    Usado por listado, resumen y exportación.
    """
    query = db.query(GastoOperativo)

    fd = _parse_fecha(fecha_desde)
    if fd is not None:
        query = query.filter(GastoOperativo.fecha >= fd)

    fh = _parse_fecha(fecha_hasta)
    if fh is not None:
        query = query.filter(GastoOperativo.fecha <= fh)

    if categoria and categoria.strip().upper() in CATEGORIAS_VALIDAS:
        query = query.filter(GastoOperativo.categoria == categoria.strip().upper())

    buscar_term = buscar.strip() if buscar and buscar.strip() else None
    if buscar_term:
        term = f"%{buscar_term}%"
        query = query.filter(GastoOperativo.concepto.like(term))

    return query
