"""
Migración: agregar columna cliente_proporciono_refacciones a ordenes_trabajo.
Si True, al finalizar la orden NO se descuenta ningún repuesto del inventario.
"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine


def main():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE ordenes_trabajo
                ADD COLUMN cliente_proporciono_refacciones TINYINT(1) NOT NULL DEFAULT 0
            """))
            conn.commit()
        print("OK: Columna cliente_proporciono_refacciones agregada a ordenes_trabajo.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "1060" in str(e):
            print("OK: La columna cliente_proporciono_refacciones ya existe.")
        else:
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    main()
