"""
Migración: crea tabla gastos_operativos.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text


def main():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gastos_operativos (
                id_gasto INT AUTO_INCREMENT PRIMARY KEY,
                fecha DATE NOT NULL,
                concepto VARCHAR(200) NOT NULL,
                monto DECIMAL(10,2) NOT NULL,
                categoria ENUM('RENTA','SERVICIOS','MATERIAL','NOMINA','OTROS') NOT NULL DEFAULT 'OTROS',
                id_turno INT NULL,
                id_usuario INT NOT NULL,
                observaciones TEXT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_gasto_turno FOREIGN KEY (id_turno) REFERENCES caja_turnos(id_turno) ON DELETE SET NULL,
                CONSTRAINT fk_gasto_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE RESTRICT
            )
        """))
        conn.commit()
    print("OK: Tabla gastos_operativos creada o ya existía.")


if __name__ == "__main__":
    main()
