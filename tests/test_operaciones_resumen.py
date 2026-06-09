"""
Pruebas A0 — GET /api/operaciones/resumen y evaluar_cita_convertible.

Requieren MySQL accesible. Si no hay BD, los tests se omiten (pytest.skip).
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.cita import Cita, EstadoCita, TipoCita
from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
from app.models.pago import Pago
from app.models.venta import Venta
from app.services.recepcion_ot_service import evaluar_cita_convertible
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _seed_usuario(session, rol: str):
    from app.models.usuario import Usuario

    uid = uuid.uuid4().hex[:10]
    usuario = Usuario(
        nombre=f"Ops {rol}",
        email=f"ops_a0_{rol.lower()}_{uid}@test.medina",
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
    cliente = Cliente(nombre=f"Cliente Ops {uid}", telefono=f"644{uid[:7]}")
    session.add(cliente)
    session.flush()
    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca="Nissan",
        modelo="Sentra",
        anio=2020,
    )
    session.add(vehiculo)
    session.flush()
    return cliente, vehiculo


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_resumen_responde_sin_datos(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    r = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["meta"]["version_contrato"] == "a0-v1"
    assert data["bloqueo_financiero"]["bloqueo_financiero"] is False
    assert isinstance(data["acciones_globales"], list)
    assert data["metricas"]["ot_pendientes"] >= 0
    assert "citas_pendientes_asistencia" in data["bandejas"]


@pytest.mark.integration
def test_detecta_ot_pendientes(client_transactional_db, db_session_transactional):
    _, token = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = OrdenTrabajo(
        numero_orden=f"OT-TEST-{uuid.uuid4().hex[:8]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.PENDIENTE,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("0.00"),
        subtotal_servicios=Decimal("0.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    db_session_transactional.add(ot)
    db_session_transactional.flush()

    r = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["metricas"]["ot_pendientes"] >= 1
    ids = [i["id"] for i in data["bandejas"]["ot_pendientes"]["items"]]
    assert ot.id in ids
    item = next(i for i in data["bandejas"]["ot_pendientes"]["items"] if i["id"] == ot.id)
    assert item["estado_operativo"] == "PENDIENTE"
    assert item["etiqueta_estado"]
    assert item["prioridad_sugerida"] in ("ALTA", "NORMAL", "BAJA")


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


@pytest.mark.integration
def test_detecta_ventas_saldo_pendiente(client_transactional_db, db_session_transactional):
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    turno = _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        total=Decimal("1000.00"),
        estado="PENDIENTE",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    pago = Pago(
        id_venta=venta.id_venta,
        id_usuario=usuario.id_usuario,
        id_turno=turno.id_turno,
        monto=Decimal("400.00"),
        metodo="EFECTIVO",
        fecha=datetime.utcnow(),
    )
    db_session_transactional.add(pago)
    db_session_transactional.flush()

    r = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["metricas"]["ventas_saldo_pendiente"] >= 1
    item = next(
        (i for i in data["bandejas"]["ventas_saldo_pendiente"]["items"] if i["id"] == venta.id_venta),
        None,
    )
    assert item is not None
    assert item["saldo_pendiente"] == pytest.approx(600.0, abs=0.01)
    assert item["origen_tipo"] == "MOSTRADOR"
    assert item["origen_id"] == venta.id_venta


@pytest.mark.integration
def test_detecta_ot_listas_para_entrega(client_transactional_db, db_session_transactional):
    usuario, token = _seed_usuario(db_session_transactional, "CAJA")
    turno = _seed_turno_caja(db_session_transactional, usuario.id_usuario)
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)
    ot = OrdenTrabajo(
        numero_orden=f"OT-ENT-{uuid.uuid4().hex[:8]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.COMPLETADA,
        fecha_ingreso=datetime.utcnow(),
        fecha_finalizacion=datetime.utcnow(),
        total=Decimal("800.00"),
        subtotal_servicios=Decimal("800.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    db_session_transactional.add(ot)
    db_session_transactional.flush()
    venta = Venta(
        id_cliente=cliente.id_cliente,
        id_vehiculo=vehiculo.id_vehiculo,
        id_orden=ot.id,
        total=Decimal("800.00"),
        estado="PAGADA",
    )
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    pago = Pago(
        id_venta=venta.id_venta,
        id_usuario=usuario.id_usuario,
        id_turno=turno.id_turno,
        monto=Decimal("800.00"),
        metodo="EFECTIVO",
        fecha=datetime.utcnow(),
    )
    db_session_transactional.add(pago)
    db_session_transactional.flush()

    r = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["metricas"]["ot_listas_entrega"] >= 1
    ids = [i["id"] for i in data["bandejas"]["ot_listas_entrega"]["items"]]
    assert ot.id in ids


@pytest.mark.integration
def test_tecnico_solo_ve_ot_asignadas(client_transactional_db, db_session_transactional):
    tecnico, token_tec = _seed_usuario(db_session_transactional, "TECNICO")
    _, token_admin = _seed_usuario(db_session_transactional, "ADMIN")
    cliente, vehiculo = _seed_cliente_vehiculo(db_session_transactional)

    ot_propia = OrdenTrabajo(
        numero_orden=f"OT-T1-{uuid.uuid4().hex[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=tecnico.id_usuario,
        estado=EstadoOrden.EN_PROCESO,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("0.00"),
        subtotal_servicios=Decimal("0.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    ot_ajena = OrdenTrabajo(
        numero_orden=f"OT-T2-{uuid.uuid4().hex[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=None,
        estado=EstadoOrden.PENDIENTE,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("0.00"),
        subtotal_servicios=Decimal("0.00"),
        subtotal_repuestos=Decimal("0.00"),
        descuento=Decimal("0.00"),
    )
    db_session_transactional.add_all([ot_propia, ot_ajena])
    db_session_transactional.flush()

    r_tec = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token_tec))
    assert r_tec.status_code == 200
    data_tec = r_tec.json()
    ids_proc = [i["id"] for i in data_tec["bandejas"]["ot_en_proceso"]["items"]]
    assert ot_propia.id in ids_proc
    assert ot_ajena.id not in ids_proc
    assert data_tec["metricas"]["ventas_saldo_pendiente"] == 0
    assert data_tec["bandejas"]["ventas_saldo_pendiente"]["total"] == 0

    iniciar = next(a for a in data_tec["acciones_globales"] if a["accion"] == "iniciar_ot")
    assert iniciar["permitida"] is True

    r_admin = client_transactional_db.get("/api/operaciones/resumen", headers=_headers(token_admin))
    data_admin = r_admin.json()
    assert data_admin["metricas"]["ot_pendientes"] >= 1


def test_validar_cita_sin_vehiculo_rechaza():
    """Regresión Citas V2: validar exige vehículo (requiere_vehiculo=True)."""
    import pytest
    from fastapi import HTTPException

    from app.services.recepcion_ot_service import validar_cita_convertible

    cita = Cita(
        id_cita=5,
        id_cliente=10,
        id_vehiculo=None,
        fecha_hora=datetime.utcnow() + timedelta(days=1),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.CONFIRMADA,
        motivo="Revisión general programada",
    )
    with pytest.raises(HTTPException) as exc:
        validar_cita_convertible(cita, 5)
    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("accion") == "COMPLETAR_RECEPCION"


def test_evaluar_cita_convertible_sin_bd():
    """Unit test puro — no requiere MySQL."""
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo

    cita_ok = Cita(
        id_cita=1,
        id_cliente=10,
        id_vehiculo=20,
        fecha_hora=datetime.utcnow() + timedelta(days=1),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.CONFIRMADA,
        motivo="Revisión general programada",
    )
    ev_ok = evaluar_cita_convertible(cita_ok)
    assert ev_ok["convertible"] is True
    assert ev_ok["motivo"] is None

    cita_no = Cita(
        id_cita=2,
        id_cliente=10,
        id_vehiculo=20,
        fecha_hora=datetime.utcnow() + timedelta(days=1),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.NO_ASISTIO,
        motivo="Revisión general programada",
    )
    ev_no = evaluar_cita_convertible(cita_no)
    assert ev_no["convertible"] is False
    assert ev_no["motivo"]

    cita_sin_auto = Cita(
        id_cita=3,
        id_cliente=10,
        id_vehiculo=None,
        fecha_hora=datetime.utcnow() + timedelta(days=1),
        tipo=TipoCita.REVISION,
        estado=EstadoCita.CONFIRMADA,
        motivo="Revisión general programada",
    )
    ev_sin = evaluar_cita_convertible(cita_sin_auto)
    assert ev_sin["convertible"] is False
    assert ev_sin.get("codigo") == "COMPLETAR_RECEPCION"


def test_acciones_globales_por_rol():
    from app.services.operaciones_service import acciones_globales_por_rol

    caja = {a["accion"]: a for a in acciones_globales_por_rol("CAJA")}
    assert caja["registrar_pago"]["permitida"] is True
    assert caja["iniciar_ot"]["permitida"] is False

    tec = {a["accion"]: a for a in acciones_globales_por_rol("TECNICO")}
    assert tec["iniciar_ot"]["permitida"] is True
    assert tec["registrar_pago"]["permitida"] is False


def test_resolver_origen_venta():
    from app.services.operaciones_service import resolver_origen_venta

    v_ot = Venta(id_venta=1, id_orden=99, total=Decimal("100"))
    assert resolver_origen_venta(v_ot) == ("OT", 99)

    v_most = Venta(id_venta=2, total=Decimal("50"))
    assert resolver_origen_venta(v_most) == ("MOSTRADOR", 2)

    v_ref = Venta(id_venta=3, total=Decimal("50"), comentarios="Cobro refaccion especial")
    assert resolver_origen_venta(v_ref) == ("REFACCION_ESPECIAL", None)
