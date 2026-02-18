"""
Servicio de comisiones.
Calcula y registra comisiones al quedar una venta PAGADA.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.orden_trabajo import OrdenTrabajo
from app.models.configuracion_comision import ConfiguracionComision
from app.models.comision_devengada import ComisionDevengada
from app.utils.decimal_utils import to_decimal, money_round

# Mapeo: DetalleVenta.tipo + id_orden_origen -> tipo_base comisión
# SERVICIO + id_orden_origen → MANO_OBRA (técnico)
# PRODUCTO + id_orden_origen → PARTES (técnico)
# SERVICIO + sin id_orden → SERVICIOS_VENTA (vendedor)
# PRODUCTO + sin id_orden → PRODUCTOS_VENTA (vendedor)


def _obtener_tipo_base(detalle: DetalleVenta) -> str:
    """Determina tipo_base para un detalle de venta."""
    tipo_str = detalle.tipo.value if hasattr(detalle.tipo, "value") else str(detalle.tipo)
    tiene_orden = detalle.id_orden_origen is not None
    if tipo_str == "SERVICIO":
        return "MANO_OBRA" if tiene_orden else "SERVICIOS_VENTA"
    return "PARTES" if tiene_orden else "PRODUCTOS_VENTA"


def _obtener_porcentaje(db: Session, id_usuario: int, tipo_base: str, fecha: date) -> Decimal | None:
    """Obtiene el % vigente para un usuario y tipo_base en una fecha."""
    conf = (
        db.query(ConfiguracionComision)
        .filter(
            ConfiguracionComision.id_usuario == id_usuario,
            ConfiguracionComision.tipo_base == tipo_base,
            ConfiguracionComision.vigencia_desde <= fecha,
            (ConfiguracionComision.vigencia_hasta.is_(None)) | (ConfiguracionComision.vigencia_hasta >= fecha),
            ConfiguracionComision.activo.is_(True),
        )
        .order_by(ConfiguracionComision.vigencia_desde.desc())
        .first()
    )
    return to_decimal(conf.porcentaje) if conf and conf.porcentaje else None


def _quien_cobra_por_tipo(venta: Venta, orden: OrdenTrabajo | None, tipo_base: str) -> int | None:
    """id_usuario que cobra comisión según tipo_base."""
    if tipo_base in ("MANO_OBRA", "PARTES"):
        if orden and orden.tecnico_id:
            return orden.tecnico_id
        return None  # Sin técnico, no hay comisión de mano/partes
    # SERVICIOS_VENTA, PRODUCTOS_VENTA → vendedor
    return venta.id_vendedor


def calcular_y_registrar_comisiones(db: Session, id_venta: int) -> int:
    """
    Calcula y registra comisiones para una venta PAGADA.
    Idempotente: si ya existen comisiones para esta venta, no vuelve a calcular.
    Retorna el número de líneas de comisión registradas.
    """
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        return 0
    estado = venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado)
    if estado != "PAGADA":
        return 0

    # Evitar duplicados
    ya_registradas = db.query(ComisionDevengada.id).filter(ComisionDevengada.id_venta == id_venta).first()
    if ya_registradas:
        return 0

    orden = None
    if venta.id_orden:
        orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == venta.id_orden).first()

    fecha_venta = venta.fecha.date() if venta.fecha else date.today()
    detalles = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
    contador = 0

    for det in detalles:
        base = to_decimal(det.subtotal)
        if base <= 0:
            continue
        tipo_base = _obtener_tipo_base(det)
        id_cobra = _quien_cobra_por_tipo(venta, orden, tipo_base)
        if not id_cobra:
            continue
        pct = _obtener_porcentaje(db, id_cobra, tipo_base, fecha_venta)
        if pct is None or pct <= 0:
            continue
        monto_comision = money_round(base * (pct / 100))
        if monto_comision <= 0:
            continue
        cd = ComisionDevengada(
            id_usuario=id_cobra,
            id_venta=id_venta,
            id_detalle=det.id_detalle,
            tipo_base=tipo_base,
            base_monto=base,
            porcentaje=pct,
            monto_comision=monto_comision,
            fecha_venta=fecha_venta,
        )
        db.add(cd)
        contador += 1
    return contador
