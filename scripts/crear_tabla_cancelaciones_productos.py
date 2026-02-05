"""
Crear tabla cancelaciones_productos para registrar decisiones por producto al cancelar ventas pagadas.
"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.database import engine


def main():
    sql = """
    CREATE TABLE IF NOT EXISTS cancelaciones_productos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_venta INT NOT NULL,
        id_detalle_venta INT NULL,
        id_repuesto INT NOT NULL,
        cantidad_reutilizable INT NOT NULL DEFAULT 0,
        cantidad_mer INT NOT NULL DEFAULT 0,
        motivo_mer VARCHAR(500) NULL,
        costo_unitario DECIMAL(10,2) NULL,
        costo_total_mer DECIMAL(10,2) NULL,
        id_usuario INT NULL,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_venta) REFERENCES ventas(id_venta) ON DELETE CASCADE,
        FOREIGN KEY (id_detalle_venta) REFERENCES detalle_venta(id_detalle) ON DELETE SET NULL,
        FOREIGN KEY (id_repuesto) REFERENCES repuestos(id_repuesto),
        FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
        INDEX idx_cp_venta (id_venta),
        INDEX idx_cp_fecha (fecha)
    );
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("OK: Tabla cancelaciones_productos creada.")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
