"""
Contexto de fechas para citas: hora local del taller (TIMEZONE) vs validaciones.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.utils.fechas import ahora_local


def test_ahora_local_es_naive():
    """Las citas comparan naive con naive; no debe colgar tzinfo."""
    ahora = ahora_local()
    assert ahora.tzinfo is None


def test_ahora_local_coincide_con_zoneinfo_taller():
    """Debe igualar datetime.now(TIMEZONE) sin tzinfo (misma lógica que fechas.py)."""
    tz = ZoneInfo(settings.TIMEZONE)
    esperado = datetime.now(tz).replace(tzinfo=None)
    obtenido = ahora_local()
    diff_sec = abs((obtenido - esperado).total_seconds())
    assert diff_sec < 3.0


def test_fecha_pasada_es_menor_o_igual_que_ahora_local():
    """Una cita \"ayer\" debe fallar la regla fecha_hora <= ahora_local() (crear/actualizar)."""
    ayer = ahora_local() - timedelta(days=1)
    assert ayer <= ahora_local()


def test_fecha_manana_es_posterior_a_ahora_local():
    manana = ahora_local() + timedelta(days=1)
    assert manana > ahora_local()
