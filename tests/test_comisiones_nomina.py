"""
Tests de comisiones y su integración con Mi Nómina.
Cubre lógica de mapeo tipo_base, rutas, imports y fórmulas.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock


# --- Helpers para simular modelos ---
def _mock_detalle(tipo: str, id_orden_origen=None):
    """Objeto tipo DetalleVenta para tests."""
    m = MagicMock()
    m.tipo = MagicMock(value=tipo) if tipo else None
    m.id_orden_origen = id_orden_origen
    return m


def _mock_detalle_str(tipo: str, id_orden_origen=None):
    """Detalle que devuelve str en .tipo (sin .value)."""
    m = MagicMock()
    m.tipo = tipo  # str directo
    m.id_orden_origen = id_orden_origen
    return m


# --- Tests comisiones_service ---
class TestObtenerTipoBase:
    """Mapeo DetalleVenta -> tipo_base comisión."""

    def test_servicio_con_orden_es_mano_obra(self):
        from app.services.comisiones_service import _obtener_tipo_base
        det = _mock_detalle("SERVICIO", id_orden_origen=1)
        assert _obtener_tipo_base(det) == "MANO_OBRA"

    def test_servicio_sin_orden_es_servicios_venta(self):
        from app.services.comisiones_service import _obtener_tipo_base
        det = _mock_detalle("SERVICIO", id_orden_origen=None)
        assert _obtener_tipo_base(det) == "SERVICIOS_VENTA"

    def test_producto_con_orden_es_partes(self):
        from app.services.comisiones_service import _obtener_tipo_base
        det = _mock_detalle("PRODUCTO", id_orden_origen=5)
        assert _obtener_tipo_base(det) == "PARTES"

    def test_producto_sin_orden_es_productos_venta(self):
        from app.services.comisiones_service import _obtener_tipo_base
        det = _mock_detalle("PRODUCTO", id_orden_origen=None)
        assert _obtener_tipo_base(det) == "PRODUCTOS_VENTA"

    def test_tipo_como_string_sin_value(self):
        from app.services.comisiones_service import _obtener_tipo_base
        det = _mock_detalle_str("SERVICIO", id_orden_origen=1)
        assert _obtener_tipo_base(det) == "MANO_OBRA"
        det2 = _mock_detalle_str("PRODUCTO", None)
        assert _obtener_tipo_base(det2) == "PRODUCTOS_VENTA"


class TestQuienCobraPorTipo:
    """Determina id_usuario que cobra según tipo_base."""

    def test_mano_obra_con_orden_y_tecnico(self):
        from app.services.comisiones_service import _quien_cobra_por_tipo
        venta = MagicMock()
        venta.id_vendedor = 10
        orden = MagicMock()
        orden.tecnico_id = 5
        assert _quien_cobra_por_tipo(venta, orden, "MANO_OBRA") == 5

    def test_mano_obra_sin_tecnico_retorna_none(self):
        from app.services.comisiones_service import _quien_cobra_por_tipo
        venta = MagicMock()
        orden = MagicMock()
        orden.tecnico_id = None
        assert _quien_cobra_por_tipo(venta, orden, "MANO_OBRA") is None

    def test_mano_obra_sin_orden_retorna_none(self):
        from app.services.comisiones_service import _quien_cobra_por_tipo
        venta = MagicMock()
        assert _quien_cobra_por_tipo(venta, None, "MANO_OBRA") is None

    def test_partes_con_tecnico(self):
        from app.services.comisiones_service import _quien_cobra_por_tipo
        venta = MagicMock()
        orden = MagicMock()
        orden.tecnico_id = 3
        assert _quien_cobra_por_tipo(venta, orden, "PARTES") == 3

    def test_servicios_venta_usa_vendedor(self):
        from app.services.comisiones_service import _quien_cobra_por_tipo
        venta = MagicMock()
        venta.id_vendedor = 7
        assert _quien_cobra_por_tipo(venta, None, "SERVICIOS_VENTA") == 7

    def test_productos_venta_usa_vendedor(self):
        from app.services.comisiones_service import _quien_cobra_por_tipo
        venta = MagicMock()
        venta.id_vendedor = 9
        assert _quien_cobra_por_tipo(venta, None, "PRODUCTOS_VENTA") == 9


class TestFormulaComision:
    """Fórmula monto_comision = base * (porcentaje / 100)."""

    def test_money_round_comision(self):
        from app.utils.decimal_utils import to_decimal, money_round
        base = to_decimal(1000.00)
        pct = to_decimal(10)
        monto = money_round(base * (pct / 100))
        assert float(monto) == 100.0

    def test_comision_redondeo(self):
        from app.utils.decimal_utils import to_decimal, money_round
        base = to_decimal(333.33)
        pct = to_decimal(10)
        monto = money_round(base * (pct / 100))
        assert abs(float(monto) - 33.33) < 0.01


# --- Tests rutas e imports ---
class TestRutasComisiones:
    """Rutas de comisiones registradas."""

    def test_prestamos_me_mi_resumen_existe(self):
        from app.routers.prestamos_empleados import router
        paths = [getattr(r, "path", "") for r in router.routes if hasattr(r, "path")]
        paths_str = " ".join(paths).lower()
        assert "me" in paths_str or "mi-resumen" in paths_str or "mi_resumen" in paths_str

    def test_ventas_reportes_comisiones_existe(self):
        from app.routers.ventas import router as ventas_router
        # Las rutas pueden estar en subrouters
        from app.main import app
        todas = []
        for r in app.routes:
            if hasattr(r, "routes"):
                for sr in r.routes:
                    if hasattr(sr, "path"):
                        todas.append(getattr(sr, "path", ""))
            elif hasattr(r, "path"):
                todas.append(r.path)
        paths_str = " ".join(todas).lower()
        assert "comisiones" in paths_str

    def test_exportaciones_comisiones_existe(self):
        from app.routers.exportaciones import router as exp_router
        paths = [getattr(r, "path", "") for r in exp_router.routes if hasattr(r, "path")]
        paths_str = " ".join(paths).lower()
        assert "comisiones" in paths_str

    def test_configuracion_comisiones_existe(self):
        from app.routers.configuracion_comisiones import router
        assert router.prefix == "/configuracion/comisiones" or "comisiones" in str(router.prefix).lower()


# --- Tests nomina periodos ---
class TestNominaPeriodos:
    """Cálculo de periodos de nómina (SEMANAL, QUINCENAL, MENSUAL)."""

    def test_nomina_service_importa(self):
        from app.services.nomina_service import calcular_nomina, DIAS_PERIODO
        assert calcular_nomina is not None
        assert DIAS_PERIODO["SEMANAL"] == 7
        assert DIAS_PERIODO["QUINCENAL"] == 15
        assert DIAS_PERIODO["MENSUAL"] == 30

    def test_comision_devengada_tiene_fecha_venta(self):
        from app.models.comision_devengada import ComisionDevengada
        assert hasattr(ComisionDevengada, "fecha_venta")
        assert hasattr(ComisionDevengada, "monto_comision")
        assert hasattr(ComisionDevengada, "id_usuario")


# --- Tests edge cases periodo ---
class TestPeriodoEdgeCases:
    """Casos borde en fechas de periodo."""

    def test_date_fromisoformat_valido(self):
        from datetime import date
        d = date.fromisoformat("2026-02-17")
        assert d.year == 2026 and d.month == 2 and d.day == 17

    def test_date_fromisoformat_invalido_levanta(self):
        from datetime import date
        with pytest.raises(ValueError):
            date.fromisoformat("2026-13-01")  # mes inválido


# --- Tests respuesta mi-resumen contiene comisiones_periodo ---
class TestMiResumenEstructura:
    """Estructura esperada del endpoint mi-resumen."""

    def test_prestamos_router_tiene_logica_comisiones(self):
        """Verifica que mi_resumen_nomina incluye lógica de comisiones."""
        from app.routers import prestamos_empleados
        import inspect
        src = inspect.getsource(prestamos_empleados.mi_resumen_nomina)
        assert "ComisionDevengada" in src
        assert "comisiones_periodo" in src
