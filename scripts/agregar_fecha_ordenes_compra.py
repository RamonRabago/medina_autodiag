"""Agrega la columna fecha y otras columnas faltantes en ordenes_compra si no existen."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text


def col_exists(conn, col):
    r = conn.execute(text(
        "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_compra' AND COLUMN_NAME = :c"
    ), {"c": col})
    return r.fetchone() is not None


def main():
    from app.config import settings
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        cambios = False

        if not col_exists(conn, "fecha"):
            conn.execute(text(
                "ALTER TABLE ordenes_compra ADD COLUMN fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER id_usuario"
            ))
            conn.commit()
            print("OK: Columna fecha agregada.")
            cambios = True

        if not col_exists(conn, "motivo_cancelacion"):
            conn.execute(text(
                "ALTER TABLE ordenes_compra ADD COLUMN motivo_cancelacion TEXT NULL"
            ))
            conn.commit()
            print("OK: Columna motivo_cancelacion agregada.")
            cambios = True

        if not col_exists(conn, "fecha_cancelacion"):
            conn.execute(text(
                "ALTER TABLE ordenes_compra ADD COLUMN fecha_cancelacion DATETIME NULL"
            ))
            conn.commit()
            print("OK: Columna fecha_cancelacion agregada.")
            cambios = True

        if not col_exists(conn, "id_usuario_cancelacion"):
            try:
                conn.execute(text(
                    "ALTER TABLE ordenes_compra ADD COLUMN id_usuario_cancelacion INT NULL"
                ))
                conn.commit()
                print("OK: Columna id_usuario_cancelacion agregada.")
                cambios = True
            except Exception as e:
                if "Duplicate column" in str(e):
                    print("OK: id_usuario_cancelacion ya existe.")
                else:
                    raise

        if not cambios:
            print("OK: Todas las columnas ya existen en ordenes_compra.")

    print("Migración completada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
