"""Agrega columna id_orden a ventas si no existe."""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE ventas ADD COLUMN id_orden INT NULL"))
            conn.commit()
        print("OK: Columna id_orden agregada a ventas.")
    except Exception as e:
        if "Duplicate column" in str(e) or "1060" in str(e):
            print("OK: La columna id_orden ya existe.")
        else:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()
