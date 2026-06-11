"""Utilidades de fecha/hora con zona horaria para citas y comparaciones."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings


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


MSG_FECHA_PROMESA_ANTERIOR_INGRESO = "La fecha promesa no puede ser anterior a la fecha de ingreso"


def ingreso_ot_utc_naive_a_local_naive(ingreso: datetime) -> datetime:
    """Convierte fecha_ingreso legacy (UTC naive en Railway/prod) a hora local naive del taller."""
    tz = ZoneInfo(settings.TIMEZONE)
    return ingreso.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).replace(tzinfo=None)


def validar_fecha_promesa_vs_ingreso(
    fecha_promesa: datetime | None,
    fecha_ingreso: datetime | None,
) -> None:
    """
    Valida que fecha_promesa (local naive desde datetime-local) no sea anterior a fecha_ingreso.
    fecha_ingreso en BD se interpreta como UTC naive (legacy prod).
    """
    if not fecha_promesa or not fecha_ingreso:
        return
    promesa = fecha_promesa.replace(tzinfo=None) if fecha_promesa.tzinfo else fecha_promesa
    ingreso_local = ingreso_ot_utc_naive_a_local_naive(fecha_ingreso)
    if promesa < ingreso_local:
        raise ValueError(MSG_FECHA_PROMESA_ANTERIOR_INGRESO)
