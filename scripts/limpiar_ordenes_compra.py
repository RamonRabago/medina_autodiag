"""
Elimina permanentemente TODAS las órdenes de compra para empezar de cero.
Elimina: pagos, detalles, y órdenes.

Ejecutar: python scripts/limpiar_ordenes_compra.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    from app.database import SessionLocal
    from app.models.orden_compra import OrdenCompra, DetalleOrdenCompra
    from app.models.pago_orden_compra import PagoOrdenCompra

    db = SessionLocal()
    try:
        n_pagos = db.query(PagoOrdenCompra).delete()
        n_detalles = db.query(DetalleOrdenCompra).delete()
        n_ordenes = db.query(OrdenCompra).delete()
        db.commit()
        print(f"Eliminadas: {n_ordenes} órdenes, {n_detalles} detalles, {n_pagos} pagos.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
