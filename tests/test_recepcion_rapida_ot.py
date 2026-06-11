"""
Pruebas E2E de POST /api/ordenes-trabajo/recepcion-rapida (JWT + BD transaccional).

Requieren MySQL accesible. Si no hay BD, los tests se omiten (pytest.skip).
"""

import uuid

import pytest

from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"E2E {rol}",
        email=f"e2e_rr_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("E2ESecret!9"),
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
    cliente = Cliente(nombre=f"Cliente RR {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()

    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Nissan",
        modelo="Versa",
        anio=2020,
    )
    session.add(vehiculo)
    session.flush()

    return cliente, vehiculo


def _payload_recepcion(cliente_id: int, vehiculo_id: int, motivo: str = "Ruido en frenos al frenar"):
    return {
        "cliente_id": cliente_id,
        "vehiculo_id": vehiculo_id,
        "motivo": motivo,
        "prioridad": "NORMAL",
    }


@pytest.mark.integration
def test_recepcion_rapida_crea_ot_pendiente(client_transactional_db, db_session_transactional):
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    client = client_transactional_db
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(cliente.id_cliente, vehiculo.id_vehiculo),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado"] == "PENDIENTE"
    assert data["cliente_id"] == cliente.id_cliente
    assert data["vehiculo_id"] == vehiculo.id_vehiculo
    assert data["diagnostico_inicial"] == "Ruido en frenos al frenar"
    assert data["observaciones_cliente"] == "Ruido en frenos al frenar"
    assert float(data["total"]) == 0.0
    assert data["numero_orden"].startswith("OT-")


@pytest.mark.integration
def test_recepcion_rapida_empleado_puede_crear(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "EMPLEADO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(cliente.id_cliente, vehiculo.id_vehiculo),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text


@pytest.mark.integration
def test_recepcion_rapida_tecnico_prohibido(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "TECNICO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(cliente.id_cliente, vehiculo.id_vehiculo),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


@pytest.mark.integration
def test_recepcion_rapida_rechaza_sin_cliente_id(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    _, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={"vehiculo_id": vehiculo.id_vehiculo, "motivo": "Motivo válido de prueba"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_recepcion_rapida_rechaza_sin_vehiculo_id(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, _ = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={"cliente_id": cliente.id_cliente, "motivo": "Motivo válido de prueba"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_recepcion_rapida_rechaza_sin_motivo(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={"cliente_id": cliente.id_cliente, "vehiculo_id": vehiculo.id_vehiculo, "motivo": "corto"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.integration
def test_recepcion_rapida_cliente_inexistente(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    _, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(999999999, vehiculo.id_vehiculo),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.integration
def test_recepcion_rapida_vehiculo_inexistente(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, _ = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(cliente.id_cliente, 999999999),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.integration
def test_recepcion_rapida_vehiculo_no_pertenece_cliente(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente_a, _ = _seed_cliente_vehiculo(db_session_transactional)
    _, vehiculo_b = _seed_cliente_vehiculo(db_session_transactional)

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(cliente_a.id_cliente, vehiculo_b.id_vehiculo),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "no pertenece" in r.json().get("detail", "").lower()


@pytest.mark.integration
def test_recepcion_rapida_ot_minima_no_permite_cotizar_sin_items(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    headers = {"Authorization": f"Bearer {token}"}

    r_create = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json=_payload_recepcion(cliente.id_cliente, vehiculo.id_vehiculo),
        headers=headers,
    )
    assert r_create.status_code == 201
    orden_id = r_create.json()["id"]

    r_cot = client_transactional_db.post(
        f"/api/ordenes-trabajo/{orden_id}/marcar-cotizacion-enviada",
        headers=headers,
    )
    assert r_cot.status_code == 400
    assert "servicio o repuesto" in r_cot.json().get("detail", "").lower()
