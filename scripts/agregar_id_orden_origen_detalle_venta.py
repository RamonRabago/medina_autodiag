"""Agregar columna id_orden_origen a detalle_venta para marcar ítems que vinieron de una orden."""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE detalle_venta ADD COLUMN id_orden_origen INT NULL"))
            conn.commit()
        print("OK: Columna id_orden_origen agregada a detalle_venta.")
    except Exception as e:
        err = str(e).lower()
        if "duplicate column" in err or "already exists" in err:
            print("OK: La columna id_orden_origen ya existe.")
        else:
            raise

if __name__ == "__main__":
    main()
