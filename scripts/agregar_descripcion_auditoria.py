"""Agrega las columnas descripcion y fecha a la tabla auditoria (si faltan).
Ejecutar: python scripts/agregar_descripcion_auditoria.py
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def add_col(conn, col, defn, name):
    try:
        conn.execute(text(f"ALTER TABLE auditoria ADD COLUMN {col} {defn}"))
        conn.commit()
        print(f"OK: {name} agregada a auditoria")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print(f"OK: {name} ya existe en auditoria")
        else:
            conn.rollback()
            raise

def main():
    with engine.connect() as conn:
        add_col(conn, "descripcion", "TEXT NULL", "descripcion")
        add_col(conn, "fecha", "DATETIME NULL DEFAULT CURRENT_TIMESTAMP", "fecha")

    print("\nMigración completada.")

if __name__ == "__main__":
    main()
