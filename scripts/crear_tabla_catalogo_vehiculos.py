"""Crea la tabla catalogo_vehiculos e id_catalogo_vehiculo en ordenes_compra."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from app.config import settings


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # 1. Crear tabla catalogo_vehiculos
        r = conn.execute(text(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'catalogo_vehiculos'"
        ))
        if not r.fetchone():
            conn.execute(text("""
                CREATE TABLE catalogo_vehiculos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    anio INT NOT NULL,
                    marca VARCHAR(80) NOT NULL,
                    modelo VARCHAR(80) NOT NULL,
                    version_trim VARCHAR(100) NULL,
                    motor VARCHAR(80) NULL,
                    vin VARCHAR(50) NULL,
                    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("OK: Tabla catalogo_vehiculos creada.")
        else:
            print("OK: Tabla catalogo_vehiculos ya existe.")

        # 2. Agregar id_catalogo_vehiculo a ordenes_compra
        r2 = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_compra' AND COLUMN_NAME = 'id_catalogo_vehiculo'"
        ))
        if not r2.fetchone():
            conn.execute(text("""
                ALTER TABLE ordenes_compra
                ADD COLUMN id_catalogo_vehiculo INT NULL,
                ADD CONSTRAINT fk_orden_compra_catalogo_vehiculo
                FOREIGN KEY (id_catalogo_vehiculo) REFERENCES catalogo_vehiculos(id)
            """))
            conn.commit()
            print("OK: Columna id_catalogo_vehiculo agregada a ordenes_compra.")
        else:
            print("OK: Columna id_catalogo_vehiculo ya existe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
