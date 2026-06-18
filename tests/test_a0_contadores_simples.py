"""
Tests P5.3 Commit B — contadores SQL simples vs bandejas legacy (U1–U2).

Los helpers _contar_* no están cableados a construir_resumen_operativo aún;
solo se valida paridad de totales con bandeja_*(limit=0).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.cita import Cita, EstadoCita, TipoCita
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.services.operaciones_service import (
    _contar_citas_convertibles,
    _contar_citas_pendientes_asistencia,
    _contar_ot_completadas,
    _contar_ot_en_proceso,
    _contar_ot_pendientes,
    bandeja_citas_convertibles,
    bandeja_citas_pendientes_asistencia,
    bandeja_ot_completadas,
    bandeja_ot_en_proceso,
    bandeja_ot_pendientes,
)
from app.utils.fechas import ahora_local
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"Contador {rol}",
        email=f"contador_a0_{rol.lower()}_{uid}@test.medina",
        password_hash=hash_password("ContadorSecret!9"),
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
    cliente = Cliente(nombre=f"Cliente Contador {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Honda",
        modelo="Civic",
        anio=2018,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _assert_contador_igual_bandeja(contador: int, bandeja_total: int, etiqueta: str) -> None:
    assert contador == bandeja_total, (
        f"{etiqueta}: contador SQL={contador} bandeja legacy={bandeja_total}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["ADMIN", "CAJA", "EMPLEADO"])
def test_u1_contadores_citas_paridad_bandejas_vacio(
    db_session_transactional,
    rol: str,
):
    """U1 — citas: contadores == bandeja total con BD mínima."""
    usuario, _ = _seed_usuario(db_session_transactional, rol)

    _assert_contador_igual_bandeja(
        _contar_citas_pendientes_asistencia(db_session_transactional),
        bandeja_citas_pendientes_asistencia(db_session_transactional, rol, 0)[0],
        "citas_pendientes_asistencia",
    )
    _assert_contador_igual_bandeja(
        _contar_citas_convertibles(db_session_transactional),
        bandeja_citas_convertibles(db_session_transactional, rol, 0)[0],
        "citas_convertibles",
    )


@pytest.mark.integration
def test_u1_contadores_citas_con_fixtures(db_session_transactional):
    """U1 — citas con asistencia vencida y convertible."""
    usuario, _ = _seed_usuario(db_session_transactional, "ADMIN")
    rol = "ADMIN"
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    ahora = ahora_local()
    cita_vencida = Cita(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        fecha_hora=ahora - timedelta(hours=2),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.CONFIRMADA,
        motivo="Revisión general programada para asistencia",
    )
    cita_convertible = Cita(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        fecha_hora=ahora + timedelta(days=1),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.SI_ASISTIO,
        motivo="Cliente en taller listo para recepción",
    )
    cita_futura = Cita(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        fecha_hora=ahora + timedelta(days=2),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.CONFIRMADA,
        motivo="Cita futura no debe contar en asistencia vencida",
    )
    db_session_transactional.add_all([cita_vencida, cita_convertible, cita_futura])
    db_session_transactional.flush()

    total_asist_bandeja = bandeja_citas_pendientes_asistencia(db_session_transactional, rol, 0)[0]
    total_conv_bandeja = bandeja_citas_convertibles(db_session_transactional, rol, 0)[0]

    assert _contar_citas_pendientes_asistencia(db_session_transactional) >= 1
    assert _contar_citas_convertibles(db_session_transactional) >= 2
    _assert_contador_igual_bandeja(
        _contar_citas_pendientes_asistencia(db_session_transactional),
        total_asist_bandeja,
        "citas_pendientes_asistencia fixture",
    )
    _assert_contador_igual_bandeja(
        _contar_citas_convertibles(db_session_transactional),
        total_conv_bandeja,
        "citas_convertibles fixture",
    )


@pytest.mark.integration
@pytest.mark.parametrize("rol", ["ADMIN", "TECNICO"])
def test_u2_contadores_ot_paridad_bandejas_sin_filtro(
    db_session_transactional,
    rol: str,
):
    """U2 — OT pendientes / en proceso / completadas sin filtro técnico (ADMIN)."""
    usuario, _ = _seed_usuario(db_session_transactional, rol)
    tecnico_filtro = usuario.id_usuario if rol == "TECNICO" else None

    _assert_contador_igual_bandeja(
        _contar_ot_pendientes(db_session_transactional, tecnico_filtro),
        bandeja_ot_pendientes(db_session_transactional, rol, usuario, 0, tecnico_filtro)[0],
        f"ot_pendientes rol={rol}",
    )
    _assert_contador_igual_bandeja(
        _contar_ot_en_proceso(db_session_transactional, tecnico_filtro),
        bandeja_ot_en_proceso(db_session_transactional, rol, usuario, 0, tecnico_filtro)[0],
        f"ot_en_proceso rol={rol}",
    )
    _assert_contador_igual_bandeja(
        _contar_ot_completadas(db_session_transactional, tecnico_filtro),
        bandeja_ot_completadas(db_session_transactional, rol, usuario, 0, tecnico_filtro)[0],
        f"ot_completadas rol={rol}",
    )


@pytest.mark.integration
def test_u2_contadores_ot_filtro_tecnico_paridad_bandejas(db_session_transactional):
    """U2 — filtro tecnico_id: contador == bandeja Mi Taller."""
    tecnico, _ = _seed_usuario(db_session_transactional, "TECNICO")
    admin_user, _ = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    ot_propia_pend = OrdenTrabajo(
        numero_orden=f"OT-CB-P-{uuid.uuid4().hex[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=tecnico.id_usuario,
        estado=EstadoOrden.PENDIENTE,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("0.00"),
        subtotal_servicios=Decimal("0.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    ot_ajena_proc = OrdenTrabajo(
        numero_orden=f"OT-CB-A-{uuid.uuid4().hex[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=None,
        estado=EstadoOrden.EN_PROCESO,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("0.00"),
        subtotal_servicios=Decimal("0.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    ot_propia_compl = OrdenTrabajo(
        numero_orden=f"OT-CB-C-{uuid.uuid4().hex[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=tecnico.id_usuario,
        estado=EstadoOrden.COMPLETADA,
        fecha_ingreso=datetime.utcnow(),
        fecha_finalizacion=datetime.utcnow(),
        total=Decimal("100.00"),
        subtotal_servicios=Decimal("100.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    db_session_transactional.add_all([ot_propia_pend, ot_ajena_proc, ot_propia_compl])
    db_session_transactional.flush()

    rol = "TECNICO"
    tec_id = tecnico.id_usuario

    assert _contar_ot_pendientes(db_session_transactional, tec_id) >= 1
    assert _contar_ot_en_proceso(db_session_transactional, tec_id) == 0
    assert _contar_ot_completadas(db_session_transactional, tec_id) >= 1

    _assert_contador_igual_bandeja(
        _contar_ot_pendientes(db_session_transactional, tec_id),
        bandeja_ot_pendientes(db_session_transactional, rol, tecnico, 0, tec_id)[0],
        "ot_pendientes tecnico",
    )
    _assert_contador_igual_bandeja(
        _contar_ot_en_proceso(db_session_transactional, tec_id),
        bandeja_ot_en_proceso(db_session_transactional, rol, tecnico, 0, tec_id)[0],
        "ot_en_proceso tecnico",
    )
    _assert_contador_igual_bandeja(
        _contar_ot_completadas(db_session_transactional, tec_id),
        bandeja_ot_completadas(db_session_transactional, rol, tecnico, 0, tec_id)[0],
        "ot_completadas tecnico",
    )

    # ADMIN ve todas; contador sin filtro debe coincidir con bandeja ADMIN
    _assert_contador_igual_bandeja(
        _contar_ot_pendientes(db_session_transactional, None),
        bandeja_ot_pendientes(db_session_transactional, "ADMIN", admin_user, 0, None)[0],
        "ot_pendientes admin sin filtro",
    )
