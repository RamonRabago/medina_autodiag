"""
P4.1 Fase 4B — Entregar vehículo desde Caja Operativa (A0 O2 → POST → refetch).

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
        nombre=f"P41 4B {rol}",
        email=f"p41_4b_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente P41 4B {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Honda",
        modelo="Civic",
        anio=2019,
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


def _seed_ot_completada_con_venta(session, *, total: Decimal = Decimal("900.00")):
    cliente, vehiculo = _seed_cliente_vehiculo(session)
    ot = OrdenTrabajo(
        numero_orden=f"OT-P41B-{uuid.uuid4().hex[:8]}",
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


def _liquidar_venta_ot(client, token, venta, total: float):
    r = client.post(
        "/api/pagos/",
        json={"id_venta": venta.id_venta, "metodo": "EFECTIVO", "monto": total},
        headers=_headers(token),
    )
    assert r.status_code == 201, r.text


@pytest.mark.integration
def test_p41_fase4b_entregar_happy_path_sale_o2(
    client_transactional_db,
    db_session_transactional,
):
    """OT liquidada en O2 → entregar_vehiculo permitida → POST → OT fuera de bandejas."""
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    ot, venta = _seed_ot_completada_con_venta(db_session_transactional, total=Decimal("900.00"))
    h = _headers(token)
    client = client_transactional_db

    _liquidar_venta_ot(client, token, venta, 900.0)

    r0 = client.get("/api/operaciones/resumen", headers=h)
    assert r0.status_code == 200
    item_o2 = _item_o2(r0.json(), ot.id)
    assert item_o2 is not None
    entregar = next(a for a in item_o2["acciones"] if a["accion"] == "entregar_vehiculo")
    assert entregar["permitida"] is True
    assert _item_o1(r0.json(), ot.id) is None

    r_post = client.post(
        f"/api/ordenes-trabajo/{ot.id}/entregar",
        json={"observaciones_entrega": "Entrega E2E P41 4B"},
        headers=h,
    )
    assert r_post.status_code == 200, r_post.text
    assert r_post.json()["estado"] in ("ENTREGADA", EstadoOrden.ENTREGADA.value)

    r1 = client.get("/api/operaciones/resumen", headers=h)
    data1 = r1.json()
    assert _item_o1(data1, ot.id) is None
    assert _item_o2(data1, ot.id) is None


@pytest.mark.integration
def test_p41_fase4b_entregar_bloqueada_con_saldo_pendiente(
    client_transactional_db,
    db_session_transactional,
):
    """OT con saldo en O1: sin entregar en A0; POST rechazado (VENTA_SIN_PAGAR)."""
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    ot, venta = _seed_ot_completada_con_venta(db_session_transactional, total=Decimal("500.00"))
    h = _headers(token)
    client = client_transactional_db

    r0 = client.get("/api/operaciones/resumen", headers=h)
    item_o1 = _item_o1(r0.json(), ot.id)
    assert item_o1 is not None
    assert item_o1["saldo_pendiente"] == pytest.approx(500.0)
    acciones_o1 = {a["accion"] for a in item_o1["acciones"]}
    assert "entregar_vehiculo" not in acciones_o1
    assert _item_o2(r0.json(), ot.id) is None

    r_post = client.post(
        f"/api/ordenes-trabajo/{ot.id}/entregar",
        json={},
        headers=h,
    )
    assert r_post.status_code == 400
    assert "pagad" in r_post.json().get("detail", "").lower()


@pytest.mark.integration
def test_p41_fase4b_tecnico_no_puede_entregar(
    client_transactional_db,
    db_session_transactional,
):
    """TECNICO: POST entregar rechazado por rol (sin mutación)."""
    usuario_caja, token_caja = _seed_usuario(db_session_transactional, "CAJA")
    _, token_tec = _seed_usuario(db_session_transactional, "TECNICO")
    _seed_turno_caja(db_session_transactional, usuario_caja.id_usuario)
    ot, venta = _seed_ot_completada_con_venta(db_session_transactional, total=Decimal("400.00"))
    _liquidar_venta_ot(client_transactional_db, token_caja, venta, 400.0)

    r = client_transactional_db.post(
        f"/api/ordenes-trabajo/{ot.id}/entregar",
        json={},
        headers=_headers(token_tec),
    )
    assert r.status_code == 403
