"""
Agrega campos id_proveedor, imagen_comprobante_url, fecha_adquisicion a movimientos_inventario.
Ejecutar: python scripts/agregar_campos_entrada_inventario.py
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        cols = [r[0] for r in conn.execute(text("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'movimientos_inventario'
        """)).fetchall()]

        if 'id_proveedor' not in cols:
            conn.execute(text("ALTER TABLE movimientos_inventario ADD COLUMN id_proveedor INT NULL"))
            conn.commit()
            conn.execute(text("""
                ALTER TABLE movimientos_inventario 
                ADD CONSTRAINT fk_movimiento_proveedor FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor) ON DELETE SET NULL
            """))
            conn.commit()
            print("OK: id_proveedor agregado.")

        if 'imagen_comprobante_url' not in cols:
            conn.execute(text("ALTER TABLE movimientos_inventario ADD COLUMN imagen_comprobante_url VARCHAR(500) NULL"))
            conn.commit()
            print("OK: imagen_comprobante_url agregado.")

        if 'fecha_adquisicion' not in cols:
            conn.execute(text("ALTER TABLE movimientos_inventario ADD COLUMN fecha_adquisicion DATE NULL"))
            conn.commit()
            print("OK: fecha_adquisicion agregado.")

    print("Migración completada.")

if __name__ == "__main__":
    main()
