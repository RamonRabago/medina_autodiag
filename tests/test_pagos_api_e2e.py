"""
Pruebas E2E de POST /api/pagos (JWT + sesión BD transaccional con rollback).

Requieren MySQL accesible con la misma configuración que el proyecto (.env).
Si no hay BD, los tests se omiten (pytest.skip).
"""
import uuid

import pytest
from decimal import Decimal


def _seed_caja_y_venta(session, total_venta: Decimal, rol: str = "CAJA"):
    """Crea usuario CAJA/ADMIN, turno abierto y venta PENDIENTE. Devuelve ids y token JWT."""
    from app.models.usuario import Usuario
    from app.models.caja_turno import CajaTurno
    from app.models.venta import Venta
    from app.utils.security import hash_password
    from app.utils.jwt import create_access_token

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre="E2E Pagos",
        email=f"e2e_pagos_{uid}@test.medina",
        password_hash=hash_password("E2ESecret!9"),
        rol=rol,
        activo=True,
    )
    session.add(usuario)
    session.flush()

    turno = CajaTurno(
        id_usuario=usuario.id_usuario,
        monto_apertura=Decimal("500.00"),
        estado="ABIERTO",
    )
    session.add(turno)
    session.flush()

    venta = Venta(
        id_cliente=None,
        id_usuario=usuario.id_usuario,
        total=total_venta,
        estado="PENDIENTE",
        requiere_factura=False,
    )
    session.add(venta)
    session.flush()

    token = create_access_token(
        data={"sub": str(usuario.id_usuario), "rol": rol},
    )
    return {
        "token": token,
        "id_usuario": usuario.id_usuario,
        "id_turno": turno.id_turno,
        "id_venta": venta.id_venta,
        "venta": venta,
    }


@pytest.mark.integration
def test_post_pago_liquida_venta(client_transactional_db, db_session_transactional):
    ctx = _seed_caja_y_venta(db_session_transactional, Decimal("100.00"))
    client = client_transactional_db
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    r = client.post(
        "/api/pagos/",
        json={
            "id_venta": ctx["id_venta"],
            "metodo": "EFECTIVO",
            "monto": 100.0,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado_venta"] == "PAGADA"
    assert abs(data["total_pagado"] - 100.0) < 0.01

    db_session_transactional.refresh(ctx["venta"])
    est = ctx["venta"].estado
    assert (est.value if hasattr(est, "value") else str(est)) == "PAGADA"


@pytest.mark.integration
def test_post_pago_rechaza_si_excede_total(client_transactional_db, db_session_transactional):
    ctx = _seed_caja_y_venta(db_session_transactional, Decimal("100.00"))
    client = client_transactional_db
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    r = client.post(
        "/api/pagos/",
        json={
            "id_venta": ctx["id_venta"],
            "metodo": "EFECTIVO",
            "monto": 100.01,
        },
        headers=headers,
    )
    assert r.status_code == 400
    assert "excede" in r.json().get("detail", "").lower()


@pytest.mark.integration
def test_post_pago_parcial_luego_liquida(client_transactional_db, db_session_transactional):
    ctx = _seed_caja_y_venta(db_session_transactional, Decimal("100.00"))
    client = client_transactional_db
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    r1 = client.post(
        "/api/pagos/",
        json={"id_venta": ctx["id_venta"], "metodo": "EFECTIVO", "monto": 60.0},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["estado_venta"] == "PENDIENTE"

    r2 = client.post(
        "/api/pagos/",
        json={"id_venta": ctx["id_venta"], "metodo": "TARJETA", "monto": 40.0},
        headers=headers,
    )
    assert r2.status_code == 201, r2.text
    assert r2.json()["estado_venta"] == "PAGADA"


@pytest.mark.integration
def test_post_pago_sin_turno_abierto_400(client_transactional_db, db_session_transactional):
    """Sin turno ABIERTO el endpoint debe rechazar."""
    from app.models.usuario import Usuario
    from app.models.venta import Venta
    from app.utils.security import hash_password
    from app.utils.jwt import create_access_token

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre="E2E Sin turno",
        email=f"e2e_sin_turno_{uid}@test.medina",
        password_hash=hash_password("E2ESecret!9"),
        rol="CAJA",
        activo=True,
    )
    db_session_transactional.add(usuario)
    db_session_transactional.flush()

    venta = Venta(
        id_usuario=usuario.id_usuario,
        total=Decimal("50.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()

    token = create_access_token(data={"sub": str(usuario.id_usuario), "rol": "CAJA"})
    client = client_transactional_db
    r = client.post(
        "/api/pagos/",
        json={"id_venta": venta.id_venta, "metodo": "EFECTIVO", "monto": 50.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "turno" in r.json().get("detail", "").lower()
