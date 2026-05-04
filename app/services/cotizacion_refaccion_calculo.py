"""Cálculos de costo MXN y precio sugerido para cotizaciones de refacción especial."""
from decimal import Decimal
from typing import Any, Optional

from app.config import settings
from app.models.cotizacion_refaccion_especial import (
    MonedaCotizacion,
    OpcionCompraLineaCotizacion,
)


def _moneda_val(m: Any) -> str:
    if hasattr(m, "value"):
        return str(m.value)
    return str(m)


def costo_unitario_mxn_opcion(
    opcion: OpcionCompraLineaCotizacion,
    tc_cotizacion: Optional[Decimal],
) -> Decimal:
    """
    Costo unitario en MXN: USD usa tipo de cambio (por opción o cotización) + otros_costos_mxn.
    MXN: monto_unitario + otros_costos_mxn.
    """
    monto = Decimal(str(opcion.monto_unitario or 0))
    otros = Decimal(str(opcion.otros_costos_mxn or 0))
    moneda = _moneda_val(opcion.moneda)

    if moneda == MonedaCotizacion.USD.value:
        tc_line = opcion.tipo_cambio_a_mxn
        tc = Decimal(str(tc_line)) if tc_line is not None else None
        if tc is None and tc_cotizacion is not None:
            tc = Decimal(str(tc_cotizacion))
        if tc is None:
            raise ValueError(
                "Para precios en USD defina tipo de cambio en la cotización (tc_referencia_usd_mxn) "
                "o en la opción (tipo_cambio_a_mxn)."
            )
        return (monto * tc) + otros

    return monto + otros


def precio_sugerido_con_iva(
    costo_unitario_mxn: Decimal,
    cantidad: Decimal,
    margen_pct: Optional[Decimal],
    iva_pct: Optional[Decimal],
) -> Decimal:
    """
    Precio total sugerido al cliente con IVA sobre la base ya marcada:
    base = costo_total * (1 + margen/100); precio = base * (1 + IVA/100).
    """
    sub_costo = costo_unitario_mxn * cantidad
    m = margen_pct if margen_pct is not None else Decimal(str(settings.MARKUP_PORCENTAJE))
    iva = iva_pct if iva_pct is not None else Decimal(str(settings.IVA_PORCENTAJE))
    base = sub_costo * (Decimal("1") + m / Decimal("100"))
    total = base * (Decimal("1") + iva / Decimal("100"))
    return total.quantize(Decimal("0.01"))


def ganancia_estimada(
    precio_con_iva: Decimal,
    costo_unitario_mxn: Decimal,
    cantidad: Decimal,
) -> Decimal:
    """Ganancia bruta aproximada: precio total menos costo total (sin desglosar IVA)."""
    costo_tot = (costo_unitario_mxn * cantidad).quantize(Decimal("0.01"))
    return (precio_con_iva - costo_tot).quantize(Decimal("0.01"))
