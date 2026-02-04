"""Agrega campos de soft delete a repuestos. Ejecutar: python scripts/agregar_campos_eliminado_repuestos.py"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        # Comprobar si ya existen las columnas
        r = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'repuestos' AND COLUMN_NAME = 'eliminado'
        """))
        if r.scalar() > 0:
            print("OK: Columnas de eliminado ya existen en repuestos.")
            return
        conn.execute(text("""
            ALTER TABLE repuestos
            ADD COLUMN eliminado TINYINT(1) NOT NULL DEFAULT 0,
            ADD COLUMN fecha_eliminacion TIMESTAMP NULL,
            ADD COLUMN motivo_eliminacion TEXT NULL,
            ADD COLUMN id_usuario_eliminacion INT NULL
        """))
        conn.execute(text("""
            ALTER TABLE repuestos
            ADD CONSTRAINT fk_repuesto_usuario_eliminacion
            FOREIGN KEY (id_usuario_eliminacion) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
        """))
        conn.commit()
        print("OK: Columnas eliminado, fecha_eliminacion, motivo_eliminacion, id_usuario_eliminacion agregadas a repuestos.")

if __name__ == "__main__":
    main()
