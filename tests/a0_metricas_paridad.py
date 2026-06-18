"""
Harness P5.3 — paridad de métricas A0 (Fase 1 Commit A).

Referencia legacy: totales producidos por las bandejas actuales con limit=0,
replicando la orquestación de construir_resumen_operativo sin tocar producción.

Uso previsto:
- Commit A: legacy harness == construir_resumen_operativo(incluir_items=false)
- Commit D+: obtener_metricas_fast_path() == metricas_legacy_desde_bandejas()
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.operaciones_service import (
    _puede_ver_bandeja_financiera,
    _puede_ver_citas,
    _rol_usuario,
    bandeja_citas_convertibles,
    bandeja_citas_pendientes_asistencia,
    bandeja_ot_completadas,
    bandeja_ot_en_proceso,
    bandeja_ot_listas_entrega,
    bandeja_ot_pendientes,
    bandeja_ot_pendientes_cobro,
    bandeja_ventas_saldo_pendiente,
    construir_resumen_operativo,
    contadores_refacciones,
)

# Contrato A0 v2 — claves obligatorias en metricas (orden estable para diffs).
METRICAS_KEYS: tuple[str, ...] = (
    "citas_pendientes_asistencia",
    "citas_convertibles",
    "ot_pendientes",
    "ot_en_proceso",
    "ot_completadas",
    "ot_pendientes_cobro",
    "ot_listas_entrega",
    "ventas_saldo_pendiente",
    "refacciones_en_compra",
    "refacciones_recibidas_pendiente_entrega",
)

BANDEJA_A_METRICA: dict[str, str] = {
    "citas_pendientes_asistencia": "citas_pendientes_asistencia",
    "citas_convertibles": "citas_convertibles",
    "ot_pendientes": "ot_pendientes",
    "ot_en_proceso": "ot_en_proceso",
    "ot_completadas": "ot_completadas",
    "ot_pendientes_cobro": "ot_pendientes_cobro",
    "ot_listas_entrega": "ot_listas_entrega",
    "ventas_saldo_pendiente": "ventas_saldo_pendiente",
}


def extraer_metricas(resumen: dict[str, Any]) -> dict[str, int]:
    """Extrae las 10 métricas del payload A0 (servicio o API)."""
    metricas = resumen.get("metricas") or {}
    return {k: int(metricas.get(k, 0) or 0) for k in METRICAS_KEYS}


def diff_metricas(esperado: dict[str, int], actual: dict[str, int]) -> str:
    """Texto legible de diferencias entre dos dicts de métricas."""
    lineas: list[str] = []
    for clave in METRICAS_KEYS:
        e = esperado.get(clave, 0)
        a = actual.get(clave, 0)
        if e != a:
            lineas.append(f"  {clave}: legacy={e} actual={a}")
    if not lineas:
        return "(sin diferencias)"
    return "\n".join(lineas)


def assert_paridad_metricas(
    esperado: dict[str, int],
    actual: dict[str, int],
    *,
    context: str = "",
) -> None:
    """Assert con mensaje detallado — uso en tests de paridad P5.3."""
    prefijo = f"{context}: " if context else ""
    if esperado == actual:
        return
    raise AssertionError(
        f"{prefijo}métricas no coinciden:\n{diff_metricas(esperado, actual)}"
    )


def metricas_legacy_desde_bandejas(db: Session, usuario: Usuario) -> dict[str, int]:
    """
    Referencia legacy P5.3: invoca bandeja_* con limit=0 (equivalente a incluir_items=false).

    Replica la rama de roles de construir_resumen_operativo sin serializar ítems.
  """
    rol = _rol_usuario(usuario)
    limit = 0
    tecnico_filtro = usuario.id_usuario if rol == "TECNICO" else None
    ver_citas = _puede_ver_citas(rol) or rol == "ADMIN"
    ver_financiero = _puede_ver_bandeja_financiera(rol)

    if ver_citas:
        total_asist, _ = bandeja_citas_pendientes_asistencia(db, rol, limit)
        total_conv, _ = bandeja_citas_convertibles(db, rol, limit)
    else:
        total_asist, total_conv = 0, 0

    if rol == "TECNICO":
        total_ot_pend, _ = bandeja_ot_pendientes(db, rol, usuario, limit, tecnico_filtro)
        total_ot_proc, _ = bandeja_ot_en_proceso(db, rol, usuario, limit, tecnico_filtro)
        total_ot_compl, _ = bandeja_ot_completadas(db, rol, usuario, limit, tecnico_filtro)
        total_ot_cobro, total_ot_entrega, total_ventas = 0, 0, 0
    elif ver_financiero:
        total_ot_pend, _ = bandeja_ot_pendientes(db, rol, usuario, limit, None)
        total_ot_proc, _ = bandeja_ot_en_proceso(db, rol, usuario, limit, None)
        total_ot_cobro, _ = bandeja_ot_pendientes_cobro(db, rol, usuario, limit)
        total_ot_entrega, _ = bandeja_ot_listas_entrega(db, rol, usuario, limit)
        total_ventas, _ = bandeja_ventas_saldo_pendiente(db, rol, usuario, limit)
        if rol == "ADMIN":
            total_ot_compl, _ = bandeja_ot_completadas(db, rol, usuario, limit, None)
        else:
            total_ot_compl = 0
    elif rol == "EMPLEADO":
        total_ot_pend, _ = bandeja_ot_pendientes(db, rol, usuario, limit, None)
        total_ot_proc, _ = bandeja_ot_en_proceso(db, rol, usuario, limit, None)
        total_ot_compl, total_ot_cobro, total_ot_entrega, total_ventas = 0, 0, 0, 0
    else:
        total_ot_pend, _ = bandeja_ot_pendientes(db, rol, usuario, limit, None)
        total_ot_proc, _ = bandeja_ot_en_proceso(db, rol, usuario, limit, None)
        total_ot_cobro, _ = bandeja_ot_pendientes_cobro(db, rol, usuario, limit)
        total_ot_entrega, _ = bandeja_ot_listas_entrega(db, rol, usuario, limit)
        total_ventas, _ = bandeja_ventas_saldo_pendiente(db, rol, usuario, limit)
        total_ot_compl = 0

    ref_compra, ref_recibidas = contadores_refacciones(db)

    return {
        "citas_pendientes_asistencia": total_asist,
        "citas_convertibles": total_conv,
        "ot_pendientes": total_ot_pend,
        "ot_en_proceso": total_ot_proc,
        "ot_completadas": total_ot_compl,
        "ot_pendientes_cobro": total_ot_cobro,
        "ot_listas_entrega": total_ot_entrega,
        "ventas_saldo_pendiente": total_ventas,
        "refacciones_en_compra": ref_compra,
        "refacciones_recibidas_pendiente_entrega": ref_recibidas,
    }


def metricas_desde_construir_resumen(
    db: Session,
    usuario: Usuario,
    *,
    incluir_items: bool = False,
    limit_items: int = 15,
) -> dict[str, int]:
    """Métricas vía servicio productivo (sin HTTP)."""
    resumen = construir_resumen_operativo(
        db,
        usuario,
        limit_items=limit_items,
        incluir_items=incluir_items,
    )
    return extraer_metricas(resumen)


def metricas_desde_api_response(data: dict[str, Any]) -> dict[str, int]:
    """Métricas desde JSON de GET /api/operaciones/resumen."""
    return extraer_metricas(data)


def assert_bandejas_total_coincide_metricas(
    resumen: dict[str, Any],
    *,
    context: str = "",
) -> None:
    """Verifica bandejas.*.total == metricas homóloga (modo light)."""
    metricas = resumen.get("metricas") or {}
    bandejas = resumen.get("bandejas") or {}
    errores: list[str] = []
    for bandeja, clave_metrica in BANDEJA_A_METRICA.items():
        total_bandeja = (bandejas.get(bandeja) or {}).get("total")
        valor_metrica = metricas.get(clave_metrica)
        if total_bandeja != valor_metrica:
            errores.append(
                f"  {bandeja}: bandeja.total={total_bandeja} metricas.{clave_metrica}={valor_metrica}"
            )
    if errores:
        prefijo = f"{context}: " if context else ""
        raise AssertionError(f"{prefijo}totales bandeja ≠ metricas:\n" + "\n".join(errores))


def obtener_metricas_fast_path(db: Session, usuario: Usuario) -> dict[str, int]:
    """
    Placeholder P5.3 Fase 1 Commit D+.

    Cuando exista _construir_resumen_metricas_rapidas, este helper delegará allí.
    """
    raise NotImplementedError(
        "Fast path A0 (incluir_items=false) no implementado — pendiente Commit D P5.3"
    )
