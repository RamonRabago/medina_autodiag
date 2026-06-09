"""
Permisos de alta rápida operativa en POST /api/clientes/.

Requieren MySQL accesible (pytest.skip si no hay BD).
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
        email=f"e2e_cli_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("E2ESecret!9"),
        rol=rol,
        activo=True,
    )
    session.add(usuario)
    session.flush()
    token = create_access_token(data={"sub": str(usuario.id_usuario), "rol": rol})
    return usuario, token


def _payload_cliente(suffix: str | None = None):
    uid = suffix or uuid.uuid4().hex[:8]
    return {
        "nombre": f"Cliente Alta Rapida {uid}",
        "telefono": f"644{uid[:7]}",
    }


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["ADMIN", "CAJA", "EMPLEADO"])
def test_post_clientes_permitido_roles_operativos(client_transactional_db, db_session_transactional, rol):
    _, token = _seed_usuario(db_session_transactional, rol)
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(
        "/api/clientes/",
        json=_payload_cliente(),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["nombre"].startswith("Cliente Alta Rapida")
    assert data["telefono"]


@pytest.mark.integration
def test_post_clientes_rechaza_tecnico(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "TECNICO")
    headers = {"Authorization": f"Bearer {token}"}

    r = client_transactional_db.post(
        "/api/clientes/",
        json=_payload_cliente(),
        headers=headers,
    )
    assert r.status_code == 403, r.text


@pytest.mark.integration
def test_get_cliente_detalle_caja(client_transactional_db, db_session_transactional):
    from app.models.cliente import Cliente

    _, token = _seed_usuario(db_session_transactional, "CAJA")
    uid = uuid.uuid4().hex[:8]
    cliente = Cliente(nombre=f"Cliente Detalle {uid}", telefono=f"644{uid[:7]}")
    db_session_transactional.add(cliente)
    db_session_transactional.flush()

    headers = {"Authorization": f"Bearer {token}"}
    r = client_transactional_db.get(f"/api/clientes/{cliente.id_cliente}", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["id_cliente"] == cliente.id_cliente
