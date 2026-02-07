"""Elimina todas las órdenes de compra para empezar a validar de cero."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from app.config import settings


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM ordenes_compra"))
        total = r.scalar()
        if total == 0:
            print("No hay órdenes de compra.")
            return 0
        conn.execute(text("DELETE FROM pagos_orden_compra"))
        conn.execute(text("DELETE FROM detalles_orden_compra"))
        conn.execute(text("DELETE FROM ordenes_compra"))
        conn.commit()
        print(f"OK: Eliminadas {total} órdenes de compra (y sus detalles/pagos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
