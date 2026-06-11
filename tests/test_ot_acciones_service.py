"""
Tests del evaluador centralizado de acciones OT.

Unitarios: no requieren MySQL.
Integración: requieren MySQL (pytest.skip si no hay BD).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo, PrioridadOrden
from app.models.usuario import Usuario
from app.services.ot_acciones_service import (
    ALLOW_TECNICO_SELF_ASSIGN,
    asegurar_accion_ot_permitida,
    evaluar_accion_ot,
)
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _orden_base(**kwargs) -> OrdenTrabajo:
    defaults = {
        "numero_orden": f"OT-T-{uuid.uuid4().hex[:6]}",
        "vehiculo_id": 1,
        "cliente_id": 1,
        "estado": EstadoOrden.PENDIENTE,
        "prioridad": PrioridadOrden.NORMAL,
        "fecha_ingreso": datetime.utcnow(),
        "total": Decimal("0"),
        "subtotal_servicios": Decimal("0"),
        "subtotal_repuestos": Decimal("0"),
        "descuento": Decimal("0"),
        "requiere_autorizacion": False,
        "autorizado": False,
        "detalles_servicio": [],
        "detalles_repuesto": [],
    }
    defaults.update(kwargs)
    return OrdenTrabajo(**defaults)


def _orden_con_items(**kwargs) -> OrdenTrabajo:
    """OT con al menos un ítem sin persistir relaciones SQLAlchemy."""
    orden = _orden_base(**kwargs)
    object.__setattr__(orden, "detalles_servicio", [MagicMock()])
    return orden


def _usuario(rol: str, uid: int = 99) -> Usuario:
    return Usuario(
        id_usuario=uid,
        nombre=f"Test {rol}",
        email=f"test_{rol.lower()}@test.medina",
        password_hash="x",
        rol=rol,
        activo=True,
    )


class _FakeSession:
    """Sesión mínima para evaluaciones que no consultan stock."""

    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


def test_iniciar_rechaza_sin_items():
    orden = _orden_base()
    usuario = _usuario("TECNICO")
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "iniciar_ot")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "SIN_ITEMS"


def test_iniciar_rechaza_esperando_repuestos():
    orden = _orden_con_items(estado=EstadoOrden.ESPERANDO_REPUESTOS, tecnico_id=99)
    usuario = _usuario("TECNICO", uid=99)
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "iniciar_ot")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "ESTADO_INVALIDO"


def test_iniciar_rechaza_sin_autorizacion_cliente():
    orden = _orden_con_items(
        estado=EstadoOrden.ESPERANDO_AUTORIZACION,
        requiere_autorizacion=True,
        autorizado=False,
        tecnico_id=99,
    )
    usuario = _usuario("TECNICO", uid=99)
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "iniciar_ot")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "SIN_AUTORIZACION"


def test_iniciar_tecnico_sin_asignar_compat_self_assign():
    if not ALLOW_TECNICO_SELF_ASSIGN:
        pytest.skip("ALLOW_TECNICO_SELF_ASSIGN desactivado")
    orden = _orden_con_items(tecnico_id=None)
    usuario = _usuario("TECNICO", uid=7)
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "iniciar_ot")
    assert ev.permitida is True


def test_iniciar_admin_sin_tecnico_rechaza():
    orden = _orden_con_items(tecnico_id=None)
    usuario = _usuario("ADMIN")
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "iniciar_ot")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "SIN_TECNICO"


def test_finalizar_solo_en_proceso():
    orden = _orden_con_items(estado=EstadoOrden.PENDIENTE, tecnico_id=5)
    usuario = _usuario("TECNICO", uid=5)
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "finalizar_ot")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "ESTADO_INVALIDO"


def test_finalizar_tecnico_ajeno_rechaza():
    orden = _orden_con_items(estado=EstadoOrden.EN_PROCESO, tecnico_id=1)
    usuario = _usuario("TECNICO", uid=2)
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "finalizar_ot")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "TECNICO_NO_ASIGNADO"


def test_asegurar_lanza_http_exception():
    orden = _orden_base(estado=EstadoOrden.EN_PROCESO)
    usuario = _usuario("CAJA")
    with pytest.raises(HTTPException) as exc:
        asegurar_accion_ot_permitida(_FakeSession(), orden, usuario, "iniciar_ot")
    assert exc.value.status_code == 403


def test_pausar_refaccion_no_implementado():
    orden = _orden_base(estado=EstadoOrden.EN_PROCESO, tecnico_id=1)
    usuario = _usuario("TECNICO", uid=1)
    ev = evaluar_accion_ot(_FakeSession(), orden, usuario, "pausar_refaccion")
    assert ev.permitida is False
    assert ev.codigo_bloqueo == "NO_IMPLEMENTADO"


@pytest.mark.integration
def test_a0_iniciar_coherente_con_evaluador(client_transactional_db, db_session_transactional):
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo

    uid = uuid.uuid4().hex[:8]
    tecnico = Usuario(
        nombre="Tec Ops",
        email=f"tec_ops_{uid}@test.medina",
        password_hash=hash_password("OpsSecret!9"),
        rol="TECNICO",
        activo=True,
    )
    db_session_transactional.add(tecnico)
    db_session_transactional.flush()

    cliente = Cliente(nombre=f"Cli {uid}", telefono=f"644{int(uid[:7], 16) % 10_000_000:07d}")
    db_session_transactional.add(cliente)
    db_session_transactional.flush()
    vehiculo = Vehiculo(id_cliente=cliente.id_cliente, marca="Nissan", modelo="Versa", anio=2020)
    db_session_transactional.add(vehiculo)
    db_session_transactional.flush()

    ot_sin_items = OrdenTrabajo(
        numero_orden=f"OT-EV-{uid}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=tecnico.id_usuario,
        estado=EstadoOrden.PENDIENTE,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("0"),
        subtotal_servicios=Decimal("0"),
        subtotal_repuestos=Decimal("0"),
        descuento=Decimal("0"),
    )
    db_session_transactional.add(ot_sin_items)
    db_session_transactional.flush()

    token = create_access_token(data={"sub": str(tecnico.id_usuario), "rol": "TECNICO"})
    r = client_transactional_db.get("/api/operaciones/resumen", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()["bandejas"]["ot_pendientes"]["items"]
    item = next(i for i in items if i["id"] == ot_sin_items.id)
    iniciar = next(a for a in item["acciones"] if a["accion"] == "iniciar_ot")
    assert iniciar["permitida"] is False
    assert iniciar["codigo_bloqueo"] == "SIN_ITEMS"

    ev = evaluar_accion_ot(db_session_transactional, ot_sin_items, tecnico, "iniciar_ot")
    assert iniciar["permitida"] == ev.permitida
    assert iniciar["codigo_bloqueo"] == ev.codigo_bloqueo


@pytest.mark.integration
def test_iniciar_api_rechaza_coherente_con_evaluador(client_transactional_db, db_session_transactional):
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo

    uid = uuid.uuid4().hex[:10]
    tecnico = Usuario(
        nombre="Tec API",
        email=f"tec_api_{uid}@test.medina",
        password_hash=hash_password("OpsSecret!9"),
        rol="TECNICO",
        activo=True,
    )
    db_session_transactional.add(tecnico)
    db_session_transactional.flush()

    cliente = Cliente(nombre=f"Cli {uid}", telefono=f"644{int(uid[:7], 16) % 10_000_000:07d}")
    db_session_transactional.add(cliente)
    db_session_transactional.flush()
    vehiculo = Vehiculo(id_cliente=cliente.id_cliente, marca="Toyota", modelo="Corolla", anio=2019)
    db_session_transactional.add(vehiculo)
    db_session_transactional.flush()

    ot = OrdenTrabajo(
        numero_orden=f"OT-API-{uid[:6]}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        tecnico_id=tecnico.id_usuario,
        estado=EstadoOrden.ESPERANDO_REPUESTOS,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("100"),
        subtotal_servicios=Decimal("100"),
        subtotal_repuestos=Decimal("0"),
        descuento=Decimal("0"),
    )
    db_session_transactional.add(ot)
    db_session_transactional.flush()

    token = create_access_token(data={"sub": str(tecnico.id_usuario), "rol": "TECNICO"})
    ev = evaluar_accion_ot(db_session_transactional, ot, tecnico, "iniciar_ot")
    assert ev.permitida is False

    r = client_transactional_db.post(
        f"/api/ordenes-trabajo/{ot.id}/iniciar",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


@pytest.mark.integration
def test_detalle_ot_incluye_acciones(client_transactional_db, db_session_transactional):
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo

    uid = uuid.uuid4().hex[:8]
    admin = Usuario(
        nombre="Admin Ops",
        email=f"adm_ops_{uid}@test.medina",
        password_hash=hash_password("OpsSecret!9"),
        rol="ADMIN",
        activo=True,
    )
    db_session_transactional.add(admin)
    db_session_transactional.flush()

    cliente = Cliente(nombre=f"Cli {uid}", telefono=f"644{int(uid[:7], 16) % 10_000_000:07d}")
    db_session_transactional.add(cliente)
    db_session_transactional.flush()
    vehiculo = Vehiculo(id_cliente=cliente.id_cliente, marca="Honda", modelo="Civic", anio=2018)
    db_session_transactional.add(vehiculo)
    db_session_transactional.flush()

    from app.models.categoria_servicio import CategoriaServicio
    from app.models.detalle_orden import DetalleOrdenTrabajo
    from app.models.servicio import Servicio

    categoria = CategoriaServicio(nombre=f"Cat OT {uid}", descripcion="Test")
    db_session_transactional.add(categoria)
    db_session_transactional.flush()
    servicio = Servicio(
        codigo=f"SRV-{uid}",
        nombre="Servicio prueba OT",
        id_categoria=categoria.id,
        precio_base=Decimal("50"),
    )
    db_session_transactional.add(servicio)
    db_session_transactional.flush()

    ot = OrdenTrabajo(
        numero_orden=f"OT-DET-{uid}",
        vehiculo_id=vehiculo.id_vehiculo,
        cliente_id=cliente.id_cliente,
        estado=EstadoOrden.EN_PROCESO,
        fecha_ingreso=datetime.utcnow(),
        total=Decimal("50"),
        subtotal_servicios=Decimal("50"),
        subtotal_repuestos=Decimal("0"),
        descuento=Decimal("0"),
    )
    db_session_transactional.add(ot)
    db_session_transactional.flush()
    db_session_transactional.add(
        DetalleOrdenTrabajo(
            orden_trabajo_id=ot.id,
            servicio_id=servicio.id,
            descripcion="Servicio prueba detalle OT",
            cantidad=1,
            precio_unitario=Decimal("50"),
            subtotal=Decimal("50"),
        )
    )
    db_session_transactional.flush()

    token = create_access_token(data={"sub": str(admin.id_usuario), "rol": "ADMIN"})
    r = client_transactional_db.get(f"/api/ordenes-trabajo/{ot.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "acciones" in data
    assert isinstance(data["acciones"], list)
    nombres = {a["accion"] for a in data["acciones"]}
    assert "iniciar_ot" in nombres
    assert "finalizar_ot" in nombres
    fin = next(a for a in data["acciones"] if a["accion"] == "finalizar_ot")
    assert fin["permitida"] is True
