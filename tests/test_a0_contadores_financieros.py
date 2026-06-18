"""
Tests P5.3 Commit C — contadores SQL financieros O1/O2/V1 (U3–U6, paridad P3).

Los _contar_* financieros no están cableados a construir_resumen_operativo.
Validación: contador SQL == bandeja legacy (limit=0).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.pago import Pago
from app.models.venta import Venta
from app.services.operaciones_service import (
    SALDO_EPSILON,
    _contar_ot_listas_entrega,
    _contar_ot_pendientes_cobro,
    _contar_ventas_saldo_pendiente,
    _ids_ordenes_ot_pendientes_cobro,
    _query_ids_ordenes_o1,
    _venta_activa_por_orden,
    bandeja_ot_listas_entrega,
    bandeja_ot_pendientes_cobro,
    bandeja_ventas_saldo_pendiente,
)
from app.utils.jwt import create_access_token
from app.utils.security import hash_password

ROL_FINANCIERO = "CAJA"


def _seed_usuario(session, rol: str = ROL_FINANCIERO):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"Fin {rol}",
        email=f"fin_a0_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("FinSecret!9"),
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
    cliente = Cliente(nombre=f"Cliente Fin {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Mazda",
        modelo="3",
        anio=2021,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _seed_turno(session, id_usuario: int):
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


def _seed_ot_completada(session, cliente, vehiculo) -> OrdenTrabajo:
    ot = OrdenTrabajo(
        numero_orden=f"OT-FIN-{uuid.uuid4().hex[:8]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.COMPLETADA,
        fecha_ingreso=datetime.utcnow(),
        fecha_finalizacion=datetime.utcnow(),
        total=Decimal("1000.00"),
        subtotal_servicios=Decimal("1000.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    session.add(ot)
    session.flush()
    return ot


def _assert_paridad(contador: int, bandeja_total: int, etiqueta: str) -> None:
    assert contador == bandeja_total, f"{etiqueta}: SQL={contador} legacy={bandeja_total}"


def _paridad_financiera_completa(db, usuario) -> None:
    rol = ROL_FINANCIERO
    _assert_paridad(
        _contar_ot_pendientes_cobro(db),
        bandeja_ot_pendientes_cobro(db, rol, usuario, 0)[0],
        "O1",
    )
    _assert_paridad(
        _contar_ot_listas_entrega(db),
        bandeja_ot_listas_entrega(db, rol, usuario, 0)[0],
        "O2",
    )
    _assert_paridad(
        _contar_ventas_saldo_pendiente(db),
        bandeja_ventas_saldo_pendiente(db, rol, usuario, 0)[0],
        "V1",
    )


@pytest.mark.integration
def test_p3_paridad_financiera_bandejas_vacio(db_session_transactional):
    """P3 — paridad O1/O2/V1 con BD mínima."""
    usuario, _ = _seed_usuario(db_session_transactional)
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_u3_o1_ot_completada_sin_venta(db_session_transactional):
    """U3 — OT COMPLETADA sin venta activa cuenta en O1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)

    assert _contar_ot_pendientes_cobro(db_session_transactional) >= 1
    assert _contar_ot_listas_entrega(db_session_transactional) == bandeja_ot_listas_entrega(
        db_session_transactional, ROL_FINANCIERO, usuario, 0
    )[0]
    ids_sql = frozenset(r[0] for r in _query_ids_ordenes_o1(db_session_transactional).all())
    assert ot.id in ids_sql
    assert ot.id in _ids_ordenes_ot_pendientes_cobro(db_session_transactional)
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_u3_o1_ot_con_venta_saldo_pendiente(db_session_transactional):
    """U3 — OT COMPLETADA con venta activa y saldo > ε cuenta en O1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("800.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("200.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    assert _venta_activa_por_orden(db_session_transactional, ot.id).id_venta == venta.id_venta
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_u4_o2_ot_con_venta_pagada(db_session_transactional):
    """U4 — OT COMPLETADA con venta saldada cuenta en O2, no en O1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("500.00"),
        estado="PAGADA",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("500.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    o1 = bandeja_ot_pendientes_cobro(db_session_transactional, ROL_FINANCIERO, usuario, 0)[0]
    o2 = bandeja_ot_listas_entrega(db_session_transactional, ROL_FINANCIERO, usuario, 0)[0]
    assert o2 >= 1
    assert ot.id not in _ids_ordenes_ot_pendientes_cobro(db_session_transactional)
    _assert_paridad(_contar_ot_listas_entrega(db_session_transactional), o2, "O2 pagada")
    _assert_paridad(_contar_ot_pendientes_cobro(db_session_transactional), o1, "O1 pagada")


@pytest.mark.integration
def test_u5_v1_venta_mostrador_sin_ot(db_session_transactional):
    """U5 — venta mostrador con saldo pendiente cuenta en V1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        total=Decimal("350.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("50.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    assert _contar_ventas_saldo_pendiente(db_session_transactional) >= 1
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_u5_v1_no_duplica_venta_ot_en_o1(db_session_transactional):
    """U5 / P3 — venta OT en O1 no aparece en V1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("900.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("100.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    v1_items = bandeja_ventas_saldo_pendiente(db_session_transactional, ROL_FINANCIERO, usuario, 30)[1]
    ids_v1 = [i["id"] for i in v1_items]
    assert venta.id_venta not in ids_v1
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_u6_venta_cancelada_no_cuenta_v1(db_session_transactional):
    """U6 — venta CANCELADA no cuenta en V1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        total=Decimal("400.00"),
        estado="CANCELADA",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()

    v1_antes = _contar_ventas_saldo_pendiente(db_session_transactional)
    v1_legacy = bandeja_ventas_saldo_pendiente(db_session_transactional, ROL_FINANCIERO, usuario, 0)[0]
    _assert_paridad(v1_antes, v1_legacy, "V1 cancelada")


@pytest.mark.integration
def test_u6_borde_saldo_epsilon_o2_no_o1(db_session_transactional):
    """U6 — saldo == SALDO_EPSILON → O2, no O1."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    total = Decimal("1000.00")
    # Dejar saldo exactamente en SALDO_EPSILON (0.001)
    monto_pagado = total - Decimal(str(SALDO_EPSILON))
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=total,
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=monto_pagado,
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    assert ot.id not in _ids_ordenes_ot_pendientes_cobro(db_session_transactional)
    ids_sql = frozenset(r[0] for r in _query_ids_ordenes_o1(db_session_transactional).all())
    assert ot.id not in ids_sql
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_u6_venta_activa_usa_ultima_no_cancelada(db_session_transactional):
    """U6 — max(id_venta) no cancelada define venta activa para O1/O2."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = _seed_ot_completada(db_session_transactional, cliente, vehiculo)

    venta_vieja = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("600.00"),
        estado="PAGADA",
    )
    db_session_transactional.add(venta_vieja)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta_vieja.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("600.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )

    venta_nueva = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("400.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta_nueva)
    db_session_transactional.flush()

    activa = _venta_activa_por_orden(db_session_transactional, ot.id)
    assert activa.id_venta == venta_nueva.id_venta
    assert ot.id in _ids_ordenes_ot_pendientes_cobro(db_session_transactional)
    _paridad_financiera_completa(db_session_transactional, usuario)


@pytest.mark.integration
def test_ids_o1_sql_vs_legacy_frozenset(db_session_transactional):
    """Paridad conjunto ids O1: query SQL vs _ids_ordenes_ot_pendientes_cobro."""
    usuario, _ = _seed_usuario(db_session_transactional)
    turno = _seed_turno(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    _seed_ot_completada(db_session_transactional, cliente, vehiculo)

    ot_o1 = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot_o1.id,
        total=Decimal("300.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()

    ot_o2 = _seed_ot_completada(db_session_transactional, cliente, vehiculo)
    venta_pagada = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot_o2.id,
        total=Decimal("200.00"),
        estado="PAGADA",
    )
    db_session_transactional.add(venta_pagada)
    db_session_transactional.flush()
    db_session_transactional.add(
        Pago(
            id_venta=venta_pagada.id_venta,
            id_usuario=usuario.id_usuario,
            id_turno=turno.id_turno,
            monto=Decimal("200.00"),
            metodo="EFECTIVO",
            fecha=datetime.utcnow(),
        )
    )
    db_session_transactional.flush()

    legacy_ids = _ids_ordenes_ot_pendientes_cobro(db_session_transactional)
    sql_ids = frozenset(row[0] for row in _query_ids_ordenes_o1(db_session_transactional).all())
    assert legacy_ids == sql_ids
    _paridad_financiera_completa(db_session_transactional, usuario)
