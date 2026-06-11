"""
Tests unitarios — acciones_operativas_service (P4.0).

No requieren MySQL: sesión simulada con MagicMock.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.caja_turno import CajaTurno
from app.models.orden_trabajo import EstadoOrden, OrdenTrabajo
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.services.acciones_operativas_service import (
    ACCIONES_FINANCIERAS_ITEM_ONLY,
    accion_global_item_only,
    acciones_globales_financieras_item_only,
    evaluar_crear_venta_desde_ot,
    evaluar_registrar_pago,
    evaluar_registrar_pago_ot,
    venta_es_activa,
)


def _usuario(rol: str, uid: int = 42) -> Usuario:
    return Usuario(
        id_usuario=uid,
        nombre=f"Test {rol}",
        email=f"ops_{rol.lower()}@test.medina",
        password_hash="x",
        rol=rol,
        activo=True,
    )


def _venta(**kwargs) -> Venta:
    defaults = {
        "id_venta": 100,
        "total": Decimal("1000.00"),
        "estado": "PENDIENTE",
    }
    defaults.update(kwargs)
    return Venta(**defaults)


def _orden(**kwargs) -> OrdenTrabajo:
    defaults = {
        "id": 50,
        "numero_orden": "OT-TEST-001",
        "vehiculo_id": 1,
        "cliente_id": 1,
        "estado": EstadoOrden.COMPLETADA,
        "fecha_ingreso": datetime.utcnow(),
        "total": Decimal("800.00"),
        "subtotal_servicios": Decimal("800.00"),
        "subtotal_repuestos": Decimal("0.00"),
        "descuento": Decimal("0.00"),
    }
    defaults.update(kwargs)
    return OrdenTrabajo(**defaults)


def _mock_db(*, turno=None, total_pagado=0.0, venta_por_orden=None):
    """Simula consultas de turno, saldo y venta activa por OT."""
    session = MagicMock()
    turno_query = MagicMock()
    turno_query.filter.return_value.first.return_value = turno

    pago_query = MagicMock()
    pago_query.filter.return_value.scalar.return_value = total_pagado

    venta_query = MagicMock()
    venta_query.filter.return_value.order_by.return_value.first.return_value = venta_por_orden

    def query_side_effect(model_or_func, *args, **kwargs):
        if model_or_func is CajaTurno:
            return turno_query
        if model_or_func is Venta:
            return venta_query
        # db.query(func.coalesce(func.sum(Pago.monto), 0)) — suma de pagos
        return pago_query

    session.query.side_effect = query_side_effect
    return session


class TestAccionesGlobalesItemOnly:
    @pytest.mark.parametrize("accion", ACCIONES_FINANCIERAS_ITEM_ONLY)
    def test_global_nunca_permitida(self, accion):
        ev = accion_global_item_only(accion)
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "REQUIERE_CONTEXTO_ENTIDAD"
        assert ev.alcance == "item_only"
        assert ev.motivo_bloqueo

    def test_lista_completa_financieras(self):
        acciones = {a.accion for a in acciones_globales_financieras_item_only()}
        assert acciones == set(ACCIONES_FINANCIERAS_ITEM_ONLY)


class TestVentaEsActiva:
    def test_activa_pendiente(self):
        assert venta_es_activa(_venta(estado="PENDIENTE")) is True

    def test_cancelada_no_activa(self):
        assert venta_es_activa(_venta(estado="CANCELADA")) is False

    def test_none_no_activa(self):
        assert venta_es_activa(None) is False


class TestEvaluarRegistrarPago:
    def test_rechaza_rol_tecnico(self):
        db = _mock_db()
        ev = evaluar_registrar_pago(db, _venta(), _usuario("TECNICO"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "ROL_NO_PERMITIDO"

    def test_rechaza_sin_turno(self):
        db = _mock_db(turno=None)
        ev = evaluar_registrar_pago(db, _venta(), _usuario("CAJA"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "TURNO_CERRADO"

    def test_rechaza_venta_inexistente(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno)
        ev = evaluar_registrar_pago(db, None, _usuario("CAJA"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "VENTA_INEXISTENTE"

    def test_rechaza_venta_cancelada(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno, total_pagado=0)
        ev = evaluar_registrar_pago(db, _venta(estado="CANCELADA"), _usuario("CAJA"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "VENTA_CANCELADA"

    def test_rechaza_saldo_cero(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno, total_pagado=1000.0)
        ev = evaluar_registrar_pago(db, _venta(total=Decimal("1000.00")), _usuario("CAJA"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "SALDO_CERO"

    def test_rechaza_pago_excede_total(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno, total_pagado=400.0)
        ev = evaluar_registrar_pago(
            db,
            _venta(total=Decimal("1000.00")),
            _usuario("CAJA"),
            monto=700.0,
        )
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "PAGO_EXCEDE_TOTAL"

    def test_permitida_con_turno_y_saldo(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno, total_pagado=400.0)
        venta = _venta(total=Decimal("1000.00"))
        ev = evaluar_registrar_pago(db, venta, _usuario("CAJA"))
        assert ev.permitida is True
        assert ev.codigo_bloqueo is None
        assert ev.contexto == {"id_venta": 100, "saldo_pendiente": 600.0}

    def test_permitida_admin_con_turno(self):
        turno = CajaTurno(id_turno=2, id_usuario=99, estado="ABIERTO")
        db = _mock_db(turno=turno, total_pagado=0.0)
        ev = evaluar_registrar_pago(db, _venta(), _usuario("ADMIN", uid=99))
        assert ev.permitida is True

    def test_monto_valido_no_excede(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno, total_pagado=400.0)
        ev = evaluar_registrar_pago(
            db,
            _venta(total=Decimal("1000.00")),
            _usuario("CAJA"),
            monto=600.0,
        )
        assert ev.permitida is True


class TestEvaluarRegistrarPagoOt:
    def test_sin_venta_vinculada(self):
        turno = CajaTurno(id_turno=1, id_usuario=42, estado="ABIERTO")
        db = _mock_db(turno=turno, venta_por_orden=None)
        ev = evaluar_registrar_pago_ot(db, _orden(), _usuario("CAJA"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "VENTA_INEXISTENTE"


class TestEvaluarCrearVentaDesdeOt:
    def test_rechaza_rol_tecnico(self):
        db = _mock_db()
        ev = evaluar_crear_venta_desde_ot(db, _orden(), _usuario("TECNICO"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "ROL_NO_PERMITIDO"

    def test_rechaza_estado_invalido(self):
        db = _mock_db(venta_por_orden=None)
        ev = evaluar_crear_venta_desde_ot(
            db,
            _orden(estado=EstadoOrden.PENDIENTE),
            _usuario("CAJA"),
        )
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "ESTADO_INVALIDO"

    def test_rechaza_venta_existente(self):
        venta = _venta(id_orden=50)
        db = _mock_db(venta_por_orden=venta)
        ev = evaluar_crear_venta_desde_ot(db, _orden(), _usuario("CAJA"))
        assert ev.permitida is False
        assert ev.codigo_bloqueo == "VENTA_EXISTENTE"

    def test_permitida_ot_completada_sin_venta(self):
        db = _mock_db(venta_por_orden=None)
        ev = evaluar_crear_venta_desde_ot(db, _orden(), _usuario("CAJA"))
        assert ev.permitida is True
