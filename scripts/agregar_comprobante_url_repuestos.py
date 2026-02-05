"""Agrega la columna comprobante_url a la tabla repuestos si no existe."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'repuestos' AND COLUMN_NAME = 'comprobante_url'
            """)).fetchall()
            if r:
                print("OK: La columna comprobante_url ya existe en repuestos.")
                return
            conn.execute(text("ALTER TABLE repuestos ADD COLUMN comprobante_url VARCHAR(500) NULL"))
            conn.commit()
        print("OK: Columna comprobante_url agregada a repuestos.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna comprobante_url ya existe en repuestos.")
        else:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()
