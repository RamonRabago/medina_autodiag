"""
Limpia los datos de las tablas principales para empezar a poblar de cero.

Ejecutar: python scripts/limpiar_tablas.py

IMPORTANTE: Respetando FK, se eliminan en orden (hijos primero).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("\n=== Limpiar tablas (datos de prueba/población) ===\n")

    from app.database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # Orden: tablas hijas primero (que referencian a otras)
        tablas = [
            "detalle_venta", "pagos",            # ventas
            "detalles_orden_trabajo", "detalles_repuesto_orden",  # ordenes_trabajo
            "movimientos_inventario", "alertas_inventario",
            "gastos_operativos", "caja_alertas",
            "detalles_orden_compra", "pagos_orden_compra",
            "ventas", "ordenes_trabajo",
            "ordenes_compra",
            "usuario_bodegas",
            "vehiculos",
            "repuestos",
            "servicios", "categorias_servicios", "categorias_repuestos",
            "clientes", "proveedores",
            "caja_turnos",
        ]

        db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for tabla in tablas:
            try:
                db.execute(text(f"TRUNCATE TABLE {tabla}"))
                print(f"  [OK] {tabla}")
            except Exception as e:
                print(f"  [SKIP] {tabla}: {e}")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.commit()

        print("\n[OK] Tablas limpiadas. Puedes empezar a crear datos nuevos.\n")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
