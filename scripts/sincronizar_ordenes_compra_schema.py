"""
Sincroniza el esquema de ordenes_compra y detalles_orden_compra con el modelo.
- Agrega columnas faltantes
- Hace NULLABLE cualquier columna legacy (no en el modelo) para evitar errores en INSERT
Ejecutar: python scripts/sincronizar_ordenes_compra_schema.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text

# Columnas que el modelo OrdenCompra usa (app/models/orden_compra.py)
ORDENES_COLUMNS_MODELO = {
    "id_orden_compra", "numero", "id_proveedor", "id_usuario",
    "fecha", "fecha_envio", "fecha_recepcion", "fecha_estimada_entrega", "estado",
    "total_estimado", "observaciones", "referencia_proveedor", "comprobante_url",
    "motivo_cancelacion", "fecha_cancelacion", "id_usuario_cancelacion",
    "creado_en", "actualizado_en",
}

# Definiciones para agregar columnas faltantes
ORDENES_ADD = [
    ("numero", "VARCHAR(50) NULL"),
    ("fecha", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("fecha_envio", "DATETIME NULL"),
    ("fecha_recepcion", "DATETIME NULL"),
    ("fecha_estimada_entrega", "DATETIME NULL"),
        ("estado", "VARCHAR(30) NOT NULL DEFAULT 'BORRADOR'"),  # BORRADOR, AUTORIZADA, ENVIADA, RECIBIDA_PARCIAL, RECIBIDA, CANCELADA
    ("total_estimado", "DECIMAL(12,2) DEFAULT 0"),
    ("observaciones", "TEXT NULL"),
    ("referencia_proveedor", "VARCHAR(100) NULL"),
    ("comprobante_url", "VARCHAR(500) NULL"),
    ("motivo_cancelacion", "TEXT NULL"),
    ("fecha_cancelacion", "DATETIME NULL"),
    ("id_usuario_cancelacion", "INT NULL"),
    ("creado_en", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ("actualizado_en", "DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
]

DETALLES_ADD = [
    ("codigo_nuevo", "VARCHAR(100) NULL"),
    ("nombre_nuevo", "VARCHAR(200) NULL"),
]

# Tipos MySQL para columnas legacy (para MODIFY - obtener de COLUMN_TYPE)
LEGACY_TYPES = {
    "numero_orden": "VARCHAR(50)",
    "fecha_orden": "DATETIME",
    "fecha_esperada": "DATETIME",
    "id_orden": "INT",
    "id_proveedor_orden": "INT",
    "subtotal": "DECIMAL(12,2)",
    "impuesto": "DECIMAL(12,2)",
    "total": "DECIMAL(12,2)",
}


def col_exists(conn, table, col):
    r = conn.execute(text(
        "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": table, "c": col})
    return r.fetchone() is not None


def get_columns(conn, table):
    r = conn.execute(text(
        "SELECT COLUMN_NAME, IS_NULLABLE, COLUMN_TYPE "
        "FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": table})
    return {row[0]: {"nullable": row[1], "col_type": row[2]} for row in r}


def add_col(conn, table, col, definition):
    if not col_exists(conn, table, col):
        try:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {definition}"))
            conn.commit()
            print(f"  + {table}.{col} agregada.")
            return True
        except Exception as e:
            if "Duplicate column" in str(e):
                pass
            else:
                raise
    return False


def make_nullable(conn, table, col, mysql_type):
    """Hace una columna nullable. mysql_type ej: VARCHAR(50), DATETIME, INT."""
    try:
        sql = f"ALTER TABLE {table} MODIFY COLUMN `{col}` {mysql_type} NULL"
        conn.execute(text(sql))
        conn.commit()
        print(f"  ~ {table}.{col} ahora nullable (legacy)")
        return True
    except Exception as e:
        err_msg = str(e).encode("ascii", "replace").decode("ascii")
        print(f"  ! {col}: {err_msg}")
        return False


def main():
    from app.config import settings
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        print("\n=== Sincronizando ordenes_compra ===\n")

        # 1. Agregar columnas faltantes
        for col, defn in ORDENES_ADD:
            add_col(conn, "ordenes_compra", col, defn)

        # 2. Detectar y hacer nullable columnas legacy (no en modelo)
        actuales = get_columns(conn, "ordenes_compra")
        legacy = set(actuales.keys()) - ORDENES_COLUMNS_MODELO
        for col in sorted(legacy):
            if actuales[col]["nullable"] == "NO":
                tipo = LEGACY_TYPES.get(col) or actuales[col].get("col_type") or "VARCHAR(100)"
                make_nullable(conn, "ordenes_compra", col, tipo)

        # 3. Poblar numero si hay NULLs
        if col_exists(conn, "ordenes_compra", "numero"):
            try:
                conn.execute(text(
                    "UPDATE ordenes_compra SET numero = CONCAT('OC-LEGACY-', id_orden_compra) WHERE numero IS NULL"
                ))
                conn.commit()
                print("  ~ numero: filas NULL actualizadas.")
            except Exception as e:
                print(f"  ! numero update: {e}")

        # 4. detalles_orden_compra
        print("\n=== Sincronizando detalles_orden_compra ===\n")
        for col, defn in DETALLES_ADD:
            add_col(conn, "detalles_orden_compra", col, defn)

        if col_exists(conn, "detalles_orden_compra", "id_repuesto"):
            r = conn.execute(text(
                "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'detalles_orden_compra' AND COLUMN_NAME = 'id_repuesto'"
            ))
            row = r.fetchone()
            if row and row[0] != "YES":
                try:
                    conn.execute(text(
                        "ALTER TABLE detalles_orden_compra MODIFY COLUMN id_repuesto INT NULL"
                    ))
                    conn.commit()
                    print("  ~ id_repuesto ahora nullable (repuesto nuevo).")
                except Exception as e:
                    print(f"  ! id_repuesto: {e}")

    print("\nSincronización completada. Ejecute diagnostico_ordenes_compra.py para verificar.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
