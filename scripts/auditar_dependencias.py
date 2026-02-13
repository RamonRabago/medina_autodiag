"""
Audita dependencias en busca de vulnerabilidades conocidas.

  python scripts/auditar_dependencias.py

Requisitos:
  - pip-audit: pip install pip-audit  (o está en requirements.txt)
  - npm: para frontend (npm audit viene incluido)

Ejecutar con regularidad (ej. semanal, o antes de cada release).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")


def run_pip_audit():
    """Ejecuta pip-audit sobre el entorno actual."""
    print("\n" + "=" * 60)
    print("pip-audit (vulnerabilidades en paquetes Python)")
    print("=" * 60)
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--desc"],
            cwd=ROOT,
            capture_output=False,
        )
        return r.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_npm_audit():
    """Ejecuta npm audit en frontend/."""
    print("\n" + "=" * 60)
    print("npm audit (vulnerabilidades en paquetes Node)")
    print("=" * 60)
    if not os.path.isdir(FRONTEND) or not os.path.exists(os.path.join(FRONTEND, "package.json")):
        print("SKIP: frontend/package.json no encontrado")
        return True
    try:
        r = subprocess.run(
            ["npm", "audit"],
            cwd=FRONTEND,
            shell=True,
            capture_output=False,
        )
        # npm audit devuelve 1 si hay vulnerabilidades; 0 si no hay
        return r.returncode in (0, None)
    except FileNotFoundError:
        print("SKIP: npm no encontrado")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    print("Auditando dependencias - Medina AutoDiag", flush=True)
    print("(Ejecutar con regularidad: semanal o antes de cada release)")

    try:
        import pip_audit  # noqa: F401
    except ImportError:
        print("\n[!] pip-audit no esta instalado. Instalalo con:")
        print("  pip install pip-audit")
        print("\nO descomenta pip-audit en requirements.txt (sección AUDITORÍA DE SEGURIDAD)")
        pip_ok = False
    else:
        pip_ok = run_pip_audit()

    npm_ok = run_npm_audit()

    print("\n" + "=" * 60)
    if pip_ok and npm_ok:
        print("OK: Auditoria completada (revisa los resultados anteriores)")
        return 0
    print("[!] Revisa las vulnerabilidades indicadas arriba")
    return 1


if __name__ == "__main__":
    sys.exit(main())
