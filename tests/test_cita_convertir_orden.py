"""
Pruebas E2E de POST /api/citas/{id}/convertir-orden (P2 Cita → OT).

Requieren MySQL accesible. Si no hay BD, los tests se omiten (pytest.skip).
"""
import uuid
from datetime import datetime, timedelta

import pytest

from app.models.cita import Cita, EstadoCita, TipoCita
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"E2E {rol}",
        email=f"e2e_cot_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente COT {uid}", telefono=f"644{uid[:7]}")
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


def _seed_cita(
    session,
    cliente_id: int,
    vehiculo_id=None,
    *,
    motivo="Revisión general de frenos delanteros",
    notas=None,
    estado=EstadoCita.CONFIRMADA,
):
    cita = Cita(
        id_cliente=cliente_id,
        id_vehiculo=vehiculo_id,
        fecha_hora=datetime.utcnow() + timedelta(days=1),
        tipo=TipoCita.REVISION,
        estado=estado,
        motivo=motivo,
        notas=notas,
    )
    session.add(cita)
    session.flush()
    return cita


@pytest.mark.integration
def test_convertir_cita_valida_crea_ot_pendiente(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    motivo = "Revisión general de frenos delanteros"
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo, motivo=motivo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 201, r.text
    ot = r.json()
    assert ot["estado"] == "PENDIENTE"
    assert ot["cliente_id"] == cliente.id_cliente
    assert ot["vehiculo_id"] == vehiculo.id_vehiculo
    assert ot["diagnostico_inicial"] == motivo
    assert ot["observaciones_cliente"] == motivo

    db_session_transactional.refresh(cita)
    assert cita.id_orden == ot["id"]
    assert cita.estado == EstadoCita.SI_ASISTIO


@pytest.mark.integration
def test_convertir_cita_copia_motivo_y_notas(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        motivo="Cambio de aceite",
        notas="Cliente pide filtro premium",
    )
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 201, r.text
    esperado = "Cambio de aceite — Cliente pide filtro premium"
    assert r.json()["diagnostico_inicial"] == esperado


@pytest.mark.integration
def test_convertir_cita_cancelada_rechaza(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "EMPLEADO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.CANCELADA,
    )
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 400
    assert "cancelada" in r.json().get("detail", "").lower()


@pytest.mark.integration
def test_convertir_cita_ya_convertida_rechaza(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r1 = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r1.status_code == 201
    id_orden = r1.json()["id"]

    r2 = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r2.status_code == 409
    detail = r2.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("accion") == "VER_ORDEN"
    assert detail.get("id_orden") == id_orden


@pytest.mark.integration
def test_convertir_cita_sin_vehiculo_accion_recepcion(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, _ = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo_id=None)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 409
    detail = r.json().get("detail")
    assert detail.get("accion") == "COMPLETAR_RECEPCION"
    assert f"cita_id={cita.id_cita}" in detail.get("redirect", "")


@pytest.mark.integration
def test_convertir_cita_tecnico_prohibido(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "TECNICO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 403


@pytest.mark.integration
def test_convertir_cita_inexistente_404(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post("/api/citas/999999999/convertir-orden", headers=headers)
    assert r.status_code == 404


@pytest.mark.integration
def test_recepcion_rapida_con_cita_id_vincula_cita(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "EMPLEADO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo_id=None)
    headers = {"Authorization": f"Bearer {token}"}
    motivo = "Diagnóstico de ruido en suspensión"

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={
            "cliente_id": cliente.id_cliente,
            "vehiculo_id": vehiculo.id_vehiculo,
            "motivo": motivo,
            "cita_id": cita.id_cita,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    ot_id = r.json()["id"]

    db_session_transactional.refresh(cita)
    assert cita.id_orden == ot_id
    assert cita.estado == EstadoCita.SI_ASISTIO


@pytest.mark.integration
def test_post_estandar_ot_no_cambia(client_transactional_db, db_session_transactional):
    """POST /api/ordenes-trabajo/ (wizard) sigue disponible sin regresión."""
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/",
        json={
            "cliente_id": cliente.id_cliente,
            "vehiculo_id": vehiculo.id_vehiculo,
            "diagnostico_inicial": "Diagnóstico estándar de prueba E2E",
            "prioridad": "NORMAL",
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text


@pytest.mark.integration
def test_recepcion_rapida_walkin_sin_cita_id_sigue_funcionando(
    client_transactional_db, db_session_transactional
):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={
            "cliente_id": cliente.id_cliente,
            "vehiculo_id": vehiculo.id_vehiculo,
            "motivo": "Walk-in sin cita previa",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "PENDIENTE"
