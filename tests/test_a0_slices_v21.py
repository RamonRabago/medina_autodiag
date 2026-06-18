"""
Tests paridad A0 v2.1 slices — UX-1B.0.

Requiere MySQL accesible (pytest.mark.integration).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.venta import Venta
from app.services.operaciones_service import (
    BANDEJAS_WHITELIST,
    GRUPOS_SLICE_VALIDOS,
    MAX_BANDEJAS_SLICE,
    OperacionesSliceParamError,
    construir_resumen_operativo,
    validar_params_slice,
)
from app.utils.jwt import create_access_token
from app.utils.security import hash_password
from tests.a0_metricas_paridad import assert_paridad_metricas, extraer_metricas
from tests.a0_slices_paridad import (
    BANDEJA_KEYS,
    assert_bandejas_total_coincide_metricas,
    assert_bandeja_items_paridad,
    assert_meta_legacy,
    assert_meta_slice,
    assert_slice_bandeja_vacia_no_hidratada,
    assert_slice_paridad_completa_bandeja,
    assert_slice_paridad_metricas_vs_heavy,
    assert_slice_paridad_totales_vs_heavy,
    obtener_resumen_heavy,
    obtener_resumen_slice_bandejas,
    obtener_resumen_slice_grupo,
)


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"Slice {rol}",
        email=f"slice_v21_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("SliceSecret!9"),
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
    cliente = Cliente(nombre=f"Cliente Slice {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Honda",
        modelo="Civic",
        anio=2021,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _seed_ot(session, cliente, vehiculo, estado, tecnico_id=None):
    ot = OrdenTrabajo(
        numero_orden=f"OT-SLICE-{uuid.uuid4().hex[:8]}",
        cliente_id=cliente.id_cliente,
        vehiculo_id=vehiculo.id_vehiculo,
        tecnico_id=tecnico_id,
        estado=estado,
        total=Decimal("500.00"),
        subtotal_servicios=Decimal("500.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
        fecha_ingreso=datetime.utcnow(),
    )
    session.add(ot)
    session.flush()
    return ot


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- validación params (unitario) ---


def test_max_bandejas_slice_constant():
    assert MAX_BANDEJAS_SLICE == 8
    assert len(BANDEJAS_WHITELIST) == 8


def test_validar_params_slice_sin_slice():
    assert validar_params_slice(None, None, True) is None


def test_validar_params_slice_grupo_valido():
    assert validar_params_slice("caja", None, True) == [
        "ot_pendientes_cobro",
        "ot_listas_entrega",
        "ventas_saldo_pendiente",
    ]


def test_validar_params_slice_bandejas_csv():
    result = validar_params_slice(None, "ot_en_proceso,ot_pendientes", True)
    assert result == ["ot_en_proceso", "ot_pendientes"]


def test_validar_params_slice_deduplica_bandejas():
    result = validar_params_slice(None, "ot_en_proceso,ot_en_proceso", True)
    assert result == ["ot_en_proceso"]


def test_validar_params_slice_grupo_invalido():
    with pytest.raises(OperacionesSliceParamError, match="grupo"):
        validar_params_slice("invalido", None, True)


def test_validar_params_slice_bandeja_invalida():
    with pytest.raises(OperacionesSliceParamError, match="bandejas"):
        validar_params_slice(None, "no_existe", True)


def test_validar_params_slice_bandejas_vacio():
    with pytest.raises(OperacionesSliceParamError, match="bandejas"):
        validar_params_slice(None, "", True)


def test_validar_params_slice_demasiadas_bandejas():
    csv = ",".join(["ot_pendientes"] * (MAX_BANDEJAS_SLICE + 1))
    with pytest.raises(OperacionesSliceParamError, match=str(MAX_BANDEJAS_SLICE)):
        validar_params_slice(None, csv, True)


def test_validar_params_slice_conflicto_incluir_items_false():
    with pytest.raises(OperacionesSliceParamError, match="incluir_items"):
        validar_params_slice("caja", None, False)


def test_validar_params_slice_bandejas_precede_grupo():
    result = validar_params_slice("caja", "ot_en_proceso", True)
    assert result == ["ot_en_proceso"]


def test_grupos_slice_validos():
    assert GRUPOS_SLICE_VALIDOS == frozenset({"caja", "recepcion", "mi_taller", "refacciones"})


# --- paridad integración ---


@pytest.mark.integration
@pytest.mark.parametrize("bandeja_key", list(BANDEJA_KEYS))
def test_paridad_slice_bandeja_individual_vs_heavy(
    db_session_transactional, bandeja_key: str
):
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    heavy = obtener_resumen_heavy(db_session_transactional, usuario)
    slice_res = obtener_resumen_slice_bandejas(
        db_session_transactional, usuario, [bandeja_key]
    )
    assert_meta_slice(slice_res)
    assert slice_res["meta"]["bandejas_solicitadas"] == [bandeja_key]
    assert_slice_paridad_metricas_vs_heavy(heavy, slice_res, context=bandeja_key)
    assert_slice_paridad_totales_vs_heavy(heavy, slice_res, context=bandeja_key)
    assert_bandeja_items_paridad(heavy, slice_res, bandeja_key, context=bandeja_key)
    for key in BANDEJA_KEYS:
        if key != bandeja_key:
            assert_slice_bandeja_vacia_no_hidratada(slice_res, key)


@pytest.mark.integration
@pytest.mark.parametrize(
    "grupo,expected_hidratadas",
    [
        ("caja", {"ot_pendientes_cobro", "ot_listas_entrega", "ventas_saldo_pendiente"}),
        ("recepcion", {"citas_pendientes_asistencia", "citas_convertibles"}),
        ("mi_taller", {"ot_pendientes", "ot_en_proceso", "ot_completadas"}),
        ("refacciones", set()),
    ],
)
def test_paridad_slice_grupo_vs_heavy(
    db_session_transactional, grupo: str, expected_hidratadas: set[str]
):
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    heavy = obtener_resumen_heavy(db_session_transactional, usuario)
    slice_res = obtener_resumen_slice_grupo(db_session_transactional, usuario, grupo)
    assert_meta_slice(slice_res, grupo=grupo)
    assert set(slice_res["meta"]["bandejas_hidratadas"]) == expected_hidratadas
    assert_slice_paridad_metricas_vs_heavy(heavy, slice_res, context=grupo)
    assert_slice_paridad_totales_vs_heavy(heavy, slice_res, context=grupo)
    for key in expected_hidratadas:
        assert_bandeja_items_paridad(heavy, slice_res, key, context=grupo)


@pytest.mark.integration
def test_slice_metricas_coinciden_capa0(db_session_transactional):
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    capa0 = construir_resumen_operativo(
        db_session_transactional, usuario, limit_items=1, incluir_items=False
    )
    slice_res = obtener_resumen_slice_grupo(db_session_transactional, usuario, "caja")
    assert_paridad_metricas(
        extraer_metricas(capa0),
        extraer_metricas(slice_res),
        context="capa0 vs slice caja",
    )


@pytest.mark.integration
def test_slice_bandejas_total_coincide_metricas(db_session_transactional):
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    slice_res = obtener_resumen_slice_grupo(db_session_transactional, usuario, "mi_taller")
    assert_bandejas_total_coincide_metricas(slice_res, context="slice mi_taller")


@pytest.mark.integration
def test_slice_v1_dedup_sin_o1_en_request(db_session_transactional):
    """V1 slice debe excluir OT en O1 aunque O1 no esté en bandejas solicitadas."""
    from tests.test_a0_contadores_financieros import _seed_ot_completada, _seed_turno

    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("900.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("100.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    heavy = obtener_resumen_heavy(db_session_transactional, usuario)
    slice_res = obtener_resumen_slice_bandejas(
        db_session_transactional, usuario, ["ventas_saldo_pendiente"]
    )
    assert_slice_paridad_completa_bandeja(
        heavy, slice_res, "ventas_saldo_pendiente", context="V1 dedup"
    )
    v1_ids = [i["id"] for i in slice_res["bandejas"]["ventas_saldo_pendiente"]["items"]]
    assert venta.id_venta not in v1_ids


@pytest.mark.integration
def test_slice_tecnico_no_hidrata_financieras(db_session_transactional):
    usuario, _ = _seed_usuario(db_session_transactional, "TECNICO")
    slice_res = obtener_resumen_slice_grupo(db_session_transactional, usuario, "caja")
    assert_meta_slice(slice_res, grupo="caja")
    assert slice_res["meta"]["bandejas_hidratadas"] == []
    for key in ("ot_pendientes_cobro", "ot_listas_entrega", "ventas_saldo_pendiente"):
        assert slice_res["bandejas"][key]["items"] == []
        assert slice_res["bandejas"][key]["total"] == 0


@pytest.mark.integration
def test_slice_tecnico_ot_en_proceso_paridad(db_session_transactional):
    usuario, _ = _seed_usuario(db_session_transactional, "TECNICO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    _seed_ot(
        db_session_transactional,
        cliente,
        vehiculo,
        EstadoOrden.EN_PROCESO,
        tecnico_id=usuario.id_usuario,
    )
    heavy = obtener_resumen_heavy(db_session_transactional, usuario)
    slice_res = obtener_resumen_slice_bandejas(
        db_session_transactional, usuario, ["ot_en_proceso"]
    )
    assert_slice_paridad_completa_bandeja(
        heavy, slice_res, "ot_en_proceso", context="TECNICO en_proceso"
    )


@pytest.mark.integration
def test_legacy_heavy_meta_sin_parcial(db_session_transactional):
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    heavy = obtener_resumen_heavy(db_session_transactional, usuario)
    assert_meta_legacy(heavy)


@pytest.mark.integration
def test_legacy_capa0_meta_v2(db_session_transactional):
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    capa0 = construir_resumen_operativo(
        db_session_transactional, usuario, limit_items=1, incluir_items=False
    )
    assert capa0["meta"]["version_contrato"] == "a0-v2"
    assert capa0["meta"].get("parcial") in (None, False)


# --- HTTP ---


@pytest.mark.integration
def test_api_slice_grupo_caja_200(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"limit_items": 15, "grupo": "caja"},
        headers=_headers(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["version_contrato"] == "a0-v2.1"
    assert data["meta"]["parcial"] is True
    assert data["meta"]["grupo"] == "caja"


@pytest.mark.integration
def test_api_slice_bandeja_200(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "TECNICO")
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"limit_items": 30, "bandejas": "ot_en_proceso"},
        headers=_headers(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["version_contrato"] == "a0-v2.1"
    assert data["meta"]["bandejas_solicitadas"] == ["ot_en_proceso"]


@pytest.mark.integration
def test_api_slice_conflicto_incluir_items_422(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"incluir_items": False, "grupo": "caja"},
        headers=_headers(token),
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_api_slice_grupo_invalido_422(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"grupo": "invalido"},
        headers=_headers(token),
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_api_legacy_heavy_sin_slice(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"limit_items": 30, "incluir_items": True},
        headers=_headers(token),
    )
    assert r.status_code == 200
    assert r.json()["meta"]["version_contrato"] == "a0-v2"
    assert r.json()["meta"].get("parcial") in (None, False)


@pytest.mark.integration
def test_api_legacy_capa0(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get(
        "/api/operaciones/resumen",
        params={"limit_items": 1, "incluir_items": False},
        headers=_headers(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["version_contrato"] == "a0-v2"
    assert all(len(b["items"]) == 0 for b in data["bandejas"].values())
