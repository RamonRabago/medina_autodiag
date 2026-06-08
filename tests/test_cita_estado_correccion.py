"""
Pruebas E2E de PATCH /api/citas/{id}/estado (Fase 1 corrección estados).

Requieren MySQL accesible y migración b8c9d0e1f2a3 aplicada.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from app.models.auditoria import Auditoria
from app.models.cita import Cita, EstadoCita, TipoCita
from app.models.cita_estado_historial import CitaEstadoHistorial
from app.utils.fechas import ahora_local
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"E2E EST {rol}",
        email=f"e2e_est_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente EST {uid}", telefono=f"644{uid[:7]}")
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
    estado=EstadoCita.CONFIRMADA,
    fecha_hora=None,
    id_orden=None,
):
    if fecha_hora is None:
        fecha_hora = ahora_local() + timedelta(days=2)
    cita = Cita(
        id_cliente=cliente_id,
        id_vehiculo=vehiculo_id,
        fecha_hora=fecha_hora,
        tipo=TipoCita.REVISION,
        estado=estado,
        motivo=motivo,
        id_orden=id_orden,
    )
    session.add(cita)
    session.flush()
    return cita


def _patch_estado(client, cita_id, token, payload):
    return client.patch(
        f"/api/citas/{cita_id}/estado",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def _historial_count(session, id_cita):
    return (
        session.query(CitaEstadoHistorial)
        .filter(CitaEstadoHistorial.id_cita == id_cita)
        .count()
    )


@pytest.mark.integration
def test_put_rechaza_campo_estado(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.put(
        f"/api/citas/{cita.id_cita}",
        json={"estado": "SI_ASISTIO"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "PATCH" in r.json().get("detail", "")


@pytest.mark.integration
def test_patch_confirmada_a_si_asistio(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    antes = _historial_count(db_session_transactional, cita.id_cita)

    r = _patch_estado(client_transactional_db, cita.id_cita, token, {"estado_nuevo": "SI_ASISTIO"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "SI_ASISTIO"
    assert r.json()["estado_origen_cierre"] == "SI_ASISTIO"
    assert _historial_count(db_session_transactional, cita.id_cita) == antes + 1


@pytest.mark.integration
def test_patch_confirmada_a_no_asistio(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "EMPLEADO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)

    r = _patch_estado(client_transactional_db, cita.id_cita, token, {"estado_nuevo": "NO_ASISTIO"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "NO_ASISTIO"
    assert r.json()["estado_origen_cierre"] == "NO_ASISTIO"


@pytest.mark.integration
def test_patch_correccion_si_asistio_a_no_asistio_exige_motivo(
    client_transactional_db, db_session_transactional
):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.SI_ASISTIO,
        fecha_hora=ahora_local() - timedelta(hours=2),
    )

    r = _patch_estado(client_transactional_db, cita.id_cita, token, {"estado_nuevo": "NO_ASISTIO"})
    assert r.status_code == 400


@pytest.mark.integration
def test_patch_tecnico_no_corrige_si_asistio(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "TECNICO")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.SI_ASISTIO,
        fecha_hora=ahora_local() - timedelta(hours=1),
    )

    r = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Marcado por error en recepción",
        },
    )
    assert r.status_code == 403


@pytest.mark.integration
def test_patch_caja_no_corrige_fuera_ventana_24h(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.SI_ASISTIO,
        fecha_hora=ahora_local() - timedelta(hours=48),
    )

    r = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Error de captura en recepción",
        },
    )
    assert r.status_code == 403


@pytest.mark.integration
def test_patch_admin_corrige_fuera_ventana_24h(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.SI_ASISTIO,
        fecha_hora=ahora_local() - timedelta(hours=48),
    )

    r = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Error de captura en recepción",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "NO_ASISTIO"


@pytest.mark.integration
def test_patch_con_id_orden_solo_admin(client_transactional_db, db_session_transactional):
    _, token_caja = _seed_usuario(db_session_transactional, "CAJA")
    _, token_admin = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        fecha_hora=ahora_local() - timedelta(hours=1),
    )
    headers_caja = {"Authorization": f"Bearer {token_caja}"}

    r_ot = client_transactional_db.post(
        f"/api/citas/{cita.id_cita}/convertir-orden",
        headers=headers_caja,
    )
    assert r_ot.status_code == 201, r_ot.text

    db_session_transactional.refresh(cita)
    assert cita.id_orden is not None

    r_caja = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token_caja,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Intento corrección con OT",
        },
    )
    assert r_caja.status_code == 403

    r_admin = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token_admin,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Corrección administrativa con OT",
        },
    )
    assert r_admin.status_code == 200, r_admin.text


@pytest.mark.integration
def test_patch_genera_historial_y_auditoria(client_transactional_db, db_session_transactional):
    usuario, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.SI_ASISTIO,
        fecha_hora=ahora_local() - timedelta(hours=1),
    )

    r = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Se marcó asistencia por error",
        },
    )
    assert r.status_code == 200, r.text

    eventos = (
        db_session_transactional.query(CitaEstadoHistorial)
        .filter(CitaEstadoHistorial.id_cita == cita.id_cita)
        .all()
    )
    assert any(e.estado_nuevo == "NO_ASISTIO" and e.origen == "MANUAL" for e in eventos)

    audit = (
        db_session_transactional.query(Auditoria)
        .filter(
            Auditoria.modulo == "CITA",
            Auditoria.accion == "CITA_ESTADO_CORREGIDO",
            Auditoria.id_referencia == cita.id_cita,
        )
        .order_by(Auditoria.id_auditoria.desc())
        .first()
    )
    assert audit is not None


@pytest.mark.integration
def test_estado_origen_cierre_solo_una_vez(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)

    r1 = _patch_estado(client_transactional_db, cita.id_cita, token, {"estado_nuevo": "SI_ASISTIO"})
    assert r1.status_code == 200
    assert r1.json()["estado_origen_cierre"] == "SI_ASISTIO"

    r2 = _patch_estado(
        client_transactional_db,
        cita.id_cita,
        token,
        {
            "estado_nuevo": "NO_ASISTIO",
            "motivo_codigo": "ERROR_CAPTURA",
            "motivo_detalle": "Corrección posterior sin cambiar origen",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["estado_origen_cierre"] == "SI_ASISTIO"

    db_session_transactional.refresh(cita)
    assert cita.estado_origen_cierre == EstadoCita.SI_ASISTIO


@pytest.mark.integration
def test_get_detalle_incluye_estado_meta(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.SI_ASISTIO,
        fecha_hora=ahora_local() - timedelta(hours=1),
    )
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.get(f"/api/citas/{cita.id_cita}", headers=headers)
    assert r.status_code == 200
    meta = r.json().get("estado_meta")
    assert meta is not None
    assert "transiciones_permitidas" in meta
    assert meta.get("estado_editable") is True


@pytest.mark.integration
def test_convertir_no_asistio_sigue_bloqueado(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        estado=EstadoCita.NO_ASISTIO,
    )
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 409


@pytest.mark.integration
def test_convertir_ot_registra_historial_automatico(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    cita = _seed_cita(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(f"/api/citas/{cita.id_cita}/convertir-orden", headers=headers)
    assert r.status_code == 201, r.text

    eventos = (
        db_session_transactional.query(CitaEstadoHistorial)
        .filter(
            CitaEstadoHistorial.id_cita == cita.id_cita,
            CitaEstadoHistorial.origen == "CONVERTIR_OT",
        )
        .all()
    )
    assert len(eventos) >= 1
    assert eventos[0].estado_nuevo == "SI_ASISTIO"

    db_session_transactional.refresh(cita)
    assert cita.estado_origen_cierre == EstadoCita.SI_ASISTIO
