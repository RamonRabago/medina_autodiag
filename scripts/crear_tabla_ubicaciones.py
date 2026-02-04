"""Crea la tabla ubicaciones. Ejecutar: python scripts/crear_tabla_ubicaciones.py"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ubicaciones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_bodega INT NOT NULL,
                codigo VARCHAR(50) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_ubicacion_bodega FOREIGN KEY (id_bodega) REFERENCES bodegas(id) ON DELETE RESTRICT,
                CONSTRAINT uq_bodega_codigo UNIQUE (id_bodega, codigo)
            )
        """))
        conn.commit()
        print("OK: Tabla ubicaciones creada/verificada.")

if __name__ == "__main__":
    main()
