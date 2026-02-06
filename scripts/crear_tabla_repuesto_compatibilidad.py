"""
Crea la tabla repuesto_compatibilidad para compatibilidad repuesto-vehículo.
Ejecutar: python scripts/crear_tabla_repuesto_compatibilidad.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import pymysql


def main():
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "medina_autodiag")

    conn = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        database=db_name,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS repuesto_compatibilidad (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_repuesto INT NOT NULL,
                    marca VARCHAR(80) NOT NULL,
                    modelo VARCHAR(80) NOT NULL,
                    anio_desde INT NULL,
                    anio_hasta INT NULL,
                    motor VARCHAR(50) NULL,
                    FOREIGN KEY (id_repuesto) REFERENCES repuestos(id_repuesto) ON DELETE CASCADE,
                    INDEX idx_repuesto_compat_repuesto (id_repuesto),
                    INDEX idx_repuesto_compat_vehiculo (marca, modelo)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            print("Tabla 'repuesto_compatibilidad' creada.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
