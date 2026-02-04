"""Agrega id_ubicacion a repuestos."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'repuestos' AND COLUMN_NAME = 'id_ubicacion'
        """))
        if r.scalar() > 0:
            print("OK: Columna id_ubicacion ya existe en repuestos.")
            return
        conn.execute(text("""
            ALTER TABLE repuestos
            ADD COLUMN id_ubicacion INT NULL,
            ADD CONSTRAINT fk_repuesto_ubicacion FOREIGN KEY (id_ubicacion) REFERENCES ubicaciones(id) ON DELETE SET NULL
        """))
        conn.commit()
        print("OK: Columna id_ubicacion agregada a repuestos.")

if __name__ == "__main__":
    main()
