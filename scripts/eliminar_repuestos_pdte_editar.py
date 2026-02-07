"""
Elimina (soft delete) todos los repuestos cuyo código es 'PDTE EDITAR' o 'PDTE EDITAR-N'.

Estos se crean cuando se recibe mercancía sin código en órdenes de compra.
Marca como eliminados para que no aparezcan en inventario; el historial se conserva.

Ejecutar: python scripts/eliminar_repuestos_pdte_editar.py
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.database import SessionLocal
from app.models.repuesto import Repuesto


def main():
    db = SessionLocal()
    try:
        # Repuestos con codigo = 'PDTE EDITAR' o codigo LIKE 'PDTE EDITAR-%'
        repuestos = db.query(Repuesto).filter(
            Repuesto.eliminado == False,
            (Repuesto.codigo == "PDTE EDITAR") | (Repuesto.codigo.like("PDTE EDITAR-%")),
        ).all()

        if not repuestos:
            print("No hay repuestos con código 'PDTE EDITAR' en inventario.")
            return 0

        for r in repuestos:
            codigo_original = r.codigo
            r.codigo = f"{r.codigo}_ELIM_{r.id_repuesto}"
            r.eliminado = True
            r.activo = False
            r.fecha_eliminacion = datetime.datetime.utcnow()
            r.motivo_eliminacion = "Eliminación masiva: repuestos con código PDTE EDITAR"
            print(f"  Eliminado: {codigo_original} (id={r.id_repuesto}) - {r.nombre}")

        db.commit()
        print(f"\nOK: Se eliminaron {len(repuestos)} repuesto(s) con código PDTE EDITAR.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
