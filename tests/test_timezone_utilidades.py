"""Utilidades centralizadas de timezone (America/Matamoros)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.utils.fechas import (
    aplicar_filtro_rango_taller,
    fin_dia_taller_utc,
    formatear_taller,
    inicio_dia_taller_utc,
    ingreso_ot_en_dia_taller,
    isoformat_utc,
    utc_naive_a_taller_naive,
)


def test_isoformat_utc_agrega_z():
    assert isoformat_utc(datetime(2026, 6, 30, 13, 39, 35)) == "2026-06-30T13:39:35Z"


def test_isoformat_utc_none():
    assert isoformat_utc(None) is None


def test_matamoros_verano_utc_a_local():
    """13:39 UTC → 08:39 Matamoros (CDT, UTC-5) en junio."""
    utc = datetime(2026, 6, 30, 13, 39, 35)
    local = utc_naive_a_taller_naive(utc)
    assert local.hour == 8 and local.minute == 39


def test_formatear_taller_desde_utc():
    utc = datetime(2026, 6, 30, 13, 39, 35)
    assert formatear_taller(utc) == "2026-06-30 08:39"


def test_inicio_fin_dia_taller_junio():
    """Día 2026-06-30 en Matamoros cubre 05:00 UTC – 04:59:59.999 UTC del día siguiente (CDT)."""
    d = date(2026, 6, 30)
    ini = inicio_dia_taller_utc(d)
    fin = fin_dia_taller_utc(d)
    tz = ZoneInfo(settings.TALLER_TIMEZONE)
    assert ini == datetime(2026, 6, 30, 5, 0, 0)
    assert fin == datetime(2026, 7, 1, 4, 59, 59, 999000)
    # verificación inversa
    assert ini.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).date() == d
    assert fin.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).date() == d


def test_ingreso_ot_en_dia_taller_expr():
    from app.models.orden_trabajo import OrdenTrabajo

    expr = ingreso_ot_en_dia_taller(OrdenTrabajo.fecha_ingreso, date(2026, 6, 30))
    assert expr is not None


def test_aplicar_filtro_rango_taller_genera_dos_condiciones():
    from app.models.caja_turno import CajaTurno

    conds = aplicar_filtro_rango_taller(
        CajaTurno.fecha_cierre,
        date(2026, 6, 1),
        date(2026, 6, 30),
    )
    assert len(conds) == 2
