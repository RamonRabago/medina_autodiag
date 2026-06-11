"""
P4.1 Fase 3 — Golden path API: crear venta desde OT (A0 → POST → refetch A0).

Valida el flujo delegado de Caja Operativa sin UI:
OT COMPLETADA sin venta → crear_venta permitida → POST desde-orden →
id_venta/saldo en O1 → crear_venta bloqueada (VENTA_EXISTENTE).

Requiere MySQL; si no hay BD, los tests se omiten (pytest.skip).
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"P41 F3 {rol}",
        email=f"p41_f3_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("OpsSecret!9"),
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
    cliente = Cliente(nombre=f"Cliente P41 {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Toyota",
        modelo="Corolla",
        anio=2020,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _seed_ot_completada_sin_venta(session, *, total: Decimal = Decimal("600.00")):
    cliente, vehiculo = _seed_cliente_vehiculo(session)
    ot = OrdenTrabajo(
        numero_orden=f"OT-P41F3-{uuid.uuid4().hex[:8]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.COMPLETADA,
        fecha_ingreso=datetime.utcnow(),
        fecha_finalizacion=datetime.utcnow(),
        total=total,
        subtotal_servicios=total,
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    session.add(ot)
    session.flush()
    return ot, cliente, vehiculo


def _item_o1(data: dict, ot_id: int) -> dict:
    item = next(
        (i for i in data["bandejas"]["ot_pendientes_cobro"]["items"] if i["id"] == ot_id),
        None,
    )
    assert item is not None, "OT esperada en ot_pendientes_cobro (O1)"
    return item


def _accion(item: dict, nombre: str) -> dict:
    return next(a for a in item["acciones"] if a["accion"] == nombre)


@pytest.mark.integration
def test_p41_fase3_golden_crear_venta_desde_ot_a0_refetch(
    client_transactional_db,
    db_session_transactional,
):
    """Golden path Fase 3: O1 sin venta → POST crear venta → A0 con VENTA_EXISTENTE."""
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    ot, _, _ = _seed_ot_completada_sin_venta(db_session_transactional, total=Decimal("600.00"))
    h = _headers(token)

    r0 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    assert r0.status_code == 200
    assert r0.json()["meta"]["version_contrato"] == "a0-v2"
    item0 = _item_o1(r0.json(), ot.id)
    assert item0.get("id_venta") is None
    assert item0.get("saldo_pendiente") is None
    crear0 = _accion(item0, "crear_venta_desde_ot")
    assert crear0["permitida"] is True
    assert crear0.get("codigo_bloqueo") is None

    r_post = client_transactional_db.post(
        f"/api/ventas/desde-orden/{ot.id}",
        params={"requiere_factura": False},
        headers=h,
    )
    assert r_post.status_code == 201, r_post.text
    venta_creada = r_post.json()
    id_venta = venta_creada["id_venta"]
    assert id_venta is not None

    r1 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    assert r1.status_code == 200
    item1 = _item_o1(r1.json(), ot.id)
    assert item1["id_venta"] == id_venta
    assert item1["saldo_pendiente"] == pytest.approx(600.0)
    crear1 = _accion(item1, "crear_venta_desde_ot")
    assert crear1["permitida"] is False
    assert crear1["codigo_bloqueo"] == "VENTA_EXISTENTE"
    assert crear1["motivo_bloqueo"] == "Ya existe venta vinculada"
