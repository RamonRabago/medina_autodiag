"""Agrega la columna rfc a la tabla clientes si no existe."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE clientes ADD COLUMN rfc VARCHAR(13) NULL"))
            conn.commit()
        print("OK: Columna rfc agregada a clientes.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna rfc ya existe en clientes.")
        else:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()
