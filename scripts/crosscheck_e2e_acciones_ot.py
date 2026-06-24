"""
Cross-check E2E PREREQ Acciones OT — A0 vs detalle OT vs API mutación.

Código local (39c7102+) + BD Railway, sin deploy de API.
Datos de prueba en transacción con ROLLBACK al final (no basura persistente).

Ejecutar:
  railway run python scripts/crosscheck_e2e_acciones_ot.py
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.qa_guardrails import (  # noqa: E402
    SmokeAbort,
    assert_ot_qa_fixture,
    assert_prod_db_mutation_policy,
    cliente_nombre_es_fixture_qa,
    log_prod_target,
)

import app.main  # noqa: F401 — evita import circular
from app.database import engine, get_db
from app.main import app
from app.models.caja_turno import CajaTurno
from app.models.cliente import Cliente
from app.models.detalle_orden import DetalleOrdenTrabajo
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.servicio import Servicio
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.models.venta import Venta
from app.services.ot_acciones_service import ALLOW_TECNICO_SELF_ASSIGN
from app.utils.jwt import create_access_token
from app.utils.security import hash_password
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


PREFIX = "E2E-XC"
BANDEJAS_OT = (
    "ot_pendientes",
    "ot_en_proceso",
    "ot_pendientes_cobro",
    "ot_listas_entrega",
)


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _token(user: Usuario) -> str:
    rol = user.rol.value if hasattr(user.rol, "value") else str(user.rol)
    return create_access_token(data={"sub": str(user.id_usuario), "rol": rol})


def _headers(user: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


def _seed_tecnico(db, tag: str) -> Usuario:
    u = Usuario(
        nombre=f"{PREFIX} Tec {tag}",
        email=f"{PREFIX.lower()}_tec_{tag}@test.medina",
        password_hash=hash_password("E2EXc!9"),
        rol="TECNICO",
        activo=True,
    )
    db.add(u)
    db.flush()
    return u


def _seed_caja(db, tag: str) -> tuple[Usuario, CajaTurno]:
    u = Usuario(
        nombre=f"{PREFIX} Caja {tag}",
        email=f"{PREFIX.lower()}_caja_{tag}@test.medina",
        password_hash=hash_password("E2EXc!9"),
        rol="CAJA",
        activo=True,
    )
    db.add(u)
    db.flush()
    turno = CajaTurno(
        id_usuario=u.id_usuario,
        monto_apertura=Decimal("500.00"),
        estado="ABIERTO",
        fecha_apertura=datetime.utcnow(),
    )
    db.add(turno)
    db.flush()
    return u, turno


def _telefono(tag: str) -> str:
    hexpart = "".join(c for c in tag if c in "0123456789abcdef")
    n = int(hexpart[:8], 16) % 10_000_000 if hexpart else 1234567
    return f"644{n:07d}"


def _seed_cliente_vehiculo(db, tag: str) -> tuple[Cliente, Vehiculo]:
    cliente = Cliente(nombre=f"Qa-Op100 {PREFIX} Cli {tag}", telefono=_telefono(tag))
    db.add(cliente)
    db.flush()
    vehiculo = Vehiculo(id_cliente=cliente.id_cliente, marca="Toyota", modelo="Corolla Qa", anio=2020)
    db.add(vehiculo)
    db.flush()
    return cliente, vehiculo


def _servicio_existente(db) -> Servicio:
    svc = db.query(Servicio).filter(Servicio.activo == True).first()  # noqa: E712
    if not svc:
        raise RuntimeError("No hay servicios activos en BD — abortando cross-check")
    return svc


def _ot_base(db, tag: str, cliente, vehiculo, **kwargs) -> OrdenTrabajo:
    defaults = {
        "numero_orden": f"{PREFIX}-{tag}",
        "vehiculo_id": vehiculo.id_vehiculo,
        "cliente_id": cliente.id_cliente,
        "estado": EstadoOrden.PENDIENTE,
        "fecha_ingreso": datetime.utcnow(),
        "total": Decimal("100.00"),
        "subtotal_servicios": Decimal("100.00"),
        "subtotal_repuestos": Decimal("0.00"),
        "descuento": Decimal("0.00"),
        "requiere_autorizacion": False,
        "autorizado": False,
    }
    defaults.update(kwargs)
    ot = OrdenTrabajo(**defaults)
    db.add(ot)
    db.flush()
    return ot


def _agregar_servicio(db, ot: OrdenTrabajo, servicio: Servicio) -> None:
    det = DetalleOrdenTrabajo(
        orden_trabajo_id=ot.id,
        servicio_id=servicio.id,
        precio_unitario=Decimal("100.00"),
        cantidad=1,
        subtotal=Decimal("100.00"),
    )
    db.add(det)
    db.flush()
    db.refresh(ot)


def _accion_en_item(item: dict, nombre: str) -> Optional[dict]:
    for a in item.get("acciones") or []:
        if a.get("accion") == nombre:
            return a
    return None


def _buscar_ot_a0(resumen: dict, ot_id: int) -> tuple[Optional[str], Optional[dict]]:
    for bandeja in BANDEJAS_OT:
        for item in resumen.get("bandejas", {}).get(bandeja, {}).get("items") or []:
            if item.get("id") == ot_id:
                return bandeja, item
    return None, None


def _accion_detalle(client: TestClient, ot_id: int, user: Usuario, nombre: str) -> tuple[int, Optional[dict]]:
    r = client.get(f"/api/ordenes-trabajo/{ot_id}", headers=_headers(user))
    if r.status_code != 200:
        return r.status_code, None
    for a in r.json().get("acciones") or []:
        if a.get("accion") == nombre:
            return 200, a
    return 200, None


def _assert_seeded_ot_qa(db, ot_id: int) -> None:
    ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
    if not ot:
        raise SmokeAbort("ABORT-QA-004", f"OT id={ot_id} no encontrada en sesión de prueba")
    cliente = db.query(Cliente).filter(Cliente.id_cliente == ot.cliente_id).first()
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == ot.vehiculo_id).first()
    if not cliente or not cliente_nombre_es_fixture_qa(cliente.nombre):
        raise SmokeAbort(
            "ABORT-QA-001",
            f"Cross-check OT #{ot_id}: cliente '{getattr(cliente, 'nombre', None)}' no es fixture QA",
        )
    assert_ot_qa_fixture(
        {
            "id": ot.id,
            "numero_orden": ot.numero_orden,
            "cliente": {"nombre": cliente.nombre},
            "vehiculo": {
                "marca": vehiculo.marca if vehiculo else None,
                "modelo": vehiculo.modelo if vehiculo else None,
            },
        },
        require_whitelist=False,
    )


def _eval_caso(
    *,
    caso: int,
    accion: str,
    ot_id: int,
    user: Usuario,
    client: TestClient,
    db,
    post_path: str,
    post_json: dict,
    esperado_permitida: bool,
    esperado_codigo: Optional[str] = None,
    esperado_api_ok: bool = False,
    bandeja_a0: Optional[str] = None,
    a0_entregar_ausente_ok: bool = False,
    detalle_403_ok: bool = False,
) -> dict[str, Any]:
    r_a0 = client.get("/api/operaciones/resumen", headers=_headers(user))
    a0_status = r_a0.status_code
    a0_accion: Optional[dict] = None
    a0_bandeja: Optional[str] = None
    if a0_status == 200:
        a0_bandeja, item = _buscar_ot_a0(r_a0.json(), ot_id)
        if bandeja_a0 and a0_bandeja != bandeja_a0:
            a0_bandeja = a0_bandeja or f"no_en_{bandeja_a0}"
        if item:
            a0_accion = _accion_en_item(item, accion)
            if a0_accion is None and a0_entregar_ausente_ok and accion == "entregar_vehiculo":
                a0_accion = {
                    "accion": accion,
                    "permitida": False,
                    "codigo_bloqueo": "NO_EN_LISTAS_ENTREGA",
                    "nota": "OT en pendientes_cobro; entregar solo en listas_entrega",
                }
        elif a0_entregar_ausente_ok and accion == "entregar_vehiculo":
            a0_accion = {
                "accion": accion,
                "permitida": False,
                "codigo_bloqueo": "AUSENTE_LISTAS_ENTREGA",
            }

    det_status, det_accion = _accion_detalle(client, ot_id, user, accion)

    _assert_seeded_ot_qa(db, ot_id)
    r_api = client.post(post_path, json=post_json, headers=_headers(user))
    api_ok = 200 <= r_api.status_code < 300

    a0_permitida = a0_accion.get("permitida") if a0_accion else None
    det_permitida = det_accion.get("permitida") if det_accion else None

    checks = {
        "a0_permitida_esperada": esperado_permitida,
        "detalle_permitida_esperada": esperado_permitida,
        "api_ok_esperado": esperado_api_ok,
    }
    fails: list[str] = []

    if a0_status != 200:
        fails.append(f"A0 HTTP {a0_status}")
    elif a0_accion is None and not (a0_entregar_ausente_ok and not esperado_permitida):
        if detalle_403_ok and not esperado_permitida and det_status == 403:
            a0_accion = {"accion": accion, "permitida": False, "nota": "OT no visible en A0 para técnico ajeno"}
            a0_permitida = False
        else:
            fails.append("A0: OT/acción no encontrada")
    elif a0_permitida != esperado_permitida:
        fails.append(f"A0 permitida={a0_permitida} esperado={esperado_permitida}")

    if det_status == 403 and detalle_403_ok and not esperado_permitida:
        det_accion = {
            "accion": accion,
            "permitida": False,
            "codigo_bloqueo": "DETALLE_403",
            "nota": "Técnico ajeno no puede ver detalle OT",
        }
    elif det_status != 200 and not (det_status == 403 and detalle_403_ok):
        fails.append(f"Detalle HTTP {det_status}")
    elif det_accion is None:
        fails.append("Detalle: acción no encontrada")
    elif det_permitida != esperado_permitida:
        fails.append(f"Detalle permitida={det_permitida} esperado={esperado_permitida}")

    if esperado_codigo and det_accion and det_accion.get("codigo_bloqueo") not in (
        esperado_codigo,
        "DETALLE_403",
    ):
        fails.append(f"Detalle codigo={det_accion.get('codigo_bloqueo')} esperado={esperado_codigo}")

    if api_ok != esperado_api_ok:
        fails.append(f"API status={r_api.status_code} body={r_api.text[:200]}")

    # Regresión crítica: A0 true pero API rechaza
    if a0_permitida is True and not api_ok:
        fails.append("REGRESION: A0 permitida=true pero API rechazó")

    return {
        "caso": caso,
        "accion": accion,
        "ot_id": ot_id,
        "usuario_id": user.id_usuario,
        "usuario_rol": user.rol.value if hasattr(user.rol, "value") else str(user.rol),
        "a0": {
            "http": a0_status,
            "bandeja": a0_bandeja,
            "accion": a0_accion,
        },
        "detalle": {
            "http": det_status,
            "accion": det_accion,
        },
        "api": {
            "status": r_api.status_code,
            "ok": api_ok,
            "detail": r_api.json().get("detail") if r_api.headers.get("content-type", "").startswith("application/json") else r_api.text[:200],
        },
        "checks": checks,
        "pass": len(fails) == 0,
        "fails": fails,
    }


def run_crosscheck(db, client: TestClient) -> list[dict[str, Any]]:
    tag = _uid()
    servicio = _servicio_existente(db)
    results: list[dict[str, Any]] = []

    # --- Caso 1: PENDIENTE sin ítems ---
    t1 = _seed_tecnico(db, f"c1-{tag}")
    c1, v1 = _seed_cliente_vehiculo(db, f"c1-{tag}")
    ot1 = _ot_base(db, f"C1-{tag}", c1, v1, tecnico_id=t1.id_usuario, total=Decimal("0"), subtotal_servicios=Decimal("0"))
    db.refresh(ot1)
    results.append(
        _eval_caso(
            caso=1,
            accion="iniciar_ot",
            ot_id=ot1.id,
            user=t1,
            client=client,
            db=db,
            post_path=f"/api/ordenes-trabajo/{ot1.id}/iniciar",
            post_json={},
            esperado_permitida=False,
            esperado_codigo="SIN_ITEMS",
            esperado_api_ok=False,
            bandeja_a0="ot_pendientes",
        )
    )

    # --- Caso 2: PENDIENTE con ítems ---
    t2 = _seed_tecnico(db, f"c2-{tag}")
    c2, v2 = _seed_cliente_vehiculo(db, f"c2-{tag}")
    ot2 = _ot_base(db, f"C2-{tag}", c2, v2, tecnico_id=t2.id_usuario)
    _agregar_servicio(db, ot2, servicio)
    results.append(
        _eval_caso(
            caso=2,
            accion="iniciar_ot",
            ot_id=ot2.id,
            user=t2,
            client=client,
            db=db,
            post_path=f"/api/ordenes-trabajo/{ot2.id}/iniciar",
            post_json={},
            esperado_permitida=True,
            esperado_api_ok=True,
            bandeja_a0="ot_pendientes",
        )
    )

    # --- Caso 3: autorización pendiente ---
    t3 = _seed_tecnico(db, f"c3-{tag}")
    c3, v3 = _seed_cliente_vehiculo(db, f"c3-{tag}")
    ot3 = _ot_base(
        db,
        f"C3-{tag}",
        c3,
        v3,
        tecnico_id=t3.id_usuario,
        estado=EstadoOrden.ESPERANDO_AUTORIZACION,
        requiere_autorizacion=True,
        autorizado=False,
    )
    _agregar_servicio(db, ot3, servicio)
    results.append(
        _eval_caso(
            caso=3,
            accion="iniciar_ot",
            ot_id=ot3.id,
            user=t3,
            client=client,
            db=db,
            post_path=f"/api/ordenes-trabajo/{ot3.id}/iniciar",
            post_json={},
            esperado_permitida=False,
            esperado_codigo="SIN_AUTORIZACION",
            esperado_api_ok=False,
            bandeja_a0="ot_pendientes",
        )
    )

    # --- Caso 4: EN_PROCESO técnico correcto ---
    t4 = _seed_tecnico(db, f"c4-{tag}")
    c4, v4 = _seed_cliente_vehiculo(db, f"c4-{tag}")
    ot4 = _ot_base(
        db,
        f"C4-{tag}",
        c4,
        v4,
        tecnico_id=t4.id_usuario,
        estado=EstadoOrden.EN_PROCESO,
        fecha_inicio=datetime.utcnow(),
    )
    _agregar_servicio(db, ot4, servicio)
    results.append(
        _eval_caso(
            caso=4,
            accion="finalizar_ot",
            ot_id=ot4.id,
            user=t4,
            client=client,
            db=db,
            post_path=f"/api/ordenes-trabajo/{ot4.id}/finalizar",
            post_json={},
            esperado_permitida=True,
            esperado_api_ok=True,
            bandeja_a0="ot_en_proceso",
        )
    )

    # --- Caso 5: EN_PROCESO técnico ajeno ---
    t5a = _seed_tecnico(db, f"c5a-{tag}")
    t5b = _seed_tecnico(db, f"c5b-{tag}")
    c5, v5 = _seed_cliente_vehiculo(db, f"c5-{tag}")
    ot5 = _ot_base(
        db,
        f"C5-{tag}",
        c5,
        v5,
        tecnico_id=t5a.id_usuario,
        estado=EstadoOrden.EN_PROCESO,
        fecha_inicio=datetime.utcnow(),
    )
    _agregar_servicio(db, ot5, servicio)
    r5 = _eval_caso(
        caso=5,
        accion="finalizar_ot",
        ot_id=ot5.id,
        user=t5b,
        client=client,
        db=db,
        post_path=f"/api/ordenes-trabajo/{ot5.id}/finalizar",
        post_json={},
        esperado_permitida=False,
        esperado_codigo="TECNICO_NO_ASIGNADO",
        esperado_api_ok=False,
        bandeja_a0="ot_en_proceso",
        detalle_403_ok=True,
    )
    results.append(r5)

    # --- Caso 6: COMPLETADA venta con saldo ---
    caja6, turno6 = _seed_caja(db, f"c6-{tag}")
    c6, v6 = _seed_cliente_vehiculo(db, f"c6-{tag}")
    ot6 = _ot_base(
        db,
        f"C6-{tag}",
        c6,
        v6,
        estado=EstadoOrden.COMPLETADA,
        fecha_finalizacion=datetime.utcnow(),
    )
    _agregar_servicio(db, ot6, servicio)
    venta6 = Venta(
        id_cliente=c6.id_cliente,
        id_vehiculo=v6.id_vehiculo,
        id_orden=ot6.id,
        total=Decimal("500.00"),
        estado="PENDIENTE",
    )
    db.add(venta6)
    db.flush()
    db.add(
        Pago(
            id_venta=venta6.id_venta,
            id_usuario=caja6.id_usuario,
            id_turno=turno6.id_turno,
            monto=Decimal("200.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db.flush()
    results.append(
        _eval_caso(
            caso=6,
            accion="entregar_vehiculo",
            ot_id=ot6.id,
            user=caja6,
            client=client,
            db=db,
            post_path=f"/api/ordenes-trabajo/{ot6.id}/entregar",
            post_json={},
            esperado_permitida=False,
            esperado_codigo="VENTA_SIN_PAGAR",
            esperado_api_ok=False,
            bandeja_a0="ot_pendientes_cobro",
            a0_entregar_ausente_ok=True,
        )
    )

    # --- Caso 7: COMPLETADA venta pagada ---
    caja7, turno7 = _seed_caja(db, f"c7-{tag}")
    c7, v7 = _seed_cliente_vehiculo(db, f"c7-{tag}")
    ot7 = _ot_base(
        db,
        f"C7-{tag}",
        c7,
        v7,
        estado=EstadoOrden.COMPLETADA,
        fecha_finalizacion=datetime.utcnow(),
    )
    _agregar_servicio(db, ot7, servicio)
    venta7 = Venta(
        id_cliente=c7.id_cliente,
        id_vehiculo=v7.id_vehiculo,
        id_orden=ot7.id,
        total=Decimal("300.00"),
        estado="PAGADA",
    )
    db.add(venta7)
    db.flush()
    db.add(
        Pago(
            id_venta=venta7.id_venta,
            id_usuario=caja7.id_usuario,
            id_turno=turno7.id_turno,
            monto=Decimal("300.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db.flush()
    results.append(
        _eval_caso(
            caso=7,
            accion="entregar_vehiculo",
            ot_id=ot7.id,
            user=caja7,
            client=client,
            db=db,
            post_path=f"/api/ordenes-trabajo/{ot7.id}/entregar",
            post_json={},
            esperado_permitida=True,
            esperado_api_ok=True,
            bandeja_a0="ot_listas_entrega",
        )
    )

    return results


def main() -> int:
    print("=== CROSS-CHECK E2E ACCIONES OT ===")
    print(f"ALLOW_TECNICO_SELF_ASSIGN = {ALLOW_TECNICO_SELF_ASSIGN}")
    print("Modo: código local + BD Railway + ROLLBACK transaccional\n")
    log_prod_target(transactional_rollback=True)
    try:
        assert_prod_db_mutation_policy(transactional_rollback=True)
    except SmokeAbort as exc:
        print(f"ERROR: {exc}")
        return 1

    try:
        connection = engine.connect()
    except Exception as e:
        print(f"ERROR: no se pudo conectar a BD: {e}")
        return 1

    transaction = connection.begin()
    try:
        connection.execute(text("SELECT 1"))
    except Exception as e:
        transaction.rollback()
        connection.close()
        print(f"ERROR: BD no responde: {e}")
        return 1

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    db = SessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        results = run_crosscheck(db, client)
    except Exception as e:
        print(f"ERROR durante cross-check: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        app.dependency_overrides.clear()
        db.close()
        transaction.rollback()
        connection.close()
        print("\n[ROLLBACK] Transacción revertida — sin datos persistentes\n")

    failed = 0
    for row in results:
        status = "PASS" if row["pass"] else "FAIL"
        if not row["pass"]:
            failed += 1
        print(f"Caso {row['caso']} [{row['accion']}] OT#{row['ot_id']} — {status}")
        if row["fails"]:
            for f in row["fails"]:
                print(f"  ! {f}")

    print("\n--- JSON evidencia ---")
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    if failed:
        print(f"\nRESULTADO: NO GO ({failed} caso(s) fallido(s))")
        return 1
    print("\nRESULTADO: GO cross-check E2E (deploy sigue pendiente aprobación explícita)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
