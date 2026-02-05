"""
Ejecuta todas las pruebas de verificación del proyecto.
Usar después de cambios para asegurar que nada se rompió.

  python scripts/ejecutar_todas_pruebas.py
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TESTS = [
    "scripts/test_modulos_recientes.py",
    "scripts/test_cuentas_por_pagar.py",
    "scripts/test_reporte_utilidad.py",
]

def main():
    print("=" * 60)
    print("Ejecutando pruebas de verificación - Medina Autodiag")
    print("=" * 60)
    failed = []
    for script in TESTS:
        path = os.path.join(ROOT, script)
        if not os.path.exists(path):
            print(f"SKIP: {script} (no existe)")
            continue
        name = os.path.basename(script)
        print(f"\n--- {name} ---")
        r = subprocess.run([sys.executable, path], cwd=ROOT)
        if r.returncode != 0:
            failed.append(name)
    print("\n" + "=" * 60)
    if failed:
        print(f"FALLARON: {', '.join(failed)}")
        return 1
    print("Todas las pruebas pasaron OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
