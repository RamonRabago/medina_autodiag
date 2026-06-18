"""
Tests paridad métricas A0 — P5.3 Fase 1 Commit A.

Red de seguridad: harness legacy vs construir_resumen_operativo / API.
Sin fast path hasta Commit D.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.venta import Venta
from app.utils.jwt import create_access_token
from app.utils.security import hash_password
from tests.a0_metricas_paridad import (
    METRICAS_KEYS,
    assert_bandejas_total_coincide_metricas,
    assert_paridad_metricas,
    diff_metricas,
    extraer_metricas,
    metricas_desde_api_response,
    metricas_desde_construir_resumen,
    metricas_legacy_desde_bandejas,
    obtener_metricas_fast_path,
)


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"Paridad {rol}",
        email=f"paridad_a0_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("ParidadSecret!9"),
        rol=rol,
        activo=True,
    )
    session.add(usuario)
    session.flush()
    token = create_access_token(data={"sub": str(usuario.id_usuario), "rol": rol})
    return usuario, token


def _seed_cliente_vehiculo(session):
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo

    uid = uuid.uuid4().hex[:8]
    cliente = Cliente(nombre=f"Cliente Paridad {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Toyota",
        modelo="Corolla",
        anio=2019,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _seed_turno_caja(session, id_usuario: int):
    from app.models.caja_turno import CajaTurno

    turno = CajaTurno(
        id_usuario=id_usuario,
        monto_apertura=Decimal("500.00"),
        estado="ABIERTO",
        fecha_apertura=datetime.utcnow(),
    )
    session.add(turno)
    session.flush()
    return turno


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- unitarios (sin BD) ---


def test_metricas_keys_contrato_a0():
    assert len(METRICAS_KEYS) == 10
    assert "ot_pendientes_cobro" in METRICAS_KEYS
    assert "ventas_saldo_pendiente" in METRICAS_KEYS


def test_extraer_metricas_defaults_cero():
    assert extraer_metricas({}) == {k: 0 for k in METRICAS_KEYS}


def test_diff_metricas_sin_diferencias():
    m = {k: 1 for k in METRICAS_KEYS}
    assert diff_metricas(m, m) == "(sin diferencias)"


def test_diff_metricas_con_diferencias():
    a = {k: 0 for k in METRICAS_KEYS}
    b = dict(a)
    b["ot_pendientes_cobro"] = 3
    texto = diff_metricas(a, b)
    assert "ot_pendientes_cobro" in texto
    assert "legacy=0" in texto
    assert "actual=3" in texto


def test_assert_paridad_metricas_ok():
    m = {k: 0 for k in METRICAS_KEYS}
    assert_paridad_metricas(m, m)


def test_assert_paridad_metricas_falla_con_contexto():
    a = {k: 0 for k in METRICAS_KEYS}
    b = dict(a)
    b["ot_en_proceso"] = 1
    with pytest.raises(AssertionError, match="rol=TEST"):
        assert_paridad_metricas(a, b, context="rol=TEST")


def test_fast_path_aun_no_implementado():
    with pytest.raises(NotImplementedError, match="Commit D"):
        obtener_metricas_fast_path(None, None)  # type: ignore[arg-type]


# --- integración: harness vs servicio / API ---


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["ADMIN", "CAJA", "TECNICO", "EMPLEADO"])
def test_paridad_legacy_harness_vs_construir_resumen_light(
    db_session_transactional,
    rol: str,
):
    usuario, _ = _seed_usuario(db_session_transactional, rol)
    legacy = metricas_legacy_desde_bandejas(db_session_transactional, usuario)
    servicio = metricas_desde_construir_resumen(
        db_session_transactional,
        usuario,
        incluir_items=False,
        limit_items=1,
    )
    assert_paridad_metricas(legacy, servicio, context=f"rol={rol} harness vs servicio light")


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["ADMIN", "CAJA", "TECNICO", "EMPLEADO"])
def test_paridad_legacy_harness_vs_api_incluir_items_false(
    client_transactional_db,
    db_session_transactional,
    rol: str,
):
    usuario, token = _seed_usuario(db_session_transactional, rol)
    legacy = metricas_legacy_desde_bandejas(db_session_transactional, usuario)

    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"incluir_items": False, "limit_items": 1},
        headers=_headers(token),
    )
    assert r.status_code == 200
    api_metricas = metricas_desde_api_response(r.json())
    assert_paridad_metricas(legacy, api_metricas, context=f"rol={rol} harness vs API light")


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["ADMIN", "CAJA"])
def test_bandejas_total_igual_metricas_modo_light(
    client_transactional_db,
    db_session_transactional,
    rol: str,
):
    _, token = _seed_usuario(db_session_transactional, rol)
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"incluir_items": False, "limit_items": 30},
        headers=_headers(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert all(len((data.get("bandejas") or {}).get(k, {}).get("items") or []) == 0 for k in (
        "citas_pendientes_asistencia",
        "citas_convertibles",
        "ot_pendientes",
        "ot_en_proceso",
        "ot_completadas",
        "ot_pendientes_cobro",
        "ot_listas_entrega",
        "ventas_saldo_pendiente",
    ))
    assert_bandejas_total_coincide_metricas(data, context=f"rol={rol} API light")


@pytest.mark.integration
def test_paridad_legacy_con_fixture_o1_v1_dedup(
    db_session_transactional,
):
    """Golden path P4.0 — métricas O1/V1 deben coincidir harness vs servicio light."""
    usuario, _ = _seed_usuario(db_session_transactional, "CAJA")
    turno = _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    ot = OrdenTrabajo(
        numero_orden=f"OT-PAR-{uuid.uuid4().hex[:8]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.COMPLETADA,
        fecha_ingreso=datetime.utcnow(),
        fecha_finalizacion=datetime.utcnow(),
        total=Decimal("1000.00"),
        subtotal_servicios=Decimal("1000.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    db_session_transactional.add(ot)
    db_session_transactional.flush()

    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("1000.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()

    pago = Pago(
        id_venta=venta.id_venta,
        id_usuario=usuario.id_usuario,
        id_turno=turno.id_turno,
        monto=Decimal("150.00"),
        metodo="EFECTIVO",
        fecha=datetime.utcnow(),
    )
    db_session_transactional.add(pago)
    db_session_transactional.flush()

    legacy = metricas_legacy_desde_bandejas(db_session_transactional, usuario)
    servicio = metricas_desde_construir_resumen(
        db_session_transactional,
        usuario,
        incluir_items=False,
    )
    assert_paridad_metricas(legacy, servicio, context="fixture O1 parcial dedup V1")
    assert servicio["ot_pendientes_cobro"] >= 1
    assert servicio["ventas_saldo_pendiente"] == legacy["ventas_saldo_pendiente"]


@pytest.mark.integration
@pytest.mark.skip(reason="P5.3 Commit D: activar cuando exista fast path A0")
def test_paridad_fast_path_vs_legacy_pendiente_commit_d(
    db_session_transactional,
):
    """Gate futuro: obtener_metricas_fast_path() == metricas_legacy_desde_bandejas()."""
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    legacy = metricas_legacy_desde_bandejas(db_session_transactional, usuario)
    fast = obtener_metricas_fast_path(db_session_transactional, usuario)
    assert_paridad_metricas(legacy, fast, context="fast path vs legacy")
