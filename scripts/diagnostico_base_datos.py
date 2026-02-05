"""
Diagnóstico de la base de datos - Verifica conexión y conteo de registros.

Ejecutar: python scripts/diagnostico_base_datos.py

Ayuda a identificar por qué la API no muestra datos (filtros, conexión, valores NULL, etc.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("\n=== Diagnóstico Base de Datos Medina AutoDiag ===\n")

    from app.config import settings
    print(f"DB config: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"URL (sin password): mysql+pymysql://{settings.DB_USER}:****@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}\n")

    try:
        from app.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            # Verificar conexión
            db.execute(text("SELECT 1"))
            print("[OK] Conexion a la base de datos: OK\n")

            # Conteos por tabla
            tablas = [
                ("clientes", "clientes", "id_cliente"),
                ("vehiculos", "vehiculos", "id_vehiculo"),
                ("usuarios", "usuarios", "id_usuario"),
                ("repuestos", "repuestos", "id_repuesto"),
                ("ventas", "ventas", "id_venta"),
                ("ordenes_trabajo", "ordenes_trabajo", "id"),
                ("detalle_venta", "detalle_venta", "id_detalle"),
                ("pagos", "pagos", "id_pago"),
            ]

            for nombre, tabla, pk in tablas:
                try:
                    r = db.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    total = r.scalar()
                    print(f"  {nombre}: {total} registros")
                except Exception as e:
                    print(f"  {nombre}: ERROR - {e}")

            # Repuestos: análisis de eliminado y activo
            print("\n--- Repuestos (filtros que aplica la API) ---")
            try:
                r = db.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN eliminado = 0 OR eliminado IS NULL THEN 1 ELSE 0 END) as no_eliminados,
                        SUM(CASE WHEN eliminado = 1 THEN 1 ELSE 0 END) as eliminados,
                        SUM(CASE WHEN eliminado IS NULL THEN 1 ELSE 0 END) as eliminado_null,
                        SUM(CASE WHEN activo = 1 THEN 1 ELSE 0 END) as activos,
                        SUM(CASE WHEN activo = 0 OR activo IS NULL THEN 1 ELSE 0 END) as inactivos
                    FROM repuestos
                """))
                row = r.fetchone()
                if row:
                    total, no_elim, elim, elim_null, activos, inact = row
                    print(f"  Total: {total}")
                    print(f"  eliminado=0 o NULL: {no_elim} (la API filtra eliminado=False, en SQL NULL no coincide)")
                    print(f"  eliminado=1: {elim}")
                    print(f"  eliminado IS NULL: {elim_null or 0}  <-- Si > 0, la API los excluye (NULL != False)")
                    print(f"  activo=1: {activos}")
                    print(f"  activo=0 o NULL: {inact}")
                    if (elim_null or 0) > 0:
                        print("\n  [!] Repuestos con eliminado=NULL no aparecen. Ejecutar:")
                        print("     UPDATE repuestos SET eliminado = 0 WHERE eliminado IS NULL;")
            except Exception as e:
                print(f"  Error en análisis repuestos: {e}")

            # Ventas por estado
            print("\n--- Ventas por estado ---")
            try:
                r = db.execute(text("""
                    SELECT estado, COUNT(*) FROM ventas GROUP BY estado
                """))
                for row in r.fetchall():
                    print(f"  {row[0]}: {row[1]}")
            except Exception as e:
                print(f"  Error: {e}")

        finally:
            db.close()

        print("\n=== Fin diagnóstico ===\n")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
