"""
Migración: agregar columna cliente_provee a detalles_repuesto_orden.
Indica si la refacción la provee el cliente o el taller.
"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine


def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE detalles_repuesto_orden
                ADD COLUMN cliente_provee TINYINT(1) NOT NULL DEFAULT 0
            """))
            conn.commit()
        print("OK: Columna cliente_provee agregada a detalles_repuesto_orden.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna cliente_provee ya existe.")
        else:
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    main()
