"""
Migración: agregar columna es_consumible a repuestos.
Si True, sugiere MERMA por defecto al cancelar ventas pagadas (aceite, filtros, fluidos, etc.).
"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine


def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE repuestos
                ADD COLUMN es_consumible TINYINT(1) NOT NULL DEFAULT 0
            """))
            conn.commit()
        print("OK: Columna es_consumible agregada a repuestos.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna es_consumible ya existe.")
        else:
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    main()
