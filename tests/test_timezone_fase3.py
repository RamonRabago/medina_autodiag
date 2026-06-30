"""Fase 3 timezone: citas local, OC, devoluciones, ordenes_hoy TZ-1."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.cita import Cita, EstadoCita, TipoCita
from app.models.cliente import Cliente
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.orden_compra import EstadoOrdenCompra, OrdenCompra
from app.models.proveedor import Proveedor
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.utils.fechas import ahora_local, hoy_taller
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _token(db, rol="ADMIN"):
    uid = uuid.uuid4().hex[:8]
    u = Usuario(
        nombre=f"TZ3 {uid}",
        email=f"tz3_{uid}@test.medina",
        password_hash=hash_password("Tz3Test!9"),
        rol=rol,
        activo=True,
    )
    db.add(u)
    db.flush()
    return create_access_token(data={"sub": str(u.id_usuario), "rol": rol}), u


@pytest.mark.integration
def test_citas_fecha_hora_sin_z(client_transactional_db, db_session_transactional):
    token, _ = _token(db_session_transactional)
    cli = Cliente(nombre="Cli Cita TZ", telefono="8681234567")
    db_session_transactional.add(cli)
    db_session_transactional.flush()
    fh = ahora_local() + timedelta(days=1)
    cita = Cita(
        id_cliente=cli.id_cliente,
        fecha_hora=fh,
        tipo=TipoCita.REVISION,
        estado=EstadoCita.CONFIRMADA,
    )
    db_session_transactional.add(cita)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        f"/api/citas/{cita.id_cita}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fecha_hora"]
    assert not body["fecha_hora"].endswith("Z")
    if body.get("creado_en"):
        assert body["creado_en"].endswith("Z")


@pytest.mark.integration
def test_citas_filtro_dia_local(client_transactional_db, db_session_transactional):
    token, _ = _token(db_session_transactional)
    cli = Cliente(nombre="Cli Filtro", telefono="8689999999")
    db_session_transactional.add(cli)
    db_session_transactional.flush()
    dia = hoy_taller()
    cita = Cita(
        id_cliente=cli.id_cliente,
        fecha_hora=datetime.combine(dia, datetime.min.time().replace(hour=15, minute=30)),
        tipo=TipoCita.DIAGNOSTICO,
        estado=EstadoCita.CONFIRMADA,
    )
    db_session_transactional.add(cita)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/citas/",
        params={"fecha_desde": dia.isoformat(), "fecha_hasta": dia.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    ids = [c["id_cita"] for c in r.json()["citas"]]
    assert cita.id_cita in ids


@pytest.mark.integration
def test_devoluciones_fecha_con_z(client_transactional_db, db_session_transactional):
    token, usuario = _token(db_session_transactional)
    rep = Repuesto(
        codigo=f"TZ3-{uuid.uuid4().hex[:6]}",
        nombre="Rep dev",
        stock_actual=5,
        stock_minimo=1,
        precio_compra=1,
        precio_venta=2,
    )
    db_session_transactional.add(rep)
    db_session_transactional.flush()
    mov = MovimientoInventario(
        id_repuesto=rep.id_repuesto,
        tipo_movimiento=TipoMovimiento.ENTRADA,
        cantidad=1,
        stock_anterior=5,
        stock_nuevo=6,
        id_usuario=usuario.id_usuario,
        motivo="Devolución por cancelación de venta #99",
        fecha_movimiento=datetime(2026, 6, 30, 13, 39, 0),
        creado_en=datetime(2026, 6, 30, 13, 39, 0),
    )
    db_session_transactional.add(mov)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/devoluciones/",
        params={"fecha_desde": "2026-06-30", "fecha_hasta": "2026-06-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    row = next(d for d in r.json()["devoluciones"] if d["id_movimiento"] == mov.id_movimiento)
    assert row["fecha_movimiento"].endswith("Z")


@pytest.mark.integration
def test_ordenes_compra_detalle_fecha_con_z(client_transactional_db, db_session_transactional):
    token, usuario = _token(db_session_transactional)
    prov = Proveedor(nombre=f"Prov TZ3 {uuid.uuid4().hex[:6]}", email="p@test.com")
    db_session_transactional.add(prov)
    db_session_transactional.flush()
    oc = OrdenCompra(
        numero=f"OC-TZ3-{uuid.uuid4().hex[:4]}",
        id_proveedor=prov.id_proveedor,
        id_usuario=usuario.id_usuario,
        estado=EstadoOrdenCompra.BORRADOR,
        total_estimado=100,
        fecha=datetime(2026, 6, 30, 13, 0, 0),
    )
    db_session_transactional.add(oc)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        f"/api/ordenes-compra/{oc.id_orden_compra}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["fecha"].endswith("Z")


@pytest.mark.integration
def test_catalogos_ordenes_hoy_cuenta_ot_tz1(client_transactional_db, db_session_transactional):
    """OT creada hoy (recepción rápida TZ-1) debe contar en ordenes_hoy."""
    token, usuario = _token(db_session_transactional, rol="CAJA")
    uid = uuid.uuid4().hex[:6]
    cli = Cliente(nombre=f"Cli OH {uid}", telefono="8681111111")
    db_session_transactional.add(cli)
    db_session_transactional.flush()
    veh = Vehiculo(id_cliente=cli.id_cliente, marca="Nissan", modelo="Sentra", anio=2020)
    db_session_transactional.add(veh)
    db_session_transactional.flush()

    r_ot = client_transactional_db.post(
        "/api/ordenes-trabajo/recepcion-rapida",
        json={
            "cliente_id": cli.id_cliente,
            "vehiculo_id": veh.id_vehiculo,
            "motivo": "Smoke ordenes_hoy TZ-3",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_ot.status_code == 201, r_ot.text

    r = client_transactional_db.get(
        "/api/ordenes-trabajo/estadisticas/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ordenes_hoy"] >= 1
