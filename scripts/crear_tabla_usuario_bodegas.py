"""Crea la tabla usuario_bodegas. Ejecutar: python scripts/crear_tabla_usuario_bodegas.py"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuario_bodegas (
                id_usuario INT NOT NULL,
                id_bodega INT NOT NULL,
                PRIMARY KEY (id_usuario, id_bodega),
                FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                FOREIGN KEY (id_bodega) REFERENCES bodegas(id) ON DELETE CASCADE
            )
        """))
        conn.commit()
        print("OK: Tabla usuario_bodegas creada/verificada.")

if __name__ == "__main__":
    main()
