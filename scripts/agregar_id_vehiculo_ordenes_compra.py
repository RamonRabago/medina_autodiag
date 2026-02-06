"""Agrega id_vehiculo a ordenes_compra y asegura vehiculos.id_cliente permite NULL."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from app.config import settings


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # 1. Verificar si id_vehiculo ya existe en ordenes_compra
        r = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_compra' AND COLUMN_NAME = 'id_vehiculo'"
        ))
        if not r.fetchone():
            conn.execute(text(
                "ALTER TABLE ordenes_compra ADD COLUMN id_vehiculo INT NULL, "
                "ADD CONSTRAINT fk_orden_compra_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id_vehiculo)"
            ))
            conn.commit()
            print("OK: Columna id_vehiculo agregada a ordenes_compra.")
        else:
            print("OK: La columna id_vehiculo ya existe en ordenes_compra.")

        # 2. Asegurar que vehiculos.id_cliente permite NULL (para vehículos sin cliente)
        r2 = conn.execute(text(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'vehiculos' AND COLUMN_NAME = 'id_cliente'"
        ))
        row = r2.fetchone()
        if row and row[0] == 'NO':
            conn.execute(text("ALTER TABLE vehiculos MODIFY COLUMN id_cliente INT NULL"))
            conn.commit()
            print("OK: vehiculos.id_cliente ahora permite NULL.")
        else:
            print("OK: vehiculos.id_cliente ya permite NULL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
