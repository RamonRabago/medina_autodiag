"""
Actualiza el código de repuestos eliminados o desactivados para liberar el código original.

Ejecutar: python scripts/liberar_codigos_repuestos_eliminados.py

Repuestos con eliminado=1 o activo=0 tendrán su codigo cambiado a {codigo}_ELIM_{id},
permitiendo crear nuevos repuestos con el mismo código.
"""
import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.repuesto import Repuesto

def main():
    print("\n=== Liberar códigos de repuestos eliminados/desactivados ===\n")

    db = SessionLocal()
    try:
        # Repuestos eliminados o desactivados que aún tienen el código "limpio" (sin _ELIM_)
        repuestos = db.query(Repuesto).filter(
            (Repuesto.eliminado == True) | (Repuesto.activo == False)
        ).all()

        actualizados = 0
        for r in repuestos:
            # Si ya tiene sufijo _ELIM_, no cambiar
            if "_ELIM_" in (r.codigo or ""):
                continue
            codigo_nuevo = f"{r.codigo}_ELIM_{r.id_repuesto}"
            print(f"  {r.codigo} -> {codigo_nuevo} (id={r.id_repuesto})")
            r.codigo = codigo_nuevo
            actualizados += 1

        if actualizados == 0:
            print("No hay repuestos a actualizar.")
            return

        db.commit()
        print(f"\nOK: Se liberaron {actualizados} códigos. Ya puedes crear repuestos con esos códigos.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
