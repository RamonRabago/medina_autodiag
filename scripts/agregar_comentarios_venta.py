"""Agrega columna comentarios a ventas si no existe."""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine

def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE ventas
                ADD COLUMN comentarios TEXT NULL
            """))
            conn.commit()
        print("OK: Columna comentarios agregada a ventas.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna comentarios ya existe.")
        else:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()
