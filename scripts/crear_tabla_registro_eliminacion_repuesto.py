"""Crea la tabla registro_eliminacion_repuesto."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS registro_eliminacion_repuesto (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_repuesto INT NOT NULL,
                id_usuario INT NOT NULL,
                motivo TEXT NOT NULL,
                datos_repuesto TEXT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                CONSTRAINT fk_reg_elim_rep_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE RESTRICT
            )
        """))
        conn.commit()
        print("OK: Tabla registro_eliminacion_repuesto creada/verificada.")

if __name__ == "__main__":
    main()
