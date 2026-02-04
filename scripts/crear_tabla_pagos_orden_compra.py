"""
Crea la tabla pagos_orden_compra para Cuentas por pagar.
Ejecutar: python scripts/crear_tabla_pagos_orden_compra.py
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
                CREATE TABLE IF NOT EXISTS pagos_orden_compra (
                    id_pago INT AUTO_INCREMENT PRIMARY KEY,
                    id_orden_compra INT NOT NULL,
                    id_usuario INT NOT NULL,
                    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    monto DECIMAL(10,2) NOT NULL,
                    metodo ENUM('EFECTIVO','TARJETA','TRANSFERENCIA','CHEQUE') NOT NULL,
                    referencia VARCHAR(100) NULL,
                    observaciones VARCHAR(255) NULL,
                    FOREIGN KEY (id_orden_compra) REFERENCES ordenes_compra(id_orden_compra) ON DELETE CASCADE,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
                    INDEX idx_pago_orden (id_orden_compra)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            print("Tabla 'pagos_orden_compra' creada correctamente.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
