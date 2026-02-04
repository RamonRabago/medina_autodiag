"""
Migra la tabla estantes de id_bodega a id_ubicacion.
Ejecutar: python scripts/migrar_estantes_a_ubicacion.py

Si ya existen estantes con id_bodega, crea ubicaciones por defecto por bodega
y asigna cada estante a la primera ubicación de su bodega.
"""
import sys
sys.path.insert(0, ".")

from sqlalchemy import text
from app.database import engine

def main():
    with engine.connect() as conn:
        # Verificar si id_bodega existe (necesitamos migrar)
        r_col = conn.execute(text("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'estantes'
        """))
        columns = [row[0] for row in r_col.fetchall()]
        tiene_id_ubicacion = 'id_ubicacion' in columns
        tiene_id_bodega = 'id_bodega' in columns

        if not tiene_id_bodega and tiene_id_ubicacion:
            print("INFO: La migración ya fue aplicada completamente.")
            return

        if not tiene_id_ubicacion:
            conn.execute(text("ALTER TABLE estantes ADD COLUMN id_ubicacion INT NULL AFTER id_bodega"))
            conn.commit()
            print("OK: Columna id_ubicacion agregada.")

        # 2. Para cada bodega que tenga estantes, obtener o crear una ubicación por defecto
        # y asignar los estantes a esa ubicación
        r = conn.execute(text("""
            SELECT DISTINCT id_bodega FROM estantes WHERE id_bodega IS NOT NULL
        """))
        bodegas_con_estantes = [row[0] for row in r.fetchall()]

        for id_bodega in bodegas_con_estantes:
            # Buscar primera ubicación de esta bodega
            r2 = conn.execute(text("""
                SELECT id FROM ubicaciones WHERE id_bodega = :b AND activo = 1 LIMIT 1
            """), {"b": id_bodega})
            row = r2.fetchone()
            if row:
                id_ubicacion = row[0]
            else:
                # Crear ubicación por defecto para la bodega
                conn.execute(text("""
                    INSERT INTO ubicaciones (id_bodega, codigo, nombre, activo)
                    VALUES (:b, 'ZONA-01', 'Zona principal', 1)
                """), {"b": id_bodega})
                conn.commit()
                r3 = conn.execute(text("SELECT id FROM ubicaciones WHERE id_bodega = :b ORDER BY id DESC LIMIT 1"), {"b": id_bodega})
                id_ubicacion = r3.scalar()

            if id_ubicacion:
                conn.execute(text("""
                    UPDATE estantes SET id_ubicacion = :u WHERE id_bodega = :b
                """), {"u": id_ubicacion, "b": id_bodega})
                conn.commit()
                print(f"OK: Estantes de bodega {id_bodega} asignados a ubicación {id_ubicacion}.")

        # 3. Para estantes sin bodega asignada, dejar id_ubicacion NULL (o asignar a primera ubicación disponible)
        conn.execute(text("""
            UPDATE estantes e
            SET e.id_ubicacion = (SELECT id FROM ubicaciones WHERE activo = 1 ORDER BY id LIMIT 1)
            WHERE e.id_ubicacion IS NULL AND EXISTS (SELECT 1 FROM ubicaciones LIMIT 1)
        """))
        conn.commit()

        # 4. Hacer id_ubicacion NOT NULL (solo si todos tienen valor y aún hay id_bodega)
        if tiene_id_bodega:
            conn.execute(text("ALTER TABLE estantes MODIFY COLUMN id_ubicacion INT NOT NULL"))
            conn.commit()

        # 5. Eliminar FK y constraint, luego columna id_bodega (solo si existe)
        if not tiene_id_bodega:
            print("INFO: id_bodega ya fue eliminada.")
        else:
            # Buscar nombre de la FK
            r_fk = conn.execute(text("""
                SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'estantes'
                AND COLUMN_NAME = 'id_bodega' AND REFERENCED_TABLE_NAME IS NOT NULL
            """))
            fk_row = r_fk.fetchone()
            if fk_row:
                fk_name = fk_row[0]
                conn.execute(text(f"ALTER TABLE estantes DROP FOREIGN KEY `{fk_name}`"))
                conn.commit()
                print(f"OK: FK {fk_name} eliminada.")

            try:
                conn.execute(text("ALTER TABLE estantes DROP CONSTRAINT uq_estante_bodega_codigo"))
                conn.commit()
            except Exception as e:
                if "1091" in str(e) or "check" in str(e).lower():
                    pass
                else:
                    print(f"INFO: Constraint uq_estante_bodega_codigo: {e}")

            conn.execute(text("ALTER TABLE estantes DROP COLUMN id_bodega"))
            conn.commit()
            print("OK: Columna id_bodega eliminada.")

        # 6. Agregar FK y constraint
        try:
            conn.execute(text("""
                ALTER TABLE estantes
                ADD CONSTRAINT fk_estante_ubicacion FOREIGN KEY (id_ubicacion) REFERENCES ubicaciones(id) ON DELETE RESTRICT
            """))
            conn.commit()
        except Exception as e:
            if "Duplicate" in str(e):
                pass
            else:
                print(f"INFO: FK estante_ubicacion: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE estantes ADD CONSTRAINT uq_estante_ubicacion_codigo UNIQUE (id_ubicacion, codigo)
            """))
            conn.commit()
        except Exception as e:
            if "Duplicate" in str(e):
                pass
            else:
                print(f"INFO: Constraint uq_estante_ubicacion_codigo: {e}")

    print("Migración completada: Estantes ahora pertenecen a Ubicación.")

if __name__ == "__main__":
    main()
