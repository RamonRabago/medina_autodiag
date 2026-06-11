"""
P4.1 Fase 4A — Golden path API: registrar pago desde Caja Operativa (A0 → POST → refetch).

Requiere MySQL; si no hay BD, los tests se omiten (pytest.skip).
"""
import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.venta import Venta
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"P41 4A {rol}",
        email=f"p41_4a_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente P41 4A {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Nissan",
        modelo="March",
        anio=2021,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _seed_turno_caja(session, id_usuario: int):
    from app.models.caja_turno import CajaTurno

    turno = CajaTurno(
        id_usuario=id_usuario,
        monto_apertura=Decimal("500.00"),
        estado="ABIERTO",
        fecha_apertura=datetime.utcnow(),
    )
    session.add(turno)
    session.flush()
    return turno


def _seed_ot_completada_con_venta(session, *, total: Decimal = Decimal("1000.00")):
    cliente, vehiculo = _seed_cliente_vehiculo(session)
    ot = OrdenTrabajo(
        numero_orden=f"OT-P41A-{uuid.uuid4().hex[:8]}",
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
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=total,
        estado="PENDIENTE",
    )
    session.add(venta)
    session.flush()
    return ot, venta


def _item_o1(data: dict, ot_id: int) -> dict | None:
    return next(
        (i for i in data["bandejas"]["ot_pendientes_cobro"]["items"] if i["id"] == ot_id),
        None,
    )


def _item_o2(data: dict, ot_id: int) -> dict | None:
    return next(
        (i for i in data["bandejas"]["ot_listas_entrega"]["items"] if i["id"] == ot_id),
        None,
    )


def _accion_pago(item: dict) -> dict:
    return next(a for a in item["acciones"] if a["accion"] == "registrar_pago")


@pytest.mark.integration
def test_p41_fase4a_pago_parcial_reduce_saldo_o1(
    client_transactional_db,
    db_session_transactional,
):
    """O1 con venta activa → pago parcial → A0 refetch con saldo reducido."""
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    ot, venta = _seed_ot_completada_con_venta(db_session_transactional, total=Decimal("1000.00"))
    h = _headers(token)

    r0 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    assert r0.status_code == 200
    item0 = _item_o1(r0.json(), ot.id)
    assert item0 is not None
    pago0 = _accion_pago(item0)
    assert pago0["permitida"] is True
    assert pago0["contexto"]["id_venta"] == venta.id_venta
    assert item0["saldo_pendiente"] == pytest.approx(1000.0)

    r_post = client_transactional_db.post(
        "/api/pagos/",
        json={"id_venta": venta.id_venta, "metodo": "EFECTIVO", "monto": 400.0},
        headers=h,
    )
    assert r_post.status_code == 201, r_post.text
    assert r_post.json()["estado_venta"].lower() == "pendiente"

    r1 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    item1 = _item_o1(r1.json(), ot.id)
    assert item1 is not None
    assert item1["saldo_pendiente"] == pytest.approx(600.0)
    pago1 = _accion_pago(item1)
    assert pago1["permitida"] is True
    assert pago1["contexto"]["saldo_pendiente"] == pytest.approx(600.0)


@pytest.mark.integration
def test_p41_fase4a_pago_total_liquida_sale_o1(
    client_transactional_db,
    db_session_transactional,
):
    """Pago total → OT sale de O1 y pasa a O2 con saldo 0; registrar_pago no permitido en O2."""
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    ot, venta = _seed_ot_completada_con_venta(db_session_transactional, total=Decimal("750.00"))
    h = _headers(token)

    r0 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    assert _item_o1(r0.json(), ot.id) is not None

    r_post = client_transactional_db.post(
        "/api/pagos/",
        json={"id_venta": venta.id_venta, "metodo": "TARJETA", "monto": 750.0},
        headers=h,
    )
    assert r_post.status_code == 201
    assert r_post.json()["estado_venta"].lower() == "pagada"

    r1 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    data1 = r1.json()
    assert _item_o1(data1, ot.id) is None
    item_o2 = _item_o2(data1, ot.id)
    assert item_o2 is not None
    assert item_o2["saldo_pendiente"] == pytest.approx(0.0)
    acciones_o2 = {a["accion"]: a for a in item_o2["acciones"]}
    assert "registrar_pago" not in acciones_o2
    assert acciones_o2.get("entregar_vehiculo", {}).get("permitida") is True


@pytest.mark.integration
def test_p41_fase4a_sin_turno_pago_bloqueado_turno_cerrado(
    client_transactional_db,
    db_session_transactional,
):
    """CAJA sin turno → registrar_pago bloqueado con TURNO_CERRADO."""
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    ot, venta = _seed_ot_completada_con_venta(db_session_transactional, total=Decimal("500.00"))
    h = _headers(token)

    r0 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    item0 = _item_o1(r0.json(), ot.id)
    assert item0 is not None
    pago0 = _accion_pago(item0)
    assert pago0["permitida"] is False
    assert pago0["codigo_bloqueo"] == "TURNO_CERRADO"

    r_post = client_transactional_db.post(
        "/api/pagos/",
        json={"id_venta": venta.id_venta, "metodo": "EFECTIVO", "monto": 100.0},
        headers=h,
    )
    assert r_post.status_code == 400
    assert "turno" in r_post.json().get("detail", "").lower()
