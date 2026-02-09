"""Crea la tabla citas si no existe."""
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import engine
from sqlalchemy import text

SQL = """
CREATE TABLE IF NOT EXISTS citas (
    id_cita INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_vehiculo INT NULL,
    fecha_hora DATETIME NOT NULL,
    tipo ENUM('REVISION','MANTENIMIENTO','REPARACION','DIAGNOSTICO','OTRO') NOT NULL DEFAULT 'REVISION',
    estado ENUM('PENDIENTE','CONFIRMADA','REALIZADA','CANCELADA','NO_ASISTIO') NOT NULL DEFAULT 'PENDIENTE',
    motivo VARCHAR(300) NULL,
    notas TEXT NULL,
    id_orden INT NULL,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_citas_cliente (id_cliente),
    INDEX idx_citas_vehiculo (id_vehiculo),
    INDEX idx_citas_fecha (fecha_hora),
    INDEX idx_citas_estado (estado),
    INDEX idx_citas_orden (id_orden),
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id_vehiculo) ON DELETE SET NULL,
    FOREIGN KEY (id_orden) REFERENCES ordenes_trabajo(id) ON DELETE SET NULL
);
"""

def main():
    with engine.connect() as conn:
        conn.execute(text(SQL))
        conn.commit()
    print("Tabla citas creada o ya existía.")

if __name__ == "__main__":
    main()
