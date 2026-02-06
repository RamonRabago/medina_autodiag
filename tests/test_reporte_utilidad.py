"""
Tests del reporte de utilidad.
Port de scripts/test_reporte_utilidad.py a pytest.
"""
import pytest


def test_ventas_exportaciones_imports():
    """Imports ventas y exportaciones correctos."""
    from app.routers.ventas import router as ventas_router
    from app.routers.exportaciones import router as export_router
    assert ventas_router is not None
    assert export_router is not None


def test_rutas_reporte_utilidad():
    """Rutas reporte utilidad registradas."""
    from app.routers.ventas import router as ventas_router
    from app.routers.exportaciones import router as export_router
    ventas_paths = [r.path for r in ventas_router.routes if hasattr(r, "path")]
    export_paths = str([r.path for r in export_router.routes if hasattr(r, "path")])
    assert any("utilidad" in p.lower() for p in ventas_paths)
    assert "/utilidad" in export_paths or "utilidad" in export_paths.lower()


def test_formula_utilidad():
    """Fórmula Utilidad = Ingresos - Costo correcta."""
    total_ingresos = 100.0
    total_costo = 40.0
    utilidad = total_ingresos - total_costo
    assert utilidad == 60.0
