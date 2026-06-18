"""
Harness UX-1B.0 — paridad slice A0 v2.1 vs heavy legacy.

Compara respuestas de construir_resumen_operativo con params slice
contra incluir_items=true (referencia).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.operaciones_service import MAX_BANDEJAS_SLICE, construir_resumen_operativo
from tests.a0_metricas_paridad import (
    METRICAS_KEYS,
    assert_bandejas_total_coincide_metricas,
    assert_paridad_metricas,
    extraer_metricas,
)

BANDEJA_KEYS: tuple[str, ...] = (
    "citas_convertibles",
    "citas_pendientes_asistencia",
    "ot_completadas",
    "ot_en_proceso",
    "ot_listas_entrega",
    "ot_pendientes",
    "ot_pendientes_cobro",
    "ventas_saldo_pendiente",
)


def obtener_resumen_heavy(
    db: Session,
    usuario: Usuario,
    *,
    limit_items: int = 30,
) -> dict[str, Any]:
    """Referencia legacy — incluir_items=true sin slice."""
    return construir_resumen_operativo(
        db,
        usuario,
        limit_items=limit_items,
        incluir_items=True,
    )


def obtener_resumen_slice_grupo(
    db: Session,
    usuario: Usuario,
    grupo: str,
    *,
    limit_items: int = 30,
) -> dict[str, Any]:
    return construir_resumen_operativo(
        db,
        usuario,
        limit_items=limit_items,
        incluir_items=True,
        grupo=grupo,
    )


def obtener_resumen_slice_bandejas(
    db: Session,
    usuario: Usuario,
    bandejas: list[str],
    *,
    limit_items: int = 30,
) -> dict[str, Any]:
    return construir_resumen_operativo(
        db,
        usuario,
        limit_items=limit_items,
        incluir_items=True,
        bandejas=",".join(bandejas),
    )


def assert_meta_slice(resumen: dict[str, Any], *, grupo: Optional[str] = None) -> None:
    meta = resumen.get("meta") or {}
    assert meta.get("version_contrato") == "a0-v2.1", meta
    assert meta.get("parcial") is True, meta
    assert meta.get("incluir_items") is True, meta
    hidratadas = meta.get("bandejas_hidratadas")
    assert isinstance(hidratadas, list), meta
    if grupo is not None:
        assert meta.get("grupo") == grupo, meta


def assert_meta_legacy(resumen: dict[str, Any]) -> None:
    meta = resumen.get("meta") or {}
    assert meta.get("version_contrato") == "a0-v2", meta
    assert meta.get("parcial") in (None, False), meta


def assert_slice_paridad_metricas_vs_heavy(
    heavy: dict[str, Any],
    slice_res: dict[str, Any],
    *,
    context: str = "",
) -> None:
    assert_paridad_metricas(
        extraer_metricas(heavy),
        extraer_metricas(slice_res),
        context=context or "slice vs heavy métricas",
    )


def assert_slice_paridad_totales_vs_heavy(
    heavy: dict[str, Any],
    slice_res: dict[str, Any],
    *,
    context: str = "",
) -> None:
    prefijo = f"{context}: " if context else ""
    heavy_b = heavy.get("bandejas") or {}
    slice_b = slice_res.get("bandejas") or {}
    errores: list[str] = []
    for key in BANDEJA_KEYS:
        h_total = (heavy_b.get(key) or {}).get("total")
        s_total = (slice_b.get(key) or {}).get("total")
        if h_total != s_total:
            errores.append(f"  {key}: heavy={h_total} slice={s_total}")
    if errores:
        raise AssertionError(f"{prefijo}totales bandeja divergen:\n" + "\n".join(errores))


def assert_bandeja_items_paridad(
    heavy: dict[str, Any],
    slice_res: dict[str, Any],
    bandeja_key: str,
    *,
    context: str = "",
) -> None:
    prefijo = f"{context}: " if context else ""
    h_items = (heavy.get("bandejas") or {}).get(bandeja_key, {}).get("items") or []
    s_items = (slice_res.get("bandejas") or {}).get(bandeja_key, {}).get("items") or []
    h_ids = [i.get("id") for i in h_items]
    s_ids = [i.get("id") for i in s_items]
    assert h_ids == s_ids, f"{prefijo}{bandeja_key} ids heavy={h_ids} slice={s_ids}"
    for h_item, s_item in zip(h_items, s_items, strict=True):
        assert h_item.get("acciones") == s_item.get("acciones"), (
            f"{prefijo}{bandeja_key} id={h_item.get('id')} acciones divergen"
        )


def assert_slice_bandeja_vacia_no_hidratada(
    slice_res: dict[str, Any],
    bandeja_key: str,
) -> None:
    meta = slice_res.get("meta") or {}
    hidratadas = meta.get("bandejas_hidratadas") or []
    items = (slice_res.get("bandejas") or {}).get(bandeja_key, {}).get("items") or []
    if bandeja_key not in hidratadas:
        assert items == [], f"{bandeja_key} no hidratada pero tiene items"


def assert_slice_paridad_completa_bandeja(
    heavy: dict[str, Any],
    slice_res: dict[str, Any],
    bandeja_key: str,
    *,
    context: str = "",
) -> None:
    assert_slice_paridad_metricas_vs_heavy(heavy, slice_res, context=context)
    assert_slice_paridad_totales_vs_heavy(heavy, slice_res, context=context)
    assert_bandeja_items_paridad(heavy, slice_res, bandeja_key, context=context)


__all__ = [
    "BANDEJA_KEYS",
    "MAX_BANDEJAS_SLICE",
    "METRICAS_KEYS",
    "assert_bandejas_total_coincide_metricas",
    "assert_bandeja_items_paridad",
    "assert_meta_legacy",
    "assert_meta_slice",
    "assert_slice_bandeja_vacia_no_hidratada",
    "assert_slice_paridad_completa_bandeja",
    "assert_slice_paridad_metricas_vs_heavy",
    "assert_slice_paridad_totales_vs_heavy",
    "obtener_resumen_heavy",
    "obtener_resumen_slice_bandejas",
    "obtener_resumen_slice_grupo",
]
