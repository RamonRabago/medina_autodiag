"""
Crea tablas estantes, niveles, filas y agrega columnas a repuestos.
Ejecutar: python scripts/crear_estantes_niveles_filas.py
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        # 1. Tabla niveles
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS niveles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                nombre VARCHAR(50) NOT NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # 2. Tabla filas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS filas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                nombre VARCHAR(50) NOT NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # 3. Tabla estantes
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS estantes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_bodega INT NOT NULL,
                codigo VARCHAR(50) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_estante_bodega FOREIGN KEY (id_bodega) REFERENCES bodegas(id) ON DELETE RESTRICT,
                CONSTRAINT uq_estante_bodega_codigo UNIQUE (id_bodega, codigo)
            )
        """))
        conn.commit()
        print("OK: Tablas estantes, niveles, filas creadas.")

        # 4. Insertar niveles por defecto si no existen
        conn.execute(text("""
            INSERT IGNORE INTO niveles (codigo, nombre) VALUES
            ('A', 'Nivel A'),
            ('B', 'Nivel B'),
            ('C', 'Nivel C'),
            ('D', 'Nivel D'),
            ('E', 'Nivel E')
        """))
        conn.commit()
        print("OK: Niveles por defecto insertados.")

        # 5. Insertar filas por defecto si no existen
        conn.execute(text("""
            INSERT IGNORE INTO filas (codigo, nombre) VALUES
            ('1', 'Fila 1'),
            ('2', 'Fila 2'),
            ('3', 'Fila 3'),
            ('4', 'Fila 4'),
            ('5', 'Fila 5')
        """))
        conn.commit()
        print("OK: Filas por defecto insertadas.")

        # 6. Agregar columnas a repuestos si no existen
        try:
            conn.execute(text("ALTER TABLE repuestos ADD COLUMN id_estante INT NULL"))
            conn.commit()
            print("OK: Columna id_estante agregada a repuestos.")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("INFO: id_estante ya existe en repuestos.")
            else:
                raise

        try:
            conn.execute(text("ALTER TABLE repuestos ADD COLUMN id_nivel INT NULL"))
            conn.commit()
            print("OK: Columna id_nivel agregada a repuestos.")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("INFO: id_nivel ya existe en repuestos.")
            else:
                raise

        try:
            conn.execute(text("ALTER TABLE repuestos ADD COLUMN id_fila INT NULL"))
            conn.commit()
            print("OK: Columna id_fila agregada a repuestos.")
        except Exception as e:
            if "Duplicate column" in str(e):
                print("INFO: id_fila ya existe en repuestos.")
            else:
                raise

        # 7. Foreign keys (omitir si ya existen)
        try:
            conn.execute(text("""
                ALTER TABLE repuestos
                ADD CONSTRAINT fk_repuesto_estante FOREIGN KEY (id_estante) REFERENCES estantes(id) ON DELETE SET NULL
            """))
            conn.commit()
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e).lower():
                pass
            else:
                print(f"INFO: FK estante: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE repuestos
                ADD CONSTRAINT fk_repuesto_nivel FOREIGN KEY (id_nivel) REFERENCES niveles(id) ON DELETE SET NULL
            """))
            conn.commit()
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e).lower():
                pass
            else:
                print(f"INFO: FK nivel: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE repuestos
                ADD CONSTRAINT fk_repuesto_fila FOREIGN KEY (id_fila) REFERENCES filas(id) ON DELETE SET NULL
            """))
            conn.commit()
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e).lower():
                pass
            else:
                print(f"INFO: FK fila: {e}")

    print("Migración completada.")

if __name__ == "__main__":
    main()
