"""Crea la tabla registro_eliminacion_vehiculo si no existe."""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    sql = """
    CREATE TABLE IF NOT EXISTS registro_eliminacion_vehiculo (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_vehiculo INT NOT NULL,
        id_usuario INT NOT NULL,
        motivo TEXT NOT NULL,
        datos_vehiculo TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
    );
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("OK: Tabla registro_eliminacion_vehiculo creada/verificada.")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
