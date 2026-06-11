"""Helpers para órdenes de trabajo."""

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.orden_trabajo import OrdenTrabajo

MSG_ORDEN_SIN_ITEMS = (
    "La orden debe tener al menos un servicio o repuesto antes de continuar. "
    "Agréguelos desde el detalle de la orden."
)


def orden_tiene_servicios_o_repuestos(orden: OrdenTrabajo) -> bool:
    """True si la OT tiene al menos un servicio o repuesto registrado."""
    n_serv = len(orden.detalles_servicio or [])
    n_rep = len(orden.detalles_repuesto or [])
    return n_serv > 0 or n_rep > 0


def generar_numero_orden(db: Session) -> str:
    """Genera un número de orden único en formato: OT-YYYYMMDD-NNNN.
    Bloquea la última orden con FOR UPDATE para serializar creación bajo concurrencia.
    """
    fecha_hoy = datetime.now()
    prefijo = f"OT-{fecha_hoy.strftime('%Y%m%d')}"
    # Bloquear la última orden del día (o la más reciente si no hay del día)
    ultima_orden = (
        db.query(OrdenTrabajo)
        .filter(OrdenTrabajo.numero_orden.like(f"{prefijo}-%"))
        .order_by(desc(OrdenTrabajo.numero_orden))
        .with_for_update()
        .first()
    )
    if ultima_orden:
        ultimo_num = int(ultima_orden.numero_orden.split('-')[-1])
        nuevo_num = ultimo_num + 1
    else:
        # Sin órdenes hoy: bloquear última orden global para serializar
        _ = db.query(OrdenTrabajo).order_by(desc(OrdenTrabajo.id)).limit(1).with_for_update().first()
        nuevo_num = 1
    return f"{prefijo}-{nuevo_num:04d}"
