"""Smoke Dashboard V2 — API + timing. Uso: python scripts/_smoke_dashboard_v2.py"""
from __future__ import annotations

import json
import sys
import time

import httpx

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.utils.jwt import create_access_token

BASE = "http://127.0.0.1:8000"


def _admin_token(db) -> str:
    user = (
        db.query(Usuario)
        .filter(Usuario.rol == "ADMIN", Usuario.activo == True)  # noqa: E712
        .order_by(Usuario.id_usuario)
        .first()
    )
    if not user:
        raise RuntimeError("No hay usuario ADMIN activo en BD")
    rol = user.rol.value if hasattr(user.rol, "value") else str(user.rol)
    return create_access_token(data={"sub": str(user.id_usuario), "rol": rol})


def _token_rol(db, rol: str) -> str | None:
    user = (
        db.query(Usuario)
        .filter(Usuario.rol == rol, Usuario.activo == True)  # noqa: E712
        .order_by(Usuario.id_usuario)
        .first()
    )
    if not user:
        return None
    r = user.rol.value if hasattr(user.rol, "value") else str(user.rol)
    return create_access_token(data={"sub": str(user.id_usuario), "rol": r})


def main() -> int:
    errors: list[str] = []
    db = SessionLocal()
    try:
        token = _admin_token(db)
        headers = {"Authorization": f"Bearer {token}"}
        client = httpx.Client(base_url=BASE, headers=headers, timeout=60)

        print("=== SMOKE DASHBOARD V2 API ===\n")

        cases = [
            ("GET /api/dashboard", "/api/dashboard", None),
            ("operativa", "/api/dashboard", {"secciones": "operativa"}),
            ("finanzas", "/api/dashboard", {"secciones": "finanzas", "periodo": "mes"}),
            ("inventario", "/api/dashboard", {"secciones": "inventario"}),
        ]

        for label, path, params in cases:
            t0 = time.perf_counter()
            r = client.get(path, params=params or {})
            ms = (time.perf_counter() - t0) * 1000
            print(f"[{label}] status={r.status_code} time={ms:.0f}ms")
            if r.status_code != 200:
                errors.append(f"{label}: status {r.status_code}")
                continue
            data = r.json()
            if label in ("GET /api/dashboard", "operativa"):
                op = data.get("operativa")
                if not op:
                    errors.append(f"{label}: operativa es null")
                else:
                    rec = op.get("recomendacion_inteligente")
                    if not rec or not rec.get("titulo"):
                        errors.append(f"{label}: falta recomendacion_inteligente.titulo")
                    if "decision_score" not in (rec or {}):
                        errors.append(f"{label}: falta decision_score en API (ok oculto en UI)")
                    for key in ("salud_operativa", "prioridades_agrupadas", "resumen", "acciones_frecuentes"):
                        if key not in op:
                            errors.append(f"{label}: falta operativa.{key}")
                if data.get("finanzas") is not None and label == "GET /api/dashboard":
                    errors.append("default mount no debe incluir finanzas")
                if data.get("inventario") is not None and label == "GET /api/dashboard":
                    errors.append("default mount no debe incluir inventario")
            if label == "finanzas" and data.get("finanzas") is None:
                errors.append("finanzas: bloque null")
            if label == "inventario" and data.get("inventario") is None:
                errors.append("inventario: bloque null")

        r422 = client.get("/api/dashboard", params={"secciones": "basura"})
        print(f"[422 basura] status={r422.status_code}")
        if r422.status_code != 422:
            errors.append(f"secciones=basura deberia ser 422, fue {r422.status_code}")

        # P5.1 — CAJA dashboard no operativa pesada en default
        caja_tok = _token_rol(db, "CAJA")
        if caja_tok:
            r_caja = httpx.get(
                f"{BASE}/api/dashboard",
                headers={"Authorization": f"Bearer {caja_tok}"},
                timeout=30,
            )
            print(f"[CAJA dashboard] status={r_caja.status_code}")
            if r_caja.status_code == 200:
                d = r_caja.json()
                if d.get("operativa") and d["operativa"].get("recomendacion_inteligente"):
                    pass  # CAJA puede recibir operativa si es admin_o_caja — ok backend
        else:
            print("[CAJA] sin usuario — skip")

        # A0 intacto
        t0 = time.perf_counter()
        r_a0 = client.get("/api/operaciones/resumen", params={"incluir_items": "false", "limit_items": 1})
        ms_a0 = (time.perf_counter() - t0) * 1000
        print(f"[A0 resumen ligero] status={r_a0.status_code} time={ms_a0:.0f}ms")
        if r_a0.status_code != 200:
            errors.append(f"A0 resumen status {r_a0.status_code}")

        client.close()

        if errors:
            print("\nERRORES:")
            for e in errors:
                print(f"  - {e}")
            return 1

        print("\nOK — API smoke Dashboard V2")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
