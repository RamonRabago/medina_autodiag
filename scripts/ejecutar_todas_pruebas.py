"""
Ejecuta todas las pruebas de verificación del proyecto.
Usar después de cambios para asegurar que nada se rompió.

  python scripts/ejecutar_todas_pruebas.py

IMPORTANTE: Activa el venv antes de ejecutar (pytest está en requirements.txt):
  .\\venv\\Scripts\\Activate.ps1   # Windows PowerShell
  pip install -r requirements.txt   # si faltan dependencias

O bien: make test  (ejecuta pytest tests/)
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Verificar que pytest esté disponible
try:
    import pytest  # noqa: F401
except ImportError:
    print("ERROR: pytest no está instalado. Activa el venv y ejecuta:")
    print("  pip install pytest pytest-asyncio httpx")
    print("O: pip install -r requirements.txt")
    sys.exit(1)

# 1. Primero pytest tests/ (estructura estándar)
# 2. Luego scripts legacy (por compatibilidad)
TESTS = [
    ("pytest tests/", [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]),
    ("scripts/test_modulos_recientes.py", [sys.executable, "scripts/test_modulos_recientes.py"]),
    ("scripts/test_cuentas_por_pagar.py", [sys.executable, "scripts/test_cuentas_por_pagar.py"]),
    ("scripts/test_reporte_utilidad.py", [sys.executable, "scripts/test_reporte_utilidad.py"]),
]

def main():
    print("=" * 60)
    print("Ejecutando pruebas de verificación - Medina Autodiag")
    print("=" * 60)
    failed = []
    for name, cmd in TESTS:
        if name.startswith("scripts/") and not os.path.exists(os.path.join(ROOT, name)):
            print(f"SKIP: {name} (no existe)")
            continue
        print(f"\n--- {name} ---")
        r = subprocess.run(cmd, cwd=ROOT)
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
