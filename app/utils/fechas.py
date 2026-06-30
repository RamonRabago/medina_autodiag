"""Utilidades de fecha/hora con zona horaria para citas y comparaciones.

Convenciones (ver docs/TIMEZONE_POLICY.md):
- Eventos de sistema (caja, pagos, ventas, auditoría): UTC naive en BD → ISO con Z en API.
- fecha_ingreso OT (TZ-1): hora local naive del taller en BD → ISO sin Z en API.
- Filtros por día calendario: 00:00–23:59:59.999 en America/Matamoros → convertidos a UTC para consulta.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.config import settings

_UTC = ZoneInfo("UTC")


def taller_tz() -> ZoneInfo:
    """Zona horaria operativa del taller (America/Matamoros por defecto)."""
    return ZoneInfo(settings.TALLER_TIMEZONE)

# TZ-1: OT creadas desde este instante (naive, hora taller) guardan fecha_ingreso como local.
# Anteriores: UTC naive legacy (Railway). Sin migración de datos históricos.
FECHA_INGRESO_LOCAL_DESDE = datetime(2026, 6, 17, 0, 0, 0)


def isoformat_utc(dt: datetime | None) -> str | None:
    """Serializa datetime UTC (naive) con sufijo Z para que el cliente muestre hora del taller.
    Para date (sin hora) retorna YYYY-MM-DD sin Z. Si se pasa None retorna None."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()  # Solo fecha, sin Z para evitar desfase de día
    naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
    s = naive.isoformat()
    if s.endswith("Z") or (len(s) >= 6 and s[-6] in "+-"):
        return s
    return s + "Z"


def utc_naive_a_taller_naive(dt: datetime) -> datetime:
    """Convierte instante UTC naive (BD) a hora local naive del taller (para export/display)."""
    naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
    return naive.replace(tzinfo=_UTC).astimezone(taller_tz()).replace(tzinfo=None)


