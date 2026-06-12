"""
P4.2 — Golden path API encadenado: crear venta → pago total → entregar.

Valida la secuencia que orquesta el wizard frontend sin UI.
Backend sin cambios; mismos endpoints P4.1.

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
        nombre=f"P42 {rol}",
        email=f"p42_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente P42 {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Toyota",
        modelo="Yaris",
        anio=2022,
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


def _seed_ot_completada_sin_venta(session, *, total: Decimal = Decimal("850.00")):
    cliente, vehiculo = _seed_cliente_vehiculo(session)
    ot = OrdenTrabajo(
        numero_orden=f"OT-P42-{uuid.uuid4().hex[:8]}",
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
    return ot


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


def _accion(item: dict, nombre: str) -> dict | None:
    return next((a for a in item["acciones"] if a["accion"] == nombre), None)


@pytest.mark.integration
def test_p42_golden_path_crear_venta_pago_total_entregar(
    client_transactional_db,
    db_session_transactional,
):
    """Secuencia completa del wizard: O1 → venta → pago → O2 → entregar."""
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    ot = _seed_ot_completada_sin_venta(db_session_transactional, total=Decimal("920.00"))
    h = _headers(token)
    client = client_transactional_db

    r0 = client.get("/api/operaciones/resumen", headers=h)
    assert r0.status_code == 200
    item0 = _item_o1(r0.json(), ot.id)
    assert item0 is not None
    assert _accion(item0, "crear_venta_desde_ot")["permitida"] is True

    r_venta = client.post(
        f"/api/ventas/desde-orden/{ot.id}",
        params={"requiere_factura": False},
        headers=h,
    )
    assert r_venta.status_code == 201, r_venta.text
    id_venta = r_venta.json()["id_venta"]

    r1 = client.get("/api/operaciones/resumen", headers=h)
    item1 = _item_o1(r1.json(), ot.id)
    assert item1 is not None
    pago1 = _accion(item1, "registrar_pago")
    assert pago1["permitida"] is True
    assert pago1["contexto"]["id_venta"] == id_venta

    r_pago = client.post(
        "/api/pagos/",
        json={"id_venta": id_venta, "metodo": "EFECTIVO", "monto": 920.0},
        headers=h,
    )
    assert r_pago.status_code == 201
    assert r_pago.json()["estado_venta"].lower() == "pagada"

    r2 = client.get("/api/operaciones/resumen", headers=h)
    assert _item_o1(r2.json(), ot.id) is None
    item_o2 = _item_o2(r2.json(), ot.id)
    assert item_o2 is not None
    entrega = _accion(item_o2, "entregar_vehiculo")
    assert entrega["permitida"] is True

    r_ent = client.post(
        f"/api/ordenes-trabajo/{ot.id}/entregar",
        json={"observaciones_entrega": "Entrega P42 golden path"},
        headers=h,
    )
    assert r_ent.status_code == 200, r_ent.text
    assert r_ent.json()["estado"] == "ENTREGADA"

    r3 = client.get("/api/operaciones/resumen", headers=h)
    assert _item_o2(r3.json(), ot.id) is None
    assert _item_o1(r3.json(), ot.id) is None


@pytest.mark.integration
def test_p42_pago_parcial_detiene_flujo_con_saldo(
    client_transactional_db,
    db_session_transactional,
):
    """Pago parcial: OT permanece en O1 con saldo; entrega no permitida."""
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    ot = _seed_ot_completada_sin_venta(db_session_transactional, total=Decimal("1000.00"))
    h = _headers(token)
    client = client_transactional_db

    r_venta = client.post(
        f"/api/ventas/desde-orden/{ot.id}",
        params={"requiere_factura": True},
        headers=h,
    )
    assert r_venta.status_code == 201
    id_venta = r_venta.json()["id_venta"]

    r_pago = client.post(
        "/api/pagos/",
        json={"id_venta": id_venta, "metodo": "TARJETA", "monto": 300.0},
        headers=h,
    )
    assert r_pago.status_code == 201
    assert r_pago.json()["estado_venta"].lower() == "pendiente"

    r1 = client.get("/api/operaciones/resumen", headers=h)
    item1 = _item_o1(r1.json(), ot.id)
    assert item1 is not None
    assert item1["saldo_pendiente"] == pytest.approx(700.0)
    assert _accion(item1, "registrar_pago")["permitida"] is True
    assert _item_o2(r1.json(), ot.id) is None


@pytest.mark.integration
def test_p42_sin_turno_bloquea_pago_tras_crear_venta(
    client_transactional_db,
    db_session_transactional,
):
    """Sin turno: A0 bloquea registrar_pago (TURNO_CERRADO) tras venta creada."""
    _, token = _seed_usuario(db_session_transactional, "CAJA")
    ot = _seed_ot_completada_sin_venta(db_session_transactional, total=Decimal("500.00"))
    h = _headers(token)
    client = client_transactional_db

    r_venta = client.post(
        f"/api/ventas/desde-orden/{ot.id}",
        params={"requiere_factura": False},
        headers=h,
    )
    assert r_venta.status_code == 201

    r1 = client.get("/api/operaciones/resumen", headers=h)
    item1 = _item_o1(r1.json(), ot.id)
    pago = _accion(item1, "registrar_pago")
    assert pago["permitida"] is False
    assert pago["codigo_bloqueo"] == "TURNO_CERRADO"


@pytest.mark.integration
def test_p42_o2_solo_entrega_permitida(
    client_transactional_db,
    db_session_transactional,
):
    """OT liquidada en O2: solo entregar_vehiculo permitida (entrada wizard paso 3)."""
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = OrdenTrabajo(
        numero_orden=f"OT-P42-O2-{uuid.uuid4().hex[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.COMPLETADA,
        fecha_ingreso=datetime.utcnow(),
        fecha_finalizacion=datetime.utcnow(),
        total=Decimal("600.00"),
        subtotal_servicios=Decimal("600.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    db_session_transactional.add(ot)
    db_session_transactional.flush()
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("600.00"),
        estado="PAGADA",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()

    h = _headers(token)
    r0 = client_transactional_db.get("/api/operaciones/resumen", headers=h)
    item_o2 = _item_o2(r0.json(), ot.id)
    assert item_o2 is not None
    assert _accion(item_o2, "entregar_vehiculo")["permitida"] is True
    crear = _accion(item_o2, "crear_venta_desde_ot")
    if crear:
        assert crear["permitida"] is False
