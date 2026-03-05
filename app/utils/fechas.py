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
