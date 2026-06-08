"""Tests unitarios helpers recepción rápida / OT mínima."""
from unittest.mock import MagicMock

from app.routers.ordenes_trabajo.helpers import orden_tiene_servicios_o_repuestos


def test_orden_tiene_servicios_o_repuestos_vacio():
    orden = MagicMock()
    orden.detalles_servicio = []
    orden.detalles_repuesto = []
    assert orden_tiene_servicios_o_repuestos(orden) is False


def test_orden_tiene_servicios_o_repuestos_con_servicio():
    orden = MagicMock()
    orden.detalles_servicio = [MagicMock()]
    orden.detalles_repuesto = []
    assert orden_tiene_servicios_o_repuestos(orden) is True


def test_orden_tiene_servicios_o_repuestos_con_repuesto():
    orden = MagicMock()
    orden.detalles_servicio = []
    orden.detalles_repuesto = [MagicMock()]
    assert orden_tiene_servicios_o_repuestos(orden) is True
