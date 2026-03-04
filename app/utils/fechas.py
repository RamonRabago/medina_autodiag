"""Utilidades de fecha/hora con zona horaria para citas y comparaciones."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings


def ahora_local() -> datetime:
    """Hora actual en la zona horaria del taller (naive, para comparar con fecha_hora de citas).
    Las citas se guardan en hora local del usuario; el servidor puede estar en UTC.
    Usar esta función evita marcar citas futuras como vencidas por diferencia de zona."""
    tz = ZoneInfo(settings.TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)
