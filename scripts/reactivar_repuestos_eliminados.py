"""
Reactiva repuestos marcados como eliminados (soft delete).

Ejecutar: python scripts/reactivar_repuestos_eliminados.py

Útil si los repuestos fueron marcados eliminado=1 por error (ej. durante pruebas)
y la API no los muestra en listados ni los permite en ventas/órdenes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("\n=== Reactivar repuestos eliminados ===\n")

    from app.database import SessionLocal
    from app.models.repuesto import Repuesto
    from sqlalchemy import text

    db = SessionLocal()
    try:
        # Contar eliminados
        eliminados = db.query(Repuesto).filter(Repuesto.eliminado == True).all()
        n = len(eliminados)
        if n == 0:
            print("No hay repuestos marcados como eliminados.")
            return 0

        print(f"Se encontraron {n} repuestos con eliminado=1:")
        for r in eliminados:
            print(f"  - {r.codigo} | {r.nombre}")

        # Reactivar
        db.execute(text("""
            UPDATE repuestos
            SET eliminado = 0, activo = 1,
                fecha_eliminacion = NULL,
                motivo_eliminacion = NULL,
                id_usuario_eliminacion = NULL
            WHERE eliminado = 1
        """))
        db.commit()
        print(f"\n[OK] {n} repuestos reactivados (eliminado=0, activo=1).")
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
