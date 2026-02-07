"""Agrega la columna evidencia_cancelacion_url a ordenes_compra si no existe."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import text
from app.config import settings
from sqlalchemy import create_engine


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_compra' AND COLUMN_NAME = 'evidencia_cancelacion_url'"
        ))
        if r.fetchone():
            print("OK: La columna evidencia_cancelacion_url ya existe en ordenes_compra.")
            return 0
        conn.execute(text("ALTER TABLE ordenes_compra ADD COLUMN evidencia_cancelacion_url VARCHAR(500) NULL"))
        conn.commit()
        print("OK: Columna evidencia_cancelacion_url agregada a ordenes_compra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
