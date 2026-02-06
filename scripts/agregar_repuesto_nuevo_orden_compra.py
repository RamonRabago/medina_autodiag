"""Agrega soporte para repuesto nuevo en órdenes de compra.
- id_repuesto nullable en detalles_orden_compra
- codigo_nuevo, nombre_nuevo para ítems que aún no están en inventario
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from app.config import settings


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # Verificar y agregar codigo_nuevo
        r = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalles_orden_compra' AND COLUMN_NAME = 'codigo_nuevo'"
        ))
        if not r.fetchone():
            conn.execute(text(
                "ALTER TABLE detalles_orden_compra ADD COLUMN codigo_nuevo VARCHAR(100) NULL"
            ))
            conn.commit()
            print("OK: codigo_nuevo agregado")

        # Verificar y agregar nombre_nuevo
        r = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalles_orden_compra' AND COLUMN_NAME = 'nombre_nuevo'"
        ))
        if not r.fetchone():
            conn.execute(text(
                "ALTER TABLE detalles_orden_compra ADD COLUMN nombre_nuevo VARCHAR(200) NULL"
            ))
            conn.commit()
            print("OK: nombre_nuevo agregado")

        # Hacer id_repuesto nullable
        r = conn.execute(text(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalles_orden_compra' AND COLUMN_NAME = 'id_repuesto'"
        ))
        row = r.fetchone()
        if row and row[0] != "YES":
            conn.execute(text(
                "ALTER TABLE detalles_orden_compra MODIFY COLUMN id_repuesto INT NULL"
            ))
            conn.commit()
            print("OK: id_repuesto ahora nullable")
        else:
            print("OK: id_repuesto ya era nullable")

    print("Migración repuesto nuevo en orden de compra completada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
