"""Migra vehículos sin cliente a catalogo_vehiculos y actualiza ordenes_compra."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from app.config import settings


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # Obtener vehiculos sin cliente
        r = conn.execute(text("""
            SELECT id_vehiculo, marca, modelo, anio, motor, vin
            FROM vehiculos WHERE id_cliente IS NULL
        """))
        rows = r.fetchall()
        if not rows:
            print("No hay vehículos sin cliente para migrar.")
            return 0

        migrados = 0
        mapa_vehiculo_a_catalogo = {}  # id_vehiculo -> id_catalogo
        for row in rows:
            id_v, marca, modelo, anio, motor, vin = row
            motor = motor or None
            vin = vin or None
            # Buscar o crear en catálogo (evitar duplicados por anio+marca+modelo)
            r2 = conn.execute(text("""
                SELECT id FROM catalogo_vehiculos
                WHERE anio = :anio AND marca = :marca AND modelo = :modelo
                AND COALESCE(version_trim,'') = ''
                AND (motor = :motor OR (motor IS NULL AND :motor IS NULL))
            """), {"anio": anio, "marca": marca, "modelo": modelo, "motor": motor})
            existente = r2.fetchone()
            if existente:
                id_cat = existente[0]
            else:
                conn.execute(text("""
                    INSERT INTO catalogo_vehiculos (anio, marca, modelo, version_trim, motor, vin)
                    VALUES (:anio, :marca, :modelo, NULL, :motor, :vin)
                """), {"anio": anio, "marca": marca or "", "modelo": modelo or "", "motor": motor, "vin": vin})
                r3 = conn.execute(text("SELECT LAST_INSERT_ID()"))
                id_cat = r3.scalar()
            mapa_vehiculo_a_catalogo[id_v] = id_cat
            migrados += 1

        for id_v, id_cat in mapa_vehiculo_a_catalogo.items():
            conn.execute(text("""
                UPDATE ordenes_compra SET id_catalogo_vehiculo = :id_cat
                WHERE id_vehiculo = :id_v
            """), {"id_cat": id_cat, "id_v": id_v})
        conn.commit()
        print(f"OK: Migrados {migrados} vehículos a catálogo.")

        # Remover id_vehiculo de ordenes_compra (opcional - comentar si quieres mantener)
        # conn.execute(text("ALTER TABLE ordenes_compra DROP FOREIGN KEY fk_orden_compra_vehiculo"))
        # conn.execute(text("ALTER TABLE ordenes_compra DROP COLUMN id_vehiculo"))
        # conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
