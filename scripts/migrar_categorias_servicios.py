"""
Migración: Crear categorias_servicios y cambiar Servicio de ENUM a FK.
Ejecutar: python scripts/migrar_categorias_servicios.py
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

MAPEO_ENUM_A_ID = {
    "MANTENIMIENTO": 1,
    "REPARACION": 2,
    "DIAGNOSTICO": 3,
    "ELECTRICIDAD": 4,
    "SUSPENSION": 5,
    "FRENOS": 6,
    "MOTOR": 7,
    "TRANSMISION": 8,
    "AIRE_ACONDICIONADO": 9,
    "CARROCERIA": 10,
    "OTROS": 11,
}

def main():
    with engine.connect() as conn:
        # 1. Crear tabla categorias_servicios si no existe
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS categorias_servicios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE,
                descripcion TEXT NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("1. Tabla categorias_servicios creada/verificada.")

        # 2. Insertar categorías por defecto si la tabla está vacía
        r = conn.execute(text("SELECT COUNT(*) FROM categorias_servicios")).scalar()
        if r == 0:
            conn.execute(text("""
                INSERT INTO categorias_servicios (id, nombre, descripcion, activo) VALUES
                (1, 'Mantenimiento', NULL, 1),
                (2, 'Reparación', NULL, 1),
                (3, 'Diagnóstico', NULL, 1),
                (4, 'Electricidad', NULL, 1),
                (5, 'Suspensión', NULL, 1),
                (6, 'Frenos', NULL, 1),
                (7, 'Motor', NULL, 1),
                (8, 'Transmisión', NULL, 1),
                (9, 'Aire Acondicionado', NULL, 1),
                (10, 'Carrocería', NULL, 1),
                (11, 'Otros', NULL, 1)
            """))
            conn.commit()
            print("2. Categorías por defecto insertadas.")
        else:
            print("2. Categorías ya existen.")

        # 3. Verificar si servicios ya tiene id_categoria (migración ya aplicada)
        try:
            r = conn.execute(text("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'servicios' AND COLUMN_NAME = 'id_categoria'
            """)).fetchall()
            tiene_id_categoria = len(r) > 0
        except Exception:
            tiene_id_categoria = False

        if not tiene_id_categoria:
            # 4. Agregar columna id_categoria
            conn.execute(text("ALTER TABLE servicios ADD COLUMN id_categoria INT NULL"))
            conn.commit()
            print("4. Columna id_categoria agregada a servicios.")

            # 5. Migrar datos según categoria (enum) a id_categoria
            for enum_val, cat_id in MAPEO_ENUM_A_ID.items():
                conn.execute(
                    text("UPDATE servicios SET id_categoria = :cid WHERE categoria = :eval"),
                    {"cid": cat_id, "eval": enum_val}
                )
            conn.commit()
            print("5. Datos migrados de categoria a id_categoria.")

            # 6. Asignar Otros a los que quedaron NULL
            conn.execute(text("UPDATE servicios SET id_categoria = 11 WHERE id_categoria IS NULL"))
            conn.commit()

            # 7. Hacer id_categoria NOT NULL
            conn.execute(text("ALTER TABLE servicios MODIFY id_categoria INT NOT NULL"))
            conn.commit()

            # 8. Agregar FK
            conn.execute(text("""
                ALTER TABLE servicios ADD CONSTRAINT fk_servicio_categoria
                FOREIGN KEY (id_categoria) REFERENCES categorias_servicios(id)
            """))
            conn.commit()
            print("8. Foreign key agregada.")

            # 9. Eliminar columna categoria (enum)
            conn.execute(text("ALTER TABLE servicios DROP COLUMN categoria"))
            conn.commit()
            print("9. Columna categoria (enum) eliminada.")

            print("Migración completada correctamente.")
        else:
            print("Migración ya aplicada (id_categoria existe en servicios).")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        raise
