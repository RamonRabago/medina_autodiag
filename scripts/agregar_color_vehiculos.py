"""Agrega la columna color a la tabla vehiculos si no existe. Copia motor a color para datos legacy."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE vehiculos ADD COLUMN color VARCHAR(30) NULL"))
            conn.commit()
        print("OK: Columna color agregada a vehiculos.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna color ya existe en vehiculos.")
        else:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()
