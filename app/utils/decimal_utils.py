"""
Utilidades para cálculos monetarios con Decimal.
Evita errores de precisión de punto flotante en montos.
"""
from decimal import Decimal, ROUND_HALF_UP


def to_decimal(value) -> Decimal:
    """Convierte cualquier valor numérico a Decimal de forma segura."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal(str(value))


def money_round(d: Decimal, places: int = 2) -> Decimal:
    """Redondea un Decimal a N decimales (por defecto 2) usando redondeo bancario."""
    if not isinstance(d, Decimal):
        d = to_decimal(d)
    q = Decimal(10) ** -places
    return d.quantize(q, rounding=ROUND_HALF_UP)


def to_float_money(d) -> float:
    """Convierte a float para serialización JSON, redondeado a 2 decimales."""
    return float(money_round(to_decimal(d)))
