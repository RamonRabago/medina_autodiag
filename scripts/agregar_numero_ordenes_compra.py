"""Agrega la columna numero a ordenes_compra si no existe.
El número tiene formato OC-YYYYMMDD-NNNN y se usa para identificar órdenes.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text


def main():
    from app.config import settings
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_compra' AND COLUMN_NAME = 'numero'"
        ))
        if r.fetchone():
            print("OK: La columna numero ya existe en ordenes_compra.")
            return 0

        # Agregar columna como nullable primero
        conn.execute(text(
            "ALTER TABLE ordenes_compra ADD COLUMN numero VARCHAR(50) NULL AFTER id_orden_compra"
        ))
        conn.commit()
        print("OK: Columna numero agregada.")

        # Poblar filas existentes: OC-LEGACY-{id} para evitar duplicados
        conn.execute(text(
            "UPDATE ordenes_compra SET numero = CONCAT('OC-LEGACY-', id_orden_compra) WHERE numero IS NULL"
        ))
        conn.commit()
        print("OK: Filas existentes actualizadas con numero.")

        # Hacer NOT NULL y UNIQUE
        conn.execute(text(
            "ALTER TABLE ordenes_compra MODIFY COLUMN numero VARCHAR(50) NOT NULL, ADD UNIQUE KEY uk_ordenes_compra_numero (numero)"
        ))
        conn.commit()
        print("OK: Columna numero configurada como NOT NULL y UNIQUE.")

    print("Migración numero en ordenes_compra completada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
