"""Tests unitarios — cálculo MXN y precio sugerido cotización refacción."""

from decimal import Decimal

import pytest

from app.models.cotizacion_refaccion_especial import MonedaCotizacion
from app.services.cotizacion_refaccion_calculo import (
    costo_unitario_mxn_opcion,
    precio_sugerido_con_iva,
)


class FakeOpcion:
    def __init__(self, moneda, monto, otros, tc_line=None):
        self.moneda = moneda
        self.monto_unitario = monto
        self.otros_costos_mxn = otros
        self.tipo_cambio_a_mxn = tc_line


def test_costo_mxn_usd_con_tc_cotizacion():
    op = FakeOpcion(MonedaCotizacion.USD, Decimal("50"), Decimal("100"))
    assert costo_unitario_mxn_opcion(op, Decimal("20")) == Decimal("1100")  # 50*20+100


def test_costo_mxn_usd_sin_tc_falla():
    op = FakeOpcion(MonedaCotizacion.USD, Decimal("10"), Decimal("0"))
    with pytest.raises(ValueError):
        costo_unitario_mxn_opcion(op, None)


def test_precio_sugerido_markup():
    # costo 100, qty 1, margen 10%, iva 16% -> base 110, total 127.60
    p = precio_sugerido_con_iva(Decimal("100"), Decimal("1"), Decimal("10"), Decimal("16"))
    assert p == Decimal("127.60")
