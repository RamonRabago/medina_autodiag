"""Hace nullable las columnas legacy de ordenes_compra que causan error en INSERT."""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text

LEGACY = [
    ("numero_orden", "VARCHAR(50)"),
    ("fecha_orden", "DATETIME"),
    ("fecha_esperada", "DATETIME"),
    ("subtotal", "DECIMAL(12,2)"),
    ("impuesto", "DECIMAL(12,2)"),
    ("total", "DECIMAL(12,2)"),
]

def main():
    from app.config import settings
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        for col, tpo in LEGACY:
            try:
                conn.execute(text(f"ALTER TABLE ordenes_compra MODIFY COLUMN `{col}` {tpo} NULL"))
                conn.commit()
                print(f"OK: {col} -> nullable")
            except Exception as e:
                if "Unknown column" in str(e):
                    print(f"Skip: {col} no existe")
                else:
                    print(f"Error {col}: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
