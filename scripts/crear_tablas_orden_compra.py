"""
Crea tablas ordenes_compra y detalles_orden_compra.
Ejecutar: python scripts/crear_tablas_orden_compra.py
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
                CREATE TABLE IF NOT EXISTS ordenes_compra (
                    id_orden_compra INT AUTO_INCREMENT PRIMARY KEY,
                    numero VARCHAR(50) NOT NULL UNIQUE,
                    id_proveedor INT NOT NULL,
                    id_usuario INT NOT NULL,
                    fecha DATETIME NOT NULL,
                    fecha_envio DATETIME NULL,
                    fecha_recepcion DATETIME NULL,
                    estado ENUM('BORRADOR','ENVIADA','RECIBIDA_PARCIAL','RECIBIDA','CANCELADA') NOT NULL DEFAULT 'BORRADOR',
                    total_estimado DECIMAL(12,2) DEFAULT 0,
                    observaciones TEXT NULL,
                    referencia_proveedor VARCHAR(100) NULL,
                    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor),
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
                    INDEX idx_orden_compra_estado (estado),
                    INDEX idx_orden_compra_fecha (fecha)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS detalles_orden_compra (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_orden_compra INT NOT NULL,
                    id_repuesto INT NOT NULL,
                    cantidad_solicitada INT NOT NULL,
                    cantidad_recibida INT NOT NULL DEFAULT 0,
                    precio_unitario_estimado DECIMAL(10,2) NOT NULL,
                    precio_unitario_real DECIMAL(10,2) NULL,
                    FOREIGN KEY (id_orden_compra) REFERENCES ordenes_compra(id_orden_compra) ON DELETE CASCADE,
                    FOREIGN KEY (id_repuesto) REFERENCES repuestos(id_repuesto)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            print("Tablas 'ordenes_compra' y 'detalles_orden_compra' creadas.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
