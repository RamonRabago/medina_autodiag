"""Verifica si existe la tabla pagos_orden_compra."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text


def main():
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SHOW TABLES LIKE 'pagos_orden_compra'"))
            row = r.fetchone()
            if row:
                print("OK: Tabla pagos_orden_compra EXISTE")
                r2 = conn.execute(text("DESCRIBE pagos_orden_compra"))
                cols = [c[0] for c in r2.fetchall()]
                print("Columnas:", cols)
                return 0
            else:
                print("NO: Tabla pagos_orden_compra NO EXISTE")
                print("Ejecuta: python scripts/crear_tabla_pagos_orden_compra.py")
                return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
