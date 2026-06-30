"""Fase 2 timezone: pagos, ventas, auditoría, movimientos inventario."""

import uuid
from datetime import datetime

import pytest

from app.models.auditoria import Auditoria
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.caja_turno import CajaTurno
from app.models.pago import Pago
from app.models.repuesto import Repuesto
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


def _usuario_token(db, rol="ADMIN"):
    uid = uuid.uuid4().hex[:8]
    u = Usuario(
        nombre=f"TZ2 {uid}",
        email=f"tz2_{uid}@test.medina",
        password_hash=hash_password("Tz2Test!9"),
        rol=rol,
        activo=True,
    )
    db.add(u)
    db.flush()
    token = create_access_token(data={"sub": str(u.id_usuario), "rol": rol})
    return token, u


@pytest.mark.integration
def test_ventas_lista_fecha_con_z(client_transactional_db, db_session_transactional):
    token, _ = _usuario_token(db_session_transactional)
    venta = Venta(total=100, estado="PAGADA", fecha=datetime(2026, 6, 30, 15, 0, 0))
    db_session_transactional.add(venta)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/ventas/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    row = next(v for v in r.json()["ventas"] if v["id_venta"] == venta.id_venta)
    assert row["fecha"].endswith("Z")


@pytest.mark.integration
def test_reporte_ingresos_pago_fecha_con_z(client_transactional_db, db_session_transactional):
    token, usuario = _usuario_token(db_session_transactional)
    venta = Venta(total=200, estado="PAGADA", fecha=datetime(2026, 6, 30, 14, 0, 0))
    db_session_transactional.add(venta)
    db_session_transactional.flush()
    turno = CajaTurno(
        id_usuario=usuario.id_usuario,
        monto_apertura=0,
        estado="CERRADO",
        fecha_apertura=datetime(2026, 6, 30, 12, 0, 0),
        fecha_cierre=datetime(2026, 6, 30, 18, 0, 0),
    )
    db_session_transactional.add(turno)
    db_session_transactional.flush()
    pago = Pago(
        id_venta=venta.id_venta,
        id_usuario=usuario.id_usuario,
        id_turno=turno.id_turno,
        monto=200,
        metodo="EFECTIVO",
        fecha=datetime(2026, 6, 30, 13, 39, 0),
    )
    db_session_transactional.add(pago)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/ventas/reportes/ingresos-detalle",
        params={"fecha_desde": "2026-06-30", "fecha_hasta": "2026-06-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    pagos = r.json()["pagos"]
    assert any(p["id_pago"] == pago.id_pago for p in pagos)
    row = next(p for p in pagos if p["id_pago"] == pago.id_pago)
    assert row["fecha"].endswith("Z")


@pytest.mark.integration
def test_auditoria_fecha_con_z(client_transactional_db, db_session_transactional):
    token, usuario = _usuario_token(db_session_transactional)
    reg = Auditoria(
        id_usuario=usuario.id_usuario,
        modulo="TEST_TZ",
        accion="SMOKE",
        id_referencia=1,
        descripcion="{}",
        fecha=datetime(2026, 6, 30, 13, 39, 0),
    )
    db_session_transactional.add(reg)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/auditoria",
        params={"fecha_desde": "2026-06-30", "fecha_hasta": "2026-06-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    item = next(i for i in r.json()["registros"] if i["id_auditoria"] == reg.id_auditoria)
    assert item["fecha"].endswith("Z")


@pytest.mark.integration
def test_movimientos_inventario_fecha_con_z(client_transactional_db, db_session_transactional):
    token, usuario = _usuario_token(db_session_transactional)
    rep = Repuesto(
        codigo=f"TZ2-{uuid.uuid4().hex[:6]}",
        nombre="Rep TZ2",
        stock_actual=10,
        stock_minimo=1,
        precio_compra=10,
        precio_venta=15,
    )
    db_session_transactional.add(rep)
    db_session_transactional.flush()
    mov = MovimientoInventario(
        id_repuesto=rep.id_repuesto,
        tipo_movimiento=TipoMovimiento.ENTRADA,
        cantidad=1,
        stock_anterior=10,
        stock_nuevo=11,
        id_usuario=usuario.id_usuario,
        fecha_movimiento=datetime(2026, 6, 30, 13, 39, 0),
        creado_en=datetime(2026, 6, 30, 13, 39, 0),
    )
    db_session_transactional.add(mov)
    db_session_transactional.commit()

    r = client_transactional_db.get(
        "/api/inventario/movimientos/",
        params={"fecha_desde": "2026-06-30", "fecha_hasta": "2026-06-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("movimientos") or data.get("items") or data
    if isinstance(items, dict):
        items = items.get("movimientos", [])
    row = next(m for m in items if m["id_movimiento"] == mov.id_movimiento)
    assert row["fecha_movimiento"].endswith("Z")
