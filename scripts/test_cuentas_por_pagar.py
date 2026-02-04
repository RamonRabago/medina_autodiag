"""
Verificación del módulo Cuentas por pagar.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    try:
        # 1. Imports
        from app.routers.ordenes_compra import router as oc_router
        from app.models.pago_orden_compra import PagoOrdenCompra
        from app.services.auditoria_service import registrar as registrar_auditoria
        print("OK: Imports correctos")

        # 2. Rutas (paths pueden variar según estructura del router)
        paths_str = str([getattr(r, "path", "") for r in oc_router.routes])
        assert "cuentas-por-pagar" in paths_str or "cuentas_por_pagar" in paths_str, "Falta ruta cuentas-por-pagar"
        assert "pagar" in paths_str, "Falta ruta pagar"
        print("OK: Rutas cuentas-por-pagar y pagar registradas")

        # 3. Schema PagoOrdenCompraCreate
        from app.schemas.orden_compra import PagoOrdenCompraCreate
        d = PagoOrdenCompraCreate(monto=100.0, metodo="EFECTIVO", referencia=None)
        assert d.monto == 100.0
        assert d.metodo == "EFECTIVO"
        print("OK: Schema PagoOrdenCompraCreate válido")

        # 4. Estructura respuesta listar
        estructura = {"items", "total_cuentas", "total_saldo_pendiente"}
        print("OK: Estructura de respuesta esperada documentada")

        print("\n--- Verificación Cuentas por pagar: TODO OK ---")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
