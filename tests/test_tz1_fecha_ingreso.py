"""TZ-1: fecha_ingreso OT como hora local naive del taller."""

from datetime import datetime

import pytest

from app.utils.fechas import (
    FECHA_INGRESO_LOCAL_DESDE,
    ahora_local_naive,
    ingreso_ot_a_local_naive,
    isoformat_fecha_ingreso_ot,
    validar_fecha_promesa_vs_ingreso,
)

INGRESO_LEGACY_UTC = datetime(2026, 6, 10, 13, 17, 22)
INGRESO_TZ1_LOCAL = datetime(2026, 6, 17, 15, 30, 0)


def test_ahora_local_naive_sin_tzinfo():
    dt = ahora_local_naive()
    assert dt.tzinfo is None
    assert isinstance(dt, datetime)


def test_isoformat_fecha_ingreso_ot_sin_z():
    s = isoformat_fecha_ingreso_ot(datetime(2026, 6, 17, 14, 31, 5))
    assert s == "2026-06-17T14:31:05"
    assert not s.endswith("Z")


def test_ingreso_legacy_sigue_convirtiendo_desde_utc():
    local = ingreso_ot_a_local_naive(INGRESO_LEGACY_UTC)
    assert INGRESO_LEGACY_UTC < FECHA_INGRESO_LOCAL_DESDE
    assert local.hour == 7 and local.minute == 17


def test_ingreso_tz1_no_convierte_desde_utc():
    local = ingreso_ot_a_local_naive(INGRESO_TZ1_LOCAL)
    assert INGRESO_TZ1_LOCAL >= FECHA_INGRESO_LOCAL_DESDE
    assert local == INGRESO_TZ1_LOCAL


def test_validar_promesa_con_ingreso_tz1_local():
    promesa = datetime(2026, 6, 17, 16, 0, 0)
    validar_fecha_promesa_vs_ingreso(promesa, INGRESO_TZ1_LOCAL)


def test_validar_promesa_anterior_ingreso_tz1_local_falla():
    promesa = datetime(2026, 6, 17, 14, 0, 0)
    with pytest.raises(ValueError):
        validar_fecha_promesa_vs_ingreso(promesa, INGRESO_TZ1_LOCAL)


def test_validar_promesa_legacy_railway_sigue_ok():
    promesa = datetime(2026, 6, 10, 9, 50, 0)
    validar_fecha_promesa_vs_ingreso(promesa, INGRESO_LEGACY_UTC)


@pytest.mark.integration
def test_recepcion_rapida_fecha_ingreso_es_local_taller(client_transactional_db, db_session_transactional):
    """OT nueva: fecha_ingreso en API debe ser hora local naive del taller (sin Z)."""
    import uuid
    from datetime import timedelta

    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo
    from app.models.usuario import Usuario
    from app.utils.jwt import create_access_token
    from app.utils.security import hash_password

    uid = uuid.uuid4().hex[:8]
    usuario = Usuario(
        nombre="TZ1 Recep",
        email=f"tz1_{uid}@test.medina",
        password_hash=hash_password("Tz1Test!9"),
        rol="CAJA",
        activo=True,
    )
    db_session_transactional.add(usuario)
    db_session_transactional.flush()
    cliente = Cliente(nombre=f"Cli TZ1 {uid}", telefono="6441234567")
    db_session_transactional.add(cliente)
    db_session_transactional.flush()
    vehiculo = Vehiculo(id_cliente=cliente.id_cliente, marca="Nissan", modelo="Versa", anio=2024)
    db_session_transactional.add(vehiculo)
    db_session_transactional.flush()

    token = create_access_token(data={"sub": str(usuario.id_usuario), "rol": "CAJA"})
    antes = ahora_local_naive()
    r = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={
            "cliente_id": cliente.id_cliente,
            "vehiculo_id": vehiculo.id_vehiculo,
            "motivo": "Smoke TZ-1 fecha ingreso local taller",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    despues = ahora_local_naive()
    assert r.status_code == 201, r.text
    fi = r.json().get("fecha_ingreso")
    assert fi and not fi.endswith("Z")
    from datetime import datetime as dt

    ingreso = dt.fromisoformat(fi)
    assert antes - timedelta(minutes=2) <= ingreso <= despues + timedelta(minutes=2)
