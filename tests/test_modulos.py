"""
Tests de verificación de módulos: imports, rutas y estructura.
Port de scripts/test_modulos_recientes.py a pytest.
"""
import pytest


def test_app_main_inicia():
    """App main inicia correctamente."""
    from app.main import app
    assert app is not None


def test_inventario_reportes_rutas():
    """Router inventario_reportes tiene rutas sugerencia-compra, auditoria-ajustes."""
    from app.routers.inventario_reportes import router as inv_rep_router
    paths = [getattr(r, "path", "") for r in inv_rep_router.routes if hasattr(r, "path")]
    paths_str = " ".join(paths).lower()
    assert "sugerencia-compra" in paths_str or "sugerencia_compra" in paths_str
    assert "auditoria-ajustes" in paths_str or "auditoria_ajustes" in paths_str


def test_exportaciones_rutas():
    """Router exportaciones tiene sugerencia-compra y ajustes-inventario."""
    from app.routers.exportaciones import router as exp_router
    paths = [getattr(r, "path", "") for r in exp_router.routes if hasattr(r, "path")]
    exp_str = " ".join(paths).lower()
    assert "sugerencia-compra" in exp_str or "sugerencia_compra" in exp_str
    assert "ajustes-inventario" in exp_str or "ajustes_inventario" in exp_str


def test_ordenes_compra_cuentas_por_pagar():
    """Ordenes de compra tiene cuentas-por-pagar."""
    from app.routers.ordenes_compra import router as oc_router
    oc_paths = str([getattr(r, "path", "") for r in oc_router.routes])
    assert "cuentas-por-pagar" in oc_paths or "cuentas_por_pagar" in oc_paths


def test_ventas_reporte_utilidad():
    """Ventas tiene reporte utilidad."""
    from app.routers.ventas import router as ventas_router
    v_paths = [r.path for r in ventas_router.routes if hasattr(r, "path")]
    assert any("utilidad" in str(p).lower() for p in v_paths)


def test_inventario_service_metodos():
    """InventarioService tiene registrar_movimiento y ajustar_inventario."""
    from app.services.inventario_service import InventarioService
    assert hasattr(InventarioService, "registrar_movimiento")
    assert hasattr(InventarioService, "ajustar_inventario")


def test_decimal_utils():
    """decimal_utils funciona correctamente."""
    from app.utils.decimal_utils import to_decimal, money_round
    assert to_decimal(10.5) is not None
    mr = money_round(10.555)
    assert abs(float(mr) - 10.56) < 0.01


def test_movimiento_inventario_tipos():
    """Modelo MovimientoInventario y tipos correctos."""
    from app.models.movimiento_inventario import TipoMovimiento
    assert TipoMovimiento.AJUSTE_POSITIVO.value == "AJUSTE+"
    assert TipoMovimiento.AJUSTE_NEGATIVO.value == "AJUSTE-"
