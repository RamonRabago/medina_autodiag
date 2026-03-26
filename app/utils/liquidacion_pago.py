"""
Validación de pagos contra el total de la venta (redondeo monetario coherente).
Usado por el router de pagos; centralizado para pruebas y mantenimiento.
"""
from decimal import Decimal

from app.utils.decimal_utils import money_round, to_decimal


def evaluar_pago_contra_total(
    total_pagado_previo,
    monto_ingresado,
    total_venta,
) -> tuple[bool, bool, Decimal, Decimal, Decimal]:
    """
    Args:
        total_pagado_previo: suma de pagos previos (p. ej. resultado de SUM en BD).
        monto_ingresado: monto del pago actual.
        total_venta: total de la venta.

    Returns:
        excede: acumulado redondeado > total venta redondeado.
        liquida: acumulado redondeado == total venta redondeado.
        nuevo_redondeado, total_venta_redondeado, nuevo_total (sin redondear previo al step final).
    """
    nuevo_total = to_decimal(total_pagado_previo) + to_decimal(monto_ingresado)
    nuevo_rd = money_round(nuevo_total)
    total_rd = money_round(to_decimal(total_venta))
    excede = nuevo_rd > total_rd
    liquida = nuevo_rd == total_rd
    return excede, liquida, nuevo_rd, total_rd, nuevo_total
