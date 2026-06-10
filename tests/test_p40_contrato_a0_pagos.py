"""
P4.0 T13 — Contrato A0 ↔ POST /api/pagos/.

Verifica coherencia entre evaluador en ítems O1 (ot_pendientes_cobro) y mutación real.
Requiere MySQL; si no hay BD, los tests se omiten (pytest.skip).
"""
import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.venta import Venta
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"Contrato P4 {rol}",
        email=f"p40_a0_pago_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente P40 {uid}", telefono=f"644{uid[:7]}")
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


def _seed_ot_completada_con_venta_saldo(
    session,
    usuario,
    *,
    total: Decimal = Decimal("800.00"),
    monto_pagado: Decimal = Decimal("0.00"),
    id_turno=None,
):
    """OT COMPLETADA en O1 con venta activa y saldo pendiente."""
    cliente, vehiculo = _seed_cliente_vehiculo(session)
    ot = OrdenTrabajo(
        numero_orden=f"OT-P40-{uuid.uuid4().hex[:8]}",
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
    if monto_pagado > 0 and id_turno is not None:
        session.add(
            Pago(
                id_venta=venta.id_venta,
                id_usuario=usuario.id_usuario,
                id_turno=id_turno,
                monto=monto_pagado,
                metodo="EFECTIVO",
                fecha=datetime.utcnow(),
            )
        )
        session.flush()
    saldo = float(total) - float(monto_pagado)
    return ot, venta, saldo


def _registrar_pago_en_item_o1(data: dict, ot_id: int) -> dict:
    item = next(
        (i for i in data["bandejas"]["ot_pendientes_cobro"]["items"] if i["id"] == ot_id),
        None,
    )
    assert item is not None, "OT esperada en ot_pendientes_cobro"
    return next(a for a in item["acciones"] if a["accion"] == "registrar_pago")


@pytest.mark.integration
def test_p40_contrato_a0_pago_positivo_con_turno(client_transactional_db, db_session_transactional):
    """
    Escenario positivo: turno abierto → A0 permitida=true → POST /api/pagos/ 201.
    """
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    turno = _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    ot, venta, saldo = _seed_ot_completada_con_venta_saldo(
        db_session_transactional,
        usuario,
        total=Decimal("800.00"),
        monto_pagado=Decimal("300.00"),
        id_turno=turno.id_turno,
    )
    assert saldo == pytest.approx(500.0, abs=0.01)

    r_a0 = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    assert r_a0.status_code == 200
    pago_a0 = _registrar_pago_en_item_o1(r_a0.json(), ot.id)
    assert pago_a0["permitida"] is True
    assert pago_a0.get("contexto", {}).get("id_venta") == venta.id_venta

    monto_pago = 200.0
    r_post = client_transactional_db.post(
        "/api/pagos/",
        json={
            "id_venta": venta.id_venta,
            "metodo": "EFECTIVO",
            "monto": monto_pago,
        },
        headers=_headers(token),
    )
    assert r_post.status_code == 201, r_post.text
    detail = (r_post.json() if r_post.headers.get("content-type", "").startswith("application/json") else {}) or {}
    if isinstance(detail, dict):
        assert "turno" not in str(detail).lower()


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["CAJA", "ADMIN"])
def test_p40_contrato_a0_pago_negativo_sin_turno(
    client_transactional_db,
    db_session_transactional,
    rol,
):
    """
    Escenario negativo: sin turno → A0 TURNO_CERRADO → POST /api/pagos/ 400.
    """
    usuario, token = _seed_usuario(db_session_transactional, rol)
    ot, venta, _ = _seed_ot_completada_con_venta_saldo(db_session_transactional, usuario)

    r_a0 = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    assert r_a0.status_code == 200
    pago_a0 = _registrar_pago_en_item_o1(r_a0.json(), ot.id)
    assert pago_a0["permitida"] is False
    assert pago_a0["codigo_bloqueo"] == "TURNO_CERRADO"

    r_post = client_transactional_db.post(
        "/api/pagos/",
        json={
            "id_venta": venta.id_venta,
            "metodo": "EFECTIVO",
            "monto": 100.0,
        },
        headers=_headers(token),
    )
    assert r_post.status_code == 400
    assert "turno" in r_post.json().get("detail", "").lower()


@pytest.mark.integration
def test_p40_invariante_no_a0_verde_si_post_falla_por_turno(
    client_transactional_db,
    db_session_transactional,
):
    """
    Invariante P4.0: no existe escenario donde A0 permitida=true y POST rechaza por turno cerrado.
    Verificado en bandeja O1: sin turno A0=false antes de intentar POST.
    """
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    ot, venta, _ = _seed_ot_completada_con_venta_saldo(db_session_transactional, usuario)

    r_a0 = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    pago_a0 = _registrar_pago_en_item_o1(r_a0.json(), ot.id)

    r_post = client_transactional_db.post(
        "/api/pagos/",
        json={"id_venta": venta.id_venta, "metodo": "EFECTIVO", "monto": 50.0},
        headers=_headers(token),
    )
    assert r_post.status_code == 400
    assert "turno" in r_post.json().get("detail", "").lower()
    assert pago_a0["permitida"] is False, (
        "Violación contrato P4.0: A0 mostró registrar_pago permitida=true "
        "pero POST falló por turno cerrado"
    )
