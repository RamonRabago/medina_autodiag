"""Smoke A0 post-deploy — ejecutar: railway run python scripts/smoke_a0_prod.py"""
from __future__ import annotations

import json
import sys

import httpx

from app.database import SessionLocal
from app.models.cita import Cita, EstadoCita
from app.models.orden_trabajo import OrdenTrabajo
from app.models.usuario import Usuario
from app.utils.jwt import create_access_token

BASE = "https://medinaautodiag.up.railway.app"
ROLES = ("ADMIN", "CAJA", "TECNICO")
ACCIONES_FINANCIERAS_ITEM_ONLY = (
    "registrar_pago",
    "crear_venta_desde_ot",
    "entregar_vehiculo",
)


def _user_by_rol(db, rol: str) -> Usuario | None:
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
        timeout=90,
    )
    return r.status_code, r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def _accion(data: dict, nombre: str) -> dict | None:
    for a in data.get("acciones_globales", []):
        if a.get("accion") == nombre:
            return a
    return None


def _assert_financieras_item_only(data: dict, label: str, errors: list[str]) -> None:
    """P4.0 — mutaciones financiero-operativas nunca verdes en acciones_globales."""
    for nombre in ACCIONES_FINANCIERAS_ITEM_ONLY:
        accion = _accion(data, nombre)
        if not accion:
            errors.append(f"{label}: falta accion global {nombre}")
            continue
        if accion.get("permitida") is not False:
            errors.append(f"{label}: {nombre} global deberia ser permitida=false (item_only)")
        if accion.get("alcance") != "item_only":
            errors.append(f"{label}: {nombre} global deberia tener alcance=item_only")


def main() -> int:
    errors: list[str] = []
    db = SessionLocal()
    try:
        print("=== SMOKE A0 PRODUCCION ===\n")

        for rol in ROLES:
            user = _user_by_rol(db, rol)
            if not user:
                errors.append(f"No hay usuario activo con rol {rol}")
                continue
            status, data = _resumen(_token(user))
            label = f"{rol} (#{user.id_usuario} {user.nombre})"
            if status != 200:
                errors.append(f"{label}: HTTP {status}")
                continue
            if data.get("meta", {}).get("version_contrato") != "a0-v2":
                errors.append(f"{label}: version_contrato != a0-v2")
            _assert_financieras_item_only(data, label, errors)
            print(f"OK {label}")
            print(f"   metricas: {json.dumps(data.get('metricas', {}), ensure_ascii=False)}")
            conv = _accion(data, "convertir_cita_ot")
            pago = _accion(data, "registrar_pago")
            iniciar = _accion(data, "iniciar_ot")
            print(f"   convertir_cita_ot={conv.get('permitida') if conv else '?'}")
            print(
                f"   registrar_pago={pago.get('permitida') if pago else '?'} "
                f"alcance={pago.get('alcance') if pago else '?'}"
            )
            print(f"   iniciar_ot={iniciar.get('permitida') if iniciar else '?'}")
            print()

            if rol == "CAJA":
                if conv and not conv.get("permitida"):
                    errors.append("CAJA: convertir_cita_ot deberia estar permitida")
                if iniciar and iniciar.get("permitida"):
                    errors.append("CAJA: iniciar_ot NO deberia estar permitida")
            if rol == "TECNICO":
                if iniciar and not iniciar.get("permitida"):
                    errors.append("TECNICO: iniciar_ot deberia estar permitida")
                m = data.get("metricas", {})
                if m.get("ventas_saldo_pendiente", 0) != 0:
                    errors.append("TECNICO: no deberia ver ventas_saldo_pendiente > 0 en metricas")

        caja = _user_by_rol(db, "CAJA") or _user_by_rol(db, "ADMIN")
        if caja:
            token = _token(caja)
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
                ot_antes = db.query(OrdenTrabajo).count()
                r = httpx.post(
                    f"{BASE}/api/citas/{cita.id_cita}/convertir-orden",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=90,
                )
                if r.status_code != 409:
                    errors.append(f"convertir sin vehiculo cita #{cita.id_cita}: esperaba 409, got {r.status_code}")
                else:
                    detail = r.json().get("detail", {})
                    if isinstance(detail, dict) and detail.get("accion") == "COMPLETAR_RECEPCION":
                        print(f"OK convertir sin vehiculo cita #{cita.id_cita} -> 409 COMPLETAR_RECEPCION")
                    else:
                        errors.append(f"convertir sin vehiculo: detail inesperado {detail}")
                db.refresh(cita)
                if cita.id_orden is not None:
                    errors.append("convertir sin vehiculo: cita quedo con id_orden")
                if db.query(OrdenTrabajo).count() != ot_antes:
                    errors.append("convertir sin vehiculo: se creo OT indebidamente")
            else:
                print("SKIP convertir sin vehiculo: no hay cita CONFIRMADA sin vehiculo")

            r = httpx.post(
                f"{BASE}/api/ordenes-trabajo/recepcion-rapida",
                headers={"Authorization": f"Bearer {token}"},
                json={},
                timeout=90,
            )
            if r.status_code not in (400, 422):
                errors.append(f"recepcion-rapida: status inesperado {r.status_code}")
            else:
                print(f"OK recepcion-rapida endpoint vivo (CAJA) status={r.status_code}")

    finally:
        db.close()

    print()
    if errors:
        print("FALLAS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SMOKE A0: TODO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
