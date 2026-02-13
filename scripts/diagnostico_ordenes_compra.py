"""
Diagnóstico del esquema ordenes_compra y detalles_orden_compra.
Muestra columnas actuales vs esperadas por el modelo.
Ejecutar: python scripts/diagnostico_ordenes_compra.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Columnas que el modelo OrdenCompra espera (app/models/orden_compra.py)
ORDENES_ESPERADAS = {
    "id_orden_compra", "numero", "id_proveedor", "id_usuario",
    "fecha", "fecha_envio", "fecha_recepcion", "estado",
    "total_estimado", "observaciones", "referencia_proveedor", "comprobante_url",
    "motivo_cancelacion", "fecha_cancelacion", "id_usuario_cancelacion",
    "creado_en", "actualizado_en",
}

# Columnas que el modelo DetalleOrdenCompra espera
DETALLES_ESPERADAS = {
    "id", "id_orden_compra", "id_repuesto", "codigo_nuevo", "nombre_nuevo",
    "cantidad_solicitada", "cantidad_recibida", "precio_unitario_estimado", "precio_unitario_real",
}


def main():
    from app.config import settings
    from sqlalchemy import create_engine, text

    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("\n=== Diagnóstico ordenes_compra ===\n")

        for table, esperadas in [("ordenes_compra", ORDENES_ESPERADAS), ("detalles_orden_compra", DETALLES_ESPERADAS)]:
            r = conn.execute(text(
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_TYPE "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                "ORDER BY ORDINAL_POSITION"
            ), {"t": table})
            actuales = {row[0]: {"type": row[1], "nullable": row[2], "default": row[3], "col_type": row[4]} for row in r}

            print(f"--- {table} ---")
            print(f"Columnas en BD: {list(actuales.keys())}")
            print(f"Columnas esperadas por modelo: {sorted(esperadas)}")

            faltan = esperadas - set(actuales.keys())
            sobran = set(actuales.keys()) - esperadas
            not_null_problematicas = [
                c for c in sobran
                if actuales[c]["nullable"] == "NO" and (actuales[c].get("default") is None or str(actuales[c].get("default", "")).upper() == "NONE")
            ]

            if faltan:
                print(f"\n  [FALTAN] Columnas a agregar: {faltan}")
            if sobran:
                print(f"\n  [SOBRAN] Columnas legacy (no en modelo): {sobran}")
                for c in sorted(sobran):
                    n = "NULL" if actuales[c]["nullable"] == "YES" else "NOT NULL"
                    print(f"       - {c}: {n}")
            if not_null_problematicas:
                print(f"\n  [!] COLUMNAS QUE CAUSAN ERROR EN INSERT (NOT NULL sin default): {not_null_problematicas}")
                print("     Estas columnas deben hacerse NULLABLE para que el INSERT funcione.")
            print()

    print("Para corregir, ejecute: alembic upgrade head\n")


if __name__ == "__main__":
    main()
