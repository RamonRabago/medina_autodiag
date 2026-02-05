"""Agrega columnas de auditoría de cancelaciones a ordenes_trabajo y ordenes_compra.
Ejecutar: python scripts/agregar_auditoria_cancelaciones.py
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        # ordenes_trabajo
        try:
            conn.execute(text("ALTER TABLE ordenes_trabajo ADD COLUMN motivo_cancelacion TEXT NULL"))
            conn.commit()
            print("OK: motivo_cancelacion agregado a ordenes_trabajo")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("OK: motivo_cancelacion ya existe en ordenes_trabajo")
            else:
                conn.rollback()
                raise
        try:
            conn.execute(text("ALTER TABLE ordenes_trabajo ADD COLUMN fecha_cancelacion DATETIME NULL"))
            conn.commit()
            print("OK: fecha_cancelacion agregado a ordenes_trabajo")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("OK: fecha_cancelacion ya existe en ordenes_trabajo")
            else:
                conn.rollback()
                raise
        try:
            conn.execute(text("ALTER TABLE ordenes_trabajo ADD COLUMN id_usuario_cancelacion INT NULL"))
            conn.commit()
            print("OK: id_usuario_cancelacion agregado a ordenes_trabajo")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("OK: id_usuario_cancelacion ya existe en ordenes_trabajo")
            else:
                conn.rollback()
                raise

        # ordenes_compra
        try:
            conn.execute(text("ALTER TABLE ordenes_compra ADD COLUMN motivo_cancelacion TEXT NULL"))
            conn.commit()
            print("OK: motivo_cancelacion agregado a ordenes_compra")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("OK: motivo_cancelacion ya existe en ordenes_compra")
            else:
                conn.rollback()
                raise
        try:
            conn.execute(text("ALTER TABLE ordenes_compra ADD COLUMN fecha_cancelacion DATETIME NULL"))
            conn.commit()
            print("OK: fecha_cancelacion agregado a ordenes_compra")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("OK: fecha_cancelacion ya existe en ordenes_compra")
            else:
                conn.rollback()
                raise
        try:
            conn.execute(text("ALTER TABLE ordenes_compra ADD COLUMN id_usuario_cancelacion INT NULL"))
            conn.commit()
            print("OK: id_usuario_cancelacion agregado a ordenes_compra")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("OK: id_usuario_cancelacion ya existe en ordenes_compra")
            else:
                conn.rollback()
                raise

        # ventas - agregar fecha e id_usuario si no existen (para consistencia)
        for col, defn in [
            ("fecha_cancelacion", "DATETIME NULL"),
            ("id_usuario_cancelacion", "INT NULL"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE ventas ADD COLUMN {col} {defn}"))
                conn.commit()
                print(f"OK: {col} agregado a ventas")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                    print(f"OK: {col} ya existe en ventas")
                else:
                    conn.rollback()
                    raise

    print("\nAuditoría de cancelaciones: columnas verificadas/creadas.")

if __name__ == "__main__":
    main()
