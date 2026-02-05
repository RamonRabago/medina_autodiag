"""Agrega columnas id_usuario_autorizacion, id_usuario_inicio, id_usuario_finalizacion, id_usuario_entrega a ordenes_trabajo."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    cols = [
        ("id_usuario_autorizacion", "Usuario que autorizó la orden"),
        ("id_usuario_inicio", "Usuario que inició el trabajo"),
        ("id_usuario_finalizacion", "Usuario que finalizó el trabajo"),
        ("id_usuario_entrega", "Usuario que entregó al cliente"),
    ]
    with engine.connect() as conn:
        for col_name, _ in cols:
            r = conn.execute(text("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_trabajo' AND COLUMN_NAME = :name
            """), {"name": col_name}).fetchall()
            if not r:
                conn.execute(text(f"ALTER TABLE ordenes_trabajo ADD COLUMN {col_name} INT NULL"))
                conn.commit()
                print(f"OK: Columna {col_name} agregada.")
            else:
                print(f"OK: Columna {col_name} ya existe.")

if __name__ == "__main__":
    main()
