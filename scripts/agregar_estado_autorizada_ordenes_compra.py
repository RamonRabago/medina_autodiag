"""Agrega el estado AUTORIZADA al enum estado de ordenes_compra."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text


def main():
    from app.config import settings
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ordenes_compra' AND COLUMN_NAME = 'estado'"
        ))
        row = r.fetchone()
        if row and "AUTORIZADA" not in (row[0] or ""):
            try:
                conn.execute(text(
                    "ALTER TABLE ordenes_compra MODIFY COLUMN estado "
                    "VARCHAR(30) NOT NULL DEFAULT 'BORRADOR'"
                ))
                conn.commit()
                print("OK: estado ahora VARCHAR (incluye AUTORIZADA).")
            except Exception as e:
                print(f"Intentando agregar a ENUM: {e}")
                try:
                    conn.execute(text(
                        "ALTER TABLE ordenes_compra MODIFY COLUMN estado "
                        "ENUM('BORRADOR','AUTORIZADA','ENVIADA','RECIBIDA_PARCIAL','RECIBIDA','CANCELADA') "
                        "NOT NULL DEFAULT 'BORRADOR'"
                    ))
                    conn.commit()
                    print("OK: AUTORIZADA agregado al ENUM estado.")
                except Exception as e2:
                    print(f"Error: {e2}")
        else:
            print("OK: estado ya incluye AUTORIZADA o es VARCHAR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
