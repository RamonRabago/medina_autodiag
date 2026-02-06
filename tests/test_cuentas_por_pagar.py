"""
Tests del módulo Cuentas por pagar.
Port de scripts/test_cuentas_por_pagar.py a pytest.
"""
import pytest


def test_ordenes_compra_imports():
    """Imports de ordenes_compra correctos."""
    from app.routers.ordenes_compra import router as oc_router
    from app.models.pago_orden_compra import PagoOrdenCompra
    assert oc_router is not None
    assert PagoOrdenCompra is not None


def test_cuentas_por_pagar_rutas():
    """Rutas cuentas-por-pagar y pagar registradas."""
    from app.routers.ordenes_compra import router as oc_router
    paths_str = str([getattr(r, "path", "") for r in oc_router.routes])
    assert "cuentas-por-pagar" in paths_str or "cuentas_por_pagar" in paths_str
    assert "pagar" in paths_str


def test_pago_orden_compra_create_schema():
    """Schema PagoOrdenCompraCreate válido."""
    from app.schemas.orden_compra import PagoOrdenCompraCreate
    d = PagoOrdenCompraCreate(monto=100.0, metodo="EFECTIVO", referencia=None)
    assert d.monto == 100.0
    assert d.metodo == "EFECTIVO"
