"""
Guardrails P0 — smokes con mutaciones en producción.

Ver docs/PLAN_QA_GUARDRAILS.md
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

QA_CLIENT_PREFIX = "Qa-Op"
QA_VEHICULO_MARKERS = (" Qa", "Qa-", " QA")

PROD_DATABASE_MARKERS = ("aivencloud.com", "railway.app", "planetscale.com")
PROD_API_MARKERS = ("medinaautodiag.up.railway.app", ".up.railway.app")


class SmokeAbort(Exception):
    """Abort smoke before mutating production data."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def is_production_database_url(url: Optional[str] = None) -> bool:
    raw = (url if url is not None else os.getenv("DATABASE_URL", "")).strip().lower()
    if not raw:
        return False
    if "localhost" in raw or "127.0.0.1" in raw:
        return False
    return any(marker in raw for marker in PROD_DATABASE_MARKERS)


def is_production_api_base(base: str) -> bool:
    base_lower = base.strip().lower()
    return any(marker in base_lower for marker in PROD_API_MARKERS)


def assert_production_api_target(api_base: str) -> None:
    """Confirma que las reglas prod aplican cuando el target es producción."""
    if is_production_api_base(api_base):
        return
    raise SmokeAbort(
        "ABORT-QA-000",
        f"API base '{api_base}' no reconocida como prod; no ejecutar mutaciones sin target explícito",
    )


def prod_mutations_enabled() -> bool:
    return os.getenv("SMOKE_ALLOW_PROD_MUTATIONS", "").strip().lower() in ("1", "true", "yes")


def assert_prod_mutations_enabled() -> None:
    if not prod_mutations_enabled():
        raise SmokeAbort(
            "ABORT-QA-007",
            "Mutaciones en prod deshabilitadas. Exportar SMOKE_ALLOW_PROD_MUTATIONS=true para habilitar",
        )


def get_allowed_ot_qa_ids() -> frozenset[int]:
    ids: set[int] = set()
    single = os.getenv("SMOKE_OT_QA_ID", "").strip()
    if single:
        ids.add(int(single))
    multi = os.getenv("SMOKE_OT_QA_IDS", "").strip()
    if multi:
        for part in re.split(r"[\s,;]+", multi):
            part = part.strip()
            if part:
                ids.add(int(part))
    return frozenset(ids)


def cliente_nombre_es_fixture_qa(nombre: Optional[str]) -> bool:
    if not nombre or not str(nombre).strip():
        return False
    return str(nombre).strip().startswith(QA_CLIENT_PREFIX)


def vehiculo_es_fixture_qa(vehiculo: Optional[dict[str, Any]]) -> bool:
    if not vehiculo:
        return False
    blob = " ".join(
        str(vehiculo.get(k) or "")
        for k in ("marca", "modelo", "descripcion", "placas", "vin")
    )
    return any(marker.lower() in blob.lower() for marker in QA_VEHICULO_MARKERS)


def _cliente_nombre_from_ot(ot: dict[str, Any]) -> Optional[str]:
    cliente = ot.get("cliente")
    if isinstance(cliente, dict):
        return cliente.get("nombre") or cliente.get("nombre_completo")
    return ot.get("cliente_nombre")


def assert_ot_qa_fixture(
    ot: dict[str, Any],
    *,
    allowed_ids: Optional[frozenset[int]] = None,
    require_whitelist: bool = True,
) -> None:
    """
    Valida OT antes de mutación. Lanza SmokeAbort con código ABORT-QA-xxx.
    """
    ot_id = ot.get("id")
    numero = ot.get("numero_orden") or ot.get("numero")
    cliente_nombre = _cliente_nombre_from_ot(ot)
    vehiculo = ot.get("vehiculo") if isinstance(ot.get("vehiculo"), dict) else None

    if ot_id is None:
        raise SmokeAbort("ABORT-QA-004", "OT sin id — imposible validar fixture QA")

    whitelist = allowed_ids if allowed_ids is not None else get_allowed_ot_qa_ids()
    if require_whitelist and not whitelist:
        raise SmokeAbort(
            "ABORT-QA-002",
            f"OT id={ot_id}: lista blanca vacía (SMOKE_OT_QA_ID / SMOKE_OT_QA_IDS)",
        )
    if whitelist and int(ot_id) not in whitelist:
        raise SmokeAbort(
            "ABORT-QA-002",
            f"OT id={ot_id} numero={numero} no está en lista blanca {sorted(whitelist)}",
        )

    if not cliente_nombre_es_fixture_qa(cliente_nombre):
        raise SmokeAbort(
            "ABORT-QA-001",
            f"OT id={ot_id} numero={numero} cliente='{cliente_nombre}' no cumple prefijo {QA_CLIENT_PREFIX}*",
        )

    if vehiculo and not vehiculo_es_fixture_qa(vehiculo):
        raise SmokeAbort(
            "ABORT-QA-001",
            f"OT id={ot_id} vehículo no cumple convención QA documentada: {vehiculo}",
        )


def assert_ot_item_qa_fixture(
    item: dict[str, Any],
    *,
    allowed_ids: Optional[frozenset[int]] = None,
    require_whitelist: bool = True,
) -> None:
    """Valida ítem de bandeja A0 (cliente_nombre en raíz)."""
    ot = {
        "id": item.get("id"),
        "numero_orden": item.get("numero_orden"),
        "cliente_nombre": item.get("cliente_nombre"),
        "cliente": {"nombre": item.get("cliente_nombre")} if item.get("cliente_nombre") else None,
        "vehiculo": item.get("vehiculo"),
    }
    assert_ot_qa_fixture(ot, allowed_ids=allowed_ids, require_whitelist=require_whitelist)


def assert_prod_db_mutation_policy(*, transactional_rollback: bool) -> None:
    """
    En BD prod: mutaciones solo permitidas con rollback transaccional (crosscheck)
    o vía API con guardrails + SMOKE_ALLOW_PROD_MUTATIONS.
    """
    if not is_production_database_url():
        return
    if not transactional_rollback:
        raise SmokeAbort(
            "ABORT-QA-008",
            "BD prod detectada sin rollback transaccional — usar qa_guardrails + SMOKE_ALLOW_PROD_MUTATIONS",
        )


def log_prod_target(api_base: Optional[str] = None, *, transactional_rollback: bool = False) -> None:
    db_prod = is_production_database_url()
    api_prod = is_production_api_base(api_base) if api_base else False
    print(
        f"[QA-GUARDRAILS] database_prod={db_prod} api_prod={api_prod} "
        f"transactional_rollback={transactional_rollback} "
        f"prod_mutations_enabled={prod_mutations_enabled()}"
    )
