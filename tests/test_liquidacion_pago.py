"""Pruebas de liquidación de venta al registrar pagos (redondeo monetario)."""
from decimal import Decimal

from app.utils.liquidacion_pago import evaluar_pago_contra_total


def test_liquida_pago_unico_exacto():
    excede, liquida, nuevo_rd, total_rd, nuevo_total = evaluar_pago_contra_total(
        Decimal("0"), Decimal("150.00"), Decimal("150.00")
    )
    assert not excede
    assert liquida
    assert nuevo_rd == total_rd == Decimal("150.00")
    assert nuevo_total == Decimal("150.00")


def test_liquida_dos_pagos():
    excede, liquida, _, total_rd, _ = evaluar_pago_contra_total(
        Decimal("60.00"), Decimal("40.00"), Decimal("100.00")
    )
    assert not excede
    assert liquida
    assert total_rd == Decimal("100.00")


def test_no_liquida_pago_parcial():
    excede, liquida, _, _, _ = evaluar_pago_contra_total(
        Decimal("30.00"), Decimal("20.00"), Decimal("100.00")
    )
    assert not excede
    assert not liquida


def test_excede_total():
    excede, liquida, _, _, _ = evaluar_pago_contra_total(
        Decimal("99.00"), Decimal("2.00"), Decimal("100.00")
    )
    assert excede
    assert not liquida


def test_artefactos_precision_se_liquida_con_redondeo():
    """Acumulado con más decimales que el total en BD: al redondear cuadra con el total."""
    excede, liquida, nuevo_rd, total_rd, _ = evaluar_pago_contra_total(
        Decimal("33.333"), Decimal("33.333"), Decimal("66.67")
    )
    assert not excede
    assert liquida
    assert nuevo_rd == total_rd == Decimal("66.67")


def test_total_pagado_none_como_cero():
    """SUM sin filas puede llegar como None en otros contextos."""
    excede, liquida, _, _, nuevo_total = evaluar_pago_contra_total(
        None, Decimal("50.00"), Decimal("50.00")
    )
    assert not excede
    assert liquida
    assert nuevo_total == Decimal("50.00")


def test_monto_float_entrada():
    excede, liquida, _, _, _ = evaluar_pago_contra_total(0, 100.0, 100.0)
    assert not excede
    assert liquida
