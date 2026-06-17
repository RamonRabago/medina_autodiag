"""Utilidades de fecha/hora con zona horaria para citas y comparaciones."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings

# TZ-1: OT creadas desde este instante (naive, hora taller) guardan fecha_ingreso como local.
# Anteriores: UTC naive legacy (Railway). Sin migración de datos históricos.
FECHA_INGRESO_LOCAL_DESDE = datetime(2026, 6, 17, 0, 0, 0)


def isoformat_utc(dt: datetime | None) -> str | None:
    """Serializa datetime UTC (naive) con sufijo Z para que el cliente (JS) muestre hora local correcta.
    Para date (sin hora) retorna YYYY-MM-DD sin Z. Si se pasa None retorna None."""
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()  # Solo fecha, sin Z para evitar desfase de día
    s = dt.isoformat()
    if s.endswith("Z") or (len(s) >= 6 and s[-6] in "+-"):
        return s
    return s + "Z"


def ahora_local() -> datetime:
    """Hora actual en la zona horaria del taller (naive, para comparar con fecha_hora de citas).
    Las citas se guardan en hora local del usuario; el servidor puede estar en UTC.
    Usar esta función evita marcar citas futuras como vencidas por diferencia de zona."""
    tz = ZoneInfo(settings.TIMEZONE)
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
    tz = ZoneInfo(settings.TIMEZONE)
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
