"""Contrato de timezone en API de caja (histórico de turnos)."""

import uuid
from datetime import datetime

import pytest

from app.models.caja_turno import CajaTurno
from app.models.usuario import Usuario
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _token_caja(db, rol="CAJA"):
    uid = uuid.uuid4().hex[:8]
    u = Usuario(
        nombre=f"TZ Caja {uid}",
        email=f"tz_caja_{uid}@test.medina",
        password_hash=hash_password("TzCaja!9"),
        rol=rol,
        activo=True,
    )
    db.add(u)
    db.flush()
    return create_access_token(data={"sub": str(u.id_usuario), "rol": rol}), u


@pytest.mark.integration
def test_historico_turnos_fechas_con_z(client_transactional_db, db_session_transactional):
    """Turnos cerrados deben exponer fecha_cierre con sufijo Z (UTC)."""
    token, usuario = _token_caja(db_session_transactional)
    cierre_utc = datetime(2026, 6, 30, 13, 39, 35)
    turno = CajaTurno(
        id_usuario=usuario.id_usuario,
        monto_apertura=100,
        monto_cierre=150,
        diferencia=0,
        fecha_apertura=datetime(2026, 6, 30, 12, 0, 0),
        fecha_cierre=cierre_utc,
        estado="CERRADO",
    )
    db_session_transactional.add(turno)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/caja/historico-turnos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data) >= 1
    row = next(x for x in data if x["id_turno"] == turno.id_turno)
    assert row["fecha_cierre"].endswith("Z")
    assert row["fecha_apertura"].endswith("Z")
    assert "T13:39:35" in row["fecha_cierre"]


@pytest.mark.integration
def test_historico_turnos_filtro_dia_matamoros(client_transactional_db, db_session_transactional):
    """Turno cerrado 08:39 Matamoros (13:39 UTC) debe aparecer al filtrar 2026-06-30."""
    token, usuario = _token_caja(db_session_transactional)
    turno = CajaTurno(
        id_usuario=usuario.id_usuario,
        monto_apertura=50,
        monto_cierre=50,
        diferencia=0,
        fecha_apertura=datetime(2026, 6, 30, 12, 0, 0),
        fecha_cierre=datetime(2026, 6, 30, 13, 39, 0),
        estado="CERRADO",
    )
    db_session_transactional.add(turno)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/caja/historico-turnos",
        params={"fecha_desde": "2026-06-30", "fecha_hasta": "2026-06-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    ids = [x["id_turno"] for x in r.json()]
    assert turno.id_turno in ids

    r2 = client_transactional_db.get(
        "/api/caja/historico-turnos",
        params={"fecha_desde": "2026-06-29", "fecha_hasta": "2026-06-29"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert turno.id_turno not in [x["id_turno"] for x in r2.json()]
