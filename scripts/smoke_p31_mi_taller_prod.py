"""Smoke post-deploy P3.1 Mi Taller. Uso: railway run python scripts/smoke_p31_mi_taller_prod.py"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import httpx

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.qa_guardrails import (  # noqa: E402
    SmokeAbort,
    assert_ot_item_qa_fixture,
    assert_prod_mutations_enabled,
    assert_production_api_target,
    get_allowed_ot_qa_ids,
    log_prod_target,
    prod_mutations_enabled,
)

from app.database import SessionLocal
from app.models.cita import Cita, EstadoCita
from app.models.usuario import Usuario
from app.utils.jwt import create_access_token

BASE = "https://medinaautodiag.up.railway.app"
ROLES_RESUMEN = ("ADMIN", "TECNICO", "CAJA", "EMPLEADO")
ACCIONES_MI_TALLER = frozenset({"iniciar_ot", "finalizar_ot"})
PROHIBIDAS_UI = frozenset(
    {"cobrar", "entregar_vehiculo", "cancelar_ot", "autorizar_ot", "registrar_pago", "entregar"}
)


def _user(db, rol: str) -> Usuario | None:
    return (
        db.query(Usuario)
        .filter(Usuario.rol == rol, Usuario.activo == True)  # noqa: E712
        .order_by(Usuario.id_usuario)
        .first()
    )


def _token(user: Usuario) -> str:
    rol = user.rol.value if hasattr(user.rol, "value") else str(user.rol)
    return create_access_token(data={"sub": str(user.id_usuario), "rol": rol})


def _resumen(token: str) -> tuple[int, dict]:
    r = httpx.get(
        f"{BASE}/api/operaciones/resumen",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit_items": 30, "incluir_items": True},
        timeout=90,
    )
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return r.status_code, body


def _accion_item(item: dict, nombre: str) -> dict | None:
    for a in item.get("acciones") or []:
        if a.get("accion") == nombre:
            return a
    return None


def _bandeja_ot_names(data: dict) -> list[str]:
    return [k for k in (data.get("bandejas") or {}) if k.startswith("ot_")]


def _check_mi_taller_acciones(data: dict, rol: str, errors: list[str]) -> None:
    for bname in ("ot_pendientes", "ot_en_proceso"):
        for item in (data.get("bandejas") or {}).get(bname, {}).get("items") or []:
            for a in item.get("acciones") or []:
                nombre = a.get("accion")
                if nombre in PROHIBIDAS_UI:
                    errors.append(f"{rol} {bname}#{item.get('id')}: accion prohibida en UI {nombre}")
                if nombre and nombre not in ACCIONES_MI_TALLER and a.get("permitida"):
                    errors.append(f"{rol} {bname}#{item.get('id')}: accion activa no P3.1 {nombre}")


def _fetch_ot(token: str, ot_id: int) -> dict:
    r = httpx.get(
        f"{BASE}/api/ordenes-trabajo/{ot_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=90,
    )
    if r.status_code != 200:
        raise SmokeAbort("ABORT-QA-005", f"GET OT #{ot_id} falló HTTP {r.status_code}")
    return r.json()


def _assert_ot_safe_to_mutate(token: str, item: dict) -> int:
    assert_production_api_target(BASE)
    assert_prod_mutations_enabled()
    ot_id = int(item["id"])
    allowed = get_allowed_ot_qa_ids()
    assert_ot_item_qa_fixture(item, allowed_ids=allowed, require_whitelist=True)
    ot_full = _fetch_ot(token, ot_id)
    assert_ot_item_qa_fixture(
        {
            "id": ot_full.get("id"),
            "numero_orden": ot_full.get("numero_orden"),
            "cliente_nombre": (ot_full.get("cliente") or {}).get("nombre"),
            "cliente": ot_full.get("cliente"),
            "vehiculo": ot_full.get("vehiculo"),
        },
        allowed_ids=allowed,
        require_whitelist=True,
    )
    print(
        f"[QA-GUARDRAILS] MUTATE OK OT #{ot_id} "
        f"{ot_full.get('numero_orden')} cliente={(ot_full.get('cliente') or {}).get('nombre')}"
    )
    return ot_id


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []
    print("=== SMOKE P3.1 MI TALLER (PROD) ===\n")
    log_prod_target(BASE)
    assert_production_api_target(BASE)

    r = httpx.get(f"{BASE}/health", timeout=30)
    print(f"GET /health -> {r.status_code}")
    if r.status_code != 200:
        errors.append(f"/health != 200 ({r.status_code})")
    else:
        try:
            h = r.json()
            print(f"   status={h.get('status')} database={h.get('database')}")
        except Exception:
            pass

    db = SessionLocal()
    tokens: dict[str, str] = {}
    try:
        for rol in ROLES_RESUMEN:
            user = _user(db, rol)
            if not user:
                errors.append(f"Sin usuario activo {rol}")
                continue
            token = _token(user)
            tokens[rol] = token
            status, data = _resumen(token)
            label = f"{rol} (#{user.id_usuario})"
            if status != 200:
                errors.append(f"A0 {label}: HTTP {status}")
                continue

            metricas = data.get("metricas") or {}
            bandejas = data.get("bandejas") or {}
            if "ot_completadas" not in metricas:
                errors.append(f"A0 {label}: falta metrica ot_completadas")
            if "ot_completadas" not in bandejas:
                errors.append(f"A0 {label}: falta bandeja ot_completadas")
            else:
                compl = bandejas["ot_completadas"]
                for item in compl.get("items") or []:
                    if item.get("acciones"):
                        errors.append(f"A0 {label}: ot_completadas item #{item.get('id')} tiene acciones")

            print(f"OK A0 {label}")
            print(
                f"   ot_pend={metricas.get('ot_pendientes')} "
                f"ot_proc={metricas.get('ot_en_proceso')} "
                f"ot_compl={metricas.get('ot_completadas')}"
            )
            print(f"   bandejas OT: {_bandeja_ot_names(data)}")

            if rol in ("ADMIN", "TECNICO"):
                _check_mi_taller_acciones(data, rol, errors)
            if rol in ("CAJA", "EMPLEADO"):
                pend = bandejas.get("ot_pendientes", {}).get("total", 0)
                proc = bandejas.get("ot_en_proceso", {}).get("total", 0)
                if pend or proc:
                    notes.append(f"{rol}: bandejas operativas no vacias (pend={pend} proc={proc})")

        # Flujo iniciar / finalizar (TECNICO) — requiere SMOKE_ALLOW_PROD_MUTATIONS + fixture QA
        tec_token = tokens.get("TECNICO")
        if tec_token:
            if not prod_mutations_enabled():
                notes.append(
                    "SKIP mutaciones OT: SMOKE_ALLOW_PROD_MUTATIONS no está activo "
                    "(ver docs/PLAN_QA_GUARDRAILS.md)"
                )
            else:
                status, data = _resumen(tec_token)
                if status == 200:
                    pendientes = (data.get("bandejas") or {}).get("ot_pendientes", {}).get("items") or []
                    candidato = None
                    for item in pendientes:
                        acc = _accion_item(item, "iniciar_ot")
                        if acc and acc.get("permitida"):
                            candidato = item
                            break
                    if candidato:
                        try:
                            oid = _assert_ot_safe_to_mutate(tec_token, candidato)
                        except SmokeAbort as exc:
                            errors.append(str(exc))
                            oid = None
                        if oid:
                            r_ini = httpx.post(
                                f"{BASE}/api/ordenes-trabajo/{oid}/iniciar",
                                headers={"Authorization": f"Bearer {tec_token}"},
                                json={},
                                timeout=90,
                            )
                            print(f"\nPOST iniciar OT #{oid} -> {r_ini.status_code}")
                            if r_ini.status_code not in (200, 201):
                                errors.append(f"iniciar OT #{oid}: HTTP {r_ini.status_code}")
                            else:
                                _, after = _resumen(tec_token)
                                ids_proc = [
                                    i["id"]
                                    for i in (after.get("bandejas") or {}).get("ot_en_proceso", {}).get("items") or []
                                ]
                                if oid not in ids_proc:
                                    errors.append(f"iniciar OT #{oid}: no aparece en ot_en_proceso tras refetch")
                                else:
                                    print(f"OK OT #{oid} en ot_en_proceso")
                                    en_proc = next(
                                        i
                                        for i in (after.get("bandejas") or {}).get("ot_en_proceso", {}).get("items") or []
                                        if i["id"] == oid
                                    )
                                    fin = _accion_item(en_proc, "finalizar_ot")
                                    if fin and fin.get("permitida"):
                                        try:
                                            _assert_ot_safe_to_mutate(tec_token, en_proc)
                                        except SmokeAbort as exc:
                                            errors.append(str(exc))
                                        else:
                                            r_fin = httpx.post(
                                                f"{BASE}/api/ordenes-trabajo/{oid}/finalizar",
                                                headers={"Authorization": f"Bearer {tec_token}"},
                                                json={},
                                                timeout=90,
                                            )
                                            print(f"POST finalizar OT #{oid} -> {r_fin.status_code}")
                                            if r_fin.status_code not in (200, 201):
                                                errors.append(f"finalizar OT #{oid}: HTTP {r_fin.status_code}")
                                            else:
                                                _, final = _resumen(tec_token)
                                                ids_compl = [
                                                    i["id"]
                                                    for i in (final.get("bandejas") or {})
                                                    .get("ot_completadas", {})
                                                    .get("items")
                                                    or []
                                                ]
                                                if oid not in ids_compl:
                                                    errors.append(f"finalizar OT #{oid}: no en ot_completadas")
                                                else:
                                                    print(f"OK OT #{oid} en ot_completadas")
                                    else:
                                        notes.append(f"OT #{oid} en proceso sin finalizar_ot permitida (SKIP finalizar)")
                    else:
                        notes.append("SKIP iniciar: no hay OT pendiente QA con iniciar_ot permitida")

        # Regresión Citas V2 — convertir sin vehiculo -> 409
        caja = _user(db, "CAJA") or _user(db, "ADMIN")
        if caja and tokens.get("CAJA") or caja:
            ctoken = tokens.get("CAJA") or _token(caja)
            cita = (
                db.query(Cita)
                .filter(
                    Cita.estado == EstadoCita.CONFIRMADA,
                    Cita.id_vehiculo.is_(None),
                    Cita.id_orden.is_(None),
                )
                .first()
            )
            if cita:
                r = httpx.post(
                    f"{BASE}/api/citas/{cita.id_cita}/convertir-orden",
                    headers={"Authorization": f"Bearer {ctoken}"},
                    timeout=90,
                )
                if r.status_code != 409:
                    errors.append(f"Citas convertir sin vehiculo: esperaba 409, got {r.status_code}")
                else:
                    print(f"\nOK Citas V2 convertir sin vehiculo cita #{cita.id_cita} -> 409")
            else:
                notes.append("SKIP Citas convertir sin vehiculo: no hay cita candidata")

            r = httpx.post(
                f"{BASE}/api/ordenes-trabajo/recepcion-rapida",
                headers={"Authorization": f"Bearer {ctoken}"},
                json={},
                timeout=90,
            )
            if r.status_code not in (400, 422):
                errors.append(f"Recepcion rapida: status inesperado {r.status_code}")
            else:
                print(f"OK Recepcion rapida endpoint vivo status={r.status_code}")

            payload = {
                "nombre": f"Qa-Op100 Smoke P31 {uuid.uuid4().int % 10_000_000:07d}",
                "telefono": f"644{uuid.uuid4().int % 10_000_000:07d}",
            }
            r = httpx.post(
                f"{BASE}/api/clientes/",
                json=payload,
                headers={"Authorization": f"Bearer {ctoken}"},
                timeout=90,
            )
            if r.status_code != 201:
                errors.append(f"Alta rapida cliente CAJA: esperaba 201, got {r.status_code}")
            else:
                print(f"OK Alta rapida cliente CAJA id={r.json().get('id_cliente')}")

        # Tokens para smoke frontend (stdout)
        print("\n--- TOKENS FRONTEND (JWT local) ---")
        for rol in ("ADMIN", "TECNICO", "CAJA", "EMPLEADO"):
            if rol in tokens:
                u = _user(db, rol)
                print(f"{rol}_TOKEN={tokens[rol][:40]}...")
                if u:
                    print(
                        f"{rol}_USER="
                        + json.dumps(
                            {
                                "id_usuario": u.id_usuario,
                                "email": u.email,
                                "nombre": u.nombre or u.email.split("@")[0],
                                "rol": rol,
                            },
                            ensure_ascii=False,
                        )
                    )

    finally:
        db.close()

    print()
    if notes:
        print("NOTAS:")
        for n in notes:
            print(f"  - {n}")
    if errors:
        print("FALLAS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SMOKE P3.1 MI TALLER: TODO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
