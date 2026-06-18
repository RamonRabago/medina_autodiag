"""
HOTFIX OT-FECHAS-V1: validación fecha_promesa vs fecha_ingreso (UTC legacy → local).

Unitarios: helpers en app.utils.fechas (sin MySQL).
Integración: PUT/POST órdenes de trabajo (requieren MySQL).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.config import settings
from app.utils.fechas import (
    MSG_FECHA_PROMESA_ANTERIOR_INGRESO,
    ingreso_ot_utc_naive_a_local_naive,
    validar_fecha_promesa_vs_ingreso,
)
from app.utils.jwt import create_access_token
from app.utils.security import hash_password

# Caso Railway documentado: ingreso UTC naive 13:17:22, promesa local 09:50 mismo día.
INGRESO_RAILWAY = datetime(2026, 6, 10, 13, 17, 22)
PROMESA_RAILWAY_VALIDA = datetime(2026, 6, 10, 9, 50, 0)


def test_promesa_mismo_dia_local_valida_no_se_rechaza():
    """Promesa posterior al ingreso convertido a local no lanza error."""
    validar_fecha_promesa_vs_ingreso(PROMESA_RAILWAY_VALIDA, INGRESO_RAILWAY)


def test_promesa_dia_anterior_se_rechaza():
    promesa = datetime(2026, 6, 9, 18, 0, 0)
    with pytest.raises(ValueError, match=MSG_FECHA_PROMESA_ANTERIOR_INGRESO):
        validar_fecha_promesa_vs_ingreso(promesa, INGRESO_RAILWAY)


def test_promesa_hora_anterior_real_se_rechaza():
    ingreso_local = ingreso_ot_utc_naive_a_local_naive(INGRESO_RAILWAY)
    promesa = ingreso_local.replace(hour=max(0, ingreso_local.hour - 1))
    with pytest.raises(ValueError, match=MSG_FECHA_PROMESA_ANTERIOR_INGRESO):
        validar_fecha_promesa_vs_ingreso(promesa, INGRESO_RAILWAY)


def test_regresion_railway_ingreso_utc_promesa_local_valida():
    """Caso OT-20260610-0001: antes fallaba por comparar naive UTC vs local."""
    ingreso_local = ingreso_ot_utc_naive_a_local_naive(INGRESO_RAILWAY)
    esperado = INGRESO_RAILWAY.replace(tzinfo=ZoneInfo("UTC")).astimezone(
        ZoneInfo(settings.TALLER_TIMEZONE)
    ).replace(tzinfo=None)
    assert ingreso_local == esperado
    assert PROMESA_RAILWAY_VALIDA > ingreso_local
    validar_fecha_promesa_vs_ingreso(PROMESA_RAILWAY_VALIDA, INGRESO_RAILWAY)


def _seed_usuario_caja(session):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre="Caja OT Fechas",
        email=f"ot_fechas_{uid}@test.medina",
        password_hash=hash_password("OtFechas!9"),
        rol="CAJA",
        activo=True,
    )
    session.add(usuario)
    session.flush()
    token = create_access_token(data={"sub": str(usuario.id_usuario), "rol": "CAJA"})
    return usuario, token


def _seed_cliente_vehiculo(session):
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo

    uid = uuid.uuid4().hex[:8]
    cliente = Cliente(nombre=f"Cli OT Fechas {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(id_cliente=cliente.id_cliente, marca="Nissan", modelo="Versa", anio=2020)
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _seed_ot(session, cliente_id, vehiculo_id, tecnico_id=None, **kwargs):
    from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo

    uid = uuid.uuid4().hex[:6]
    defaults = {
        "numero_orden": f"OT-FECHAS-{uid}",
        "vehiculo_id": vehiculo_id,
        "cliente_id": cliente_id,
        "tecnico_id": tecnico_id,
        "estado": EstadoOrden.EN_PROCESO,
        "fecha_ingreso": INGRESO_RAILWAY,
        "total": Decimal("0"),
        "subtotal_servicios": Decimal("0"),
        "subtotal_repuestos": Decimal("0"),
        "descuento": Decimal("0"),
    }
    defaults.update(kwargs)
    ot = OrdenTrabajo(**defaults)
    session.add(ot)
    session.flush()
    return ot


@pytest.mark.integration
def test_limpiar_fecha_promesa_guarda_null(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario_caja(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot(
        db_session_transactional,
        cliente.id_cliente,
        vehiculo.id_vehiculo,
        fecha_promesa=datetime(2026, 6, 12, 15, 0, 0),
    )
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.put(
        f"/api/ordenes-trabajo/{ot.id}",
        json={"fecha_promesa": None},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("fecha_promesa") is None


@pytest.mark.integration
def test_crear_ot_sin_promesa_sigue_ok(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario_caja(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={
            "cliente_id": cliente.id_cliente,
            "vehiculo_id": vehiculo.id_vehiculo,
            "motivo": "Revisión general sin promesa de entrega",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json().get("fecha_promesa") is None


@pytest.mark.integration
def test_editar_ot_campos_basicos_sin_promesa_sigue_ok(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario_caja(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.put(
        f"/api/ordenes-trabajo/{ot.id}",
        json={"prioridad": "ALTA", "observaciones_tecnico": "Sin cambio de promesa"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["prioridad"] == "ALTA"
    assert data.get("fecha_promesa") is None


@pytest.mark.integration
def test_api_rechaza_promesa_dia_anterior(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario_caja(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.put(
        f"/api/ordenes-trabajo/{ot.id}",
        json={"fecha_promesa": "2026-06-09T10:00:00"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert MSG_FECHA_PROMESA_ANTERIOR_INGRESO in r.json().get("detail", "")


@pytest.mark.integration
def test_api_acepta_promesa_railway(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario_caja(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot(db_session_transactional, cliente.id_cliente, vehiculo.id_vehiculo)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.put(
        f"/api/ordenes-trabajo/{ot.id}",
        json={"fecha_promesa": "2026-06-10T09:50:00"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("fecha_promesa") is not None