def formatear_taller(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Formatea timestamp UTC naive como cadena en hora del taller (Excel/PDF)."""
    if dt is None:
        return ""
    local = utc_naive_a_taller_naive(dt)
    return local.strftime(fmt)


def inicio_dia_taller_utc(fecha: date) -> datetime:
    """00:00:00 del día en America/Matamoros → UTC naive para filtrar en BD."""
    inicio = datetime.combine(fecha, time.min, tzinfo=taller_tz())
    return inicio.astimezone(_UTC).replace(tzinfo=None)


def fin_dia_taller_utc(fecha: date) -> datetime:
    """23:59:59.999 del día en America/Matamoros → UTC naive para filtrar en BD."""
    fin = datetime.combine(fecha, time(23, 59, 59, 999000), tzinfo=taller_tz())
    return fin.astimezone(_UTC).replace(tzinfo=None)


def aplicar_filtro_rango_taller(columna, fecha_desde: date | None, fecha_hasta: date | None):
    """Genera condiciones SQLAlchemy para rango de fechas calendario en zona del taller."""
    condiciones = []
    if fecha_desde is not None:
        condiciones.append(columna >= inicio_dia_taller_utc(fecha_desde))
    if fecha_hasta is not None:
        condiciones.append(columna <= fin_dia_taller_utc(fecha_hasta))
    return condiciones


def parse_fecha_calendario(valor: str | date | datetime | None) -> date | None:
    """Parsea YYYY-MM-DD (o date/datetime) a date calendario del taller."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def hoy_taller() -> date:
    """Fecha calendario actual en America/Matamoros."""
    return ahora_local().date()


def condiciones_rango_taller(columna, fecha_desde: str | date | datetime | None, fecha_hasta: str | date | datetime | None):
    """Atajo: params de query string → condiciones SQLAlchemy para eventos UTC en BD."""
    return aplicar_filtro_rango_taller(
        columna,
        parse_fecha_calendario(fecha_desde),
        parse_fecha_calendario(fecha_hasta),
    )


def condiciones_rango_fecha_solo(columna, fecha_desde: str | date | datetime | None, fecha_hasta: str | date | datetime | None):
    """Rango calendario sobre columna Date (sin hora): gastos, comisiones, etc."""
    condiciones = []
    desde = parse_fecha_calendario(fecha_desde)
    hasta = parse_fecha_calendario(fecha_hasta)
    if desde is not None:
        condiciones.append(columna >= desde)
    if hasta is not None:
        condiciones.append(columna <= hasta)
    return condiciones


def inicio_dia_taller_naive(fecha: date) -> datetime:
    """00:00:00 naive — wall-clock America/Matamoros (citas, TZ-1)."""
    return datetime.combine(fecha, time.min)


def fin_dia_taller_naive(fecha: date) -> datetime:
    """23:59:59.999 naive — wall-clock America/Matamoros (citas, TZ-1)."""
    return datetime.combine(fecha, time(23, 59, 59, 999000))


def condiciones_rango_local_naive(
    columna,
    fecha_desde: str | date | datetime | None,
    fecha_hasta: str | date | datetime | None,
):
    """Filtro por día calendario para datetime naive local del taller (citas)."""
    condiciones = []
    desde = parse_fecha_calendario(fecha_desde)
    hasta = parse_fecha_calendario(fecha_hasta)
    if desde is not None:
        condiciones.append(columna >= inicio_dia_taller_naive(desde))
    if hasta is not None:
        condiciones.append(columna <= fin_dia_taller_naive(hasta))
    return condiciones


def isoformat_local_naive_taller(dt: datetime | None) -> str | None:
    """Wall-clock local del taller (citas): ISO sin Z. No usar para eventos UTC."""
    return isoformat_fecha_ingreso_ot(dt)


def ingreso_ot_en_dia_taller(columna, dia: date | None = None):
    """SQLAlchemy: fecha_ingreso OT cae en el día calendario Matamoros (TZ-1 + legacy UTC)."""
    from sqlalchemy import and_, or_

    ref = dia if dia is not None else hoy_taller()
    legacy = and_(
        columna < FECHA_INGRESO_LOCAL_DESDE,
        columna >= inicio_dia_taller_utc(ref),
        columna <= fin_dia_taller_utc(ref),
    )
    tz1 = and_(
        columna >= FECHA_INGRESO_LOCAL_DESDE,
        columna >= inicio_dia_taller_naive(ref),
        columna <= fin_dia_taller_naive(ref),
    )
    return or_(legacy, tz1)


def ahora_local() -> datetime:
    """Hora actual en la zona horaria del taller (naive, para comparar con fecha_hora de citas).
    Las citas se guardan en hora local del usuario; el servidor puede estar en UTC.
    Usar esta función evita marcar citas futuras como vencidas por diferencia de zona."""
    tz = ZoneInfo(settings.TALLER_TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)


def ahora_local_naive() -> datetime:
    """Alias TZ-1: hora local naive del taller para persistir fecha_ingreso en OT."""
    return ahora_local()


def isoformat_fecha_ingreso_ot(dt: datetime | None) -> str | None:
    """Serializa fecha_ingreso OT: naive hora local del taller, sin sufijo Z (convención TZ-1)."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()
    naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
    return naive.isoformat()


MSG_FECHA_PROMESA_ANTERIOR_INGRESO = "La fecha promesa no puede ser anterior a la fecha de ingreso"


def ingreso_ot_utc_naive_a_local_naive(ingreso: datetime) -> datetime:
    """Convierte fecha_ingreso legacy (UTC naive en Railway/prod) a hora local naive del taller."""
    tz = ZoneInfo(settings.TALLER_TIMEZONE)
    ingreso_n = ingreso.replace(tzinfo=None) if ingreso.tzinfo else ingreso
    return ingreso_n.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).replace(tzinfo=None)


def ingreso_ot_a_local_naive(ingreso: datetime) -> datetime:
    """Normaliza fecha_ingreso a hora local del taller (TZ-1 local o legacy UTC)."""
    ingreso_n = ingreso.replace(tzinfo=None) if ingreso.tzinfo else ingreso
    if ingreso_n >= FECHA_INGRESO_LOCAL_DESDE:
        return ingreso_n
    return ingreso_ot_utc_naive_a_local_naive(ingreso_n)


def validar_fecha_promesa_vs_ingreso(
    fecha_promesa: datetime | None,
    fecha_ingreso: datetime | None,
) -> None:
    """
    Valida que fecha_promesa (local naive desde datetime-local) no sea anterior a fecha_ingreso.
    TZ-1: fecha_ingreso >= FECHA_INGRESO_LOCAL_DESDE ya es local naive del taller.
    Legacy: valores anteriores se interpretan como UTC naive (Railway).
    """
    if not fecha_promesa or not fecha_ingreso:
        return
    promesa = fecha_promesa.replace(tzinfo=None) if fecha_promesa.tzinfo else fecha_promesa
    ingreso_local = ingreso_ot_a_local_naive(fecha_ingreso)
    if promesa < ingreso_local:
        raise ValueError(MSG_FECHA_PROMESA_ANTERIOR_INGRESO)
