"""Ejecuta la migración motivo_cancelacion en ventas."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE ventas ADD COLUMN motivo_cancelacion TEXT NULL"))
            conn.commit()
        print("OK: Columna motivo_cancelacion agregada a ventas.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna motivo_cancelacion ya existe.")
        else:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()
