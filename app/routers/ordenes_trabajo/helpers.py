"""Helpers para órdenes de trabajo."""
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.orden_trabajo import OrdenTrabajo


def generar_numero_orden(db: Session) -> str:
    """Genera un número de orden único en formato: OT-YYYYMMDD-NNNN"""
    fecha_hoy = datetime.now()
    prefijo = f"OT-{fecha_hoy.strftime('%Y%m%d')}"
    ultima_orden = db.query(OrdenTrabajo).filter(
        OrdenTrabajo.numero_orden.like(f"{prefijo}-%")
    ).order_by(OrdenTrabajo.numero_orden.desc()).first()
    if ultima_orden:
        ultimo_num = int(ultima_orden.numero_orden.split('-')[-1])
        nuevo_num = ultimo_num + 1
    else:
        nuevo_num = 1
    return f"{prefijo}-{nuevo_num:04d}"
