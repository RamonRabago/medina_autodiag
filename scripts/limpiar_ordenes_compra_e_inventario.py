"""
Elimina todas las órdenes de compra Y revierte el inventario que se generó al recibirlas.

1. Encuentra movimientos de inventario con referencia OC-{id} (de órdenes de compra)
2. Revierte el stock: resta la cantidad de cada entrada del repuesto
3. Elimina esos movimientos
4. Elimina pagos, detalles y órdenes de compra
5. Elimina repuestos con código PDTE EDITAR (creados al recibir sin código)

Ejecutar: python scripts/limpiar_ordenes_compra_e_inventario.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from app.config import settings


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # 1. Obtener movimientos de OC
        r = conn.execute(text(
            "SELECT id_movimiento, id_repuesto, cantidad, tipo_movimiento, referencia "
            "FROM movimientos_inventario WHERE referencia LIKE 'OC-%'"
        ))
        movs = r.fetchall()

        if movs:
            for m in movs:
                mid, rid, cant, tipo, ref = m
                if tipo == "ENTRADA" and cant > 0:
                    conn.execute(
                        text(
                            "UPDATE repuestos SET stock_actual = GREATEST(0, stock_actual - :c) WHERE id_repuesto = :rid"
                        ),
                        {"c": cant, "rid": rid},
                    )
                    print(f"  Revertido: repuesto {rid} -{cant} (mov {mid}, {ref})")
            conn.execute(text("DELETE FROM movimientos_inventario WHERE referencia LIKE 'OC-%'"))
            print(f"  Eliminados {len(movs)} movimiento(s) de inventario (OC)")

        # 2. Eliminar órdenes de compra
        r = conn.execute(text("SELECT COUNT(*) FROM ordenes_compra"))
        total_oc = r.scalar()
        if total_oc > 0:
            conn.execute(text("DELETE FROM pagos_orden_compra"))
            conn.execute(text("DELETE FROM detalles_orden_compra"))
            conn.execute(text("DELETE FROM ordenes_compra"))
            print(f"  Eliminadas {total_oc} orden(es) de compra (y detalles/pagos)")

        conn.commit()

        # 3. Eliminar repuestos PDTE EDITAR (soft delete)
        r = conn.execute(
            text(
                "SELECT id_repuesto, codigo, nombre FROM repuestos "
                "WHERE eliminado = 0 AND (codigo = 'PDTE EDITAR' OR codigo LIKE 'PDTE EDITAR-%')"
            )
        )
        pdte = r.fetchall()
        if pdte:
            import datetime
            for rid, cod, nom in pdte:
                nuevo_cod = f"{cod}_ELIM_{rid}"
                conn.execute(
                    text(
                        "UPDATE repuestos SET codigo = :nc, eliminado = 1, activo = 0, "
                        "fecha_eliminacion = :fe, motivo_eliminacion = 'Limpieza: borrado con órdenes de compra' "
                        "WHERE id_repuesto = :rid"
                    ),
                    {"nc": nuevo_cod, "fe": datetime.datetime.utcnow(), "rid": rid},
                )
                print(f"  Eliminado repuesto: {cod} (id={rid}) - {nom}")
            conn.commit()
            print(f"  Eliminados {len(pdte)} repuesto(s) PDTE EDITAR")

    print("\nOK: Órdenes de compra e inventario generado por ellas han sido limpiados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
