"""
Script para resetear la base de datos a cero.
Borra todos los datos, recrea las tablas y crea a Ramon como único administrador.

Uso (desde raíz del proyecto):
    python scripts/reset_bd_cero.py
    python scripts/reset_bd_cero.py --yes   # Sin confirmación (útil en scripts)

Variables de entorno opcionales:
    RESET_ADMIN_NOMBRE    (default: Ramon)
    RESET_ADMIN_EMAIL     (default: admin@medinaautodiag.com)
    RESET_ADMIN_PASSWORD  (default: Admin1234)

IMPORTANTE: Ejecutar solo en desarrollo o cuando no hay datos en producción.
"""
import os
import sys

# Asegurar que el proyecto esté en el path
_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

os.chdir(_raiz)

from sqlalchemy import text
from app.database import engine, Base
# Importar todos los modelos para poblar Base.metadata
import app.models  # noqa: F401
from app.models.usuario import Usuario
from app.utils.security import hash_password


# Configuración del admin (Ramon)
ADMIN_NOMBRE = os.getenv("RESET_ADMIN_NOMBRE", "Ramon")
ADMIN_EMAIL = os.getenv("RESET_ADMIN_EMAIL", "rrabago@medinaautodiag.com")
ADMIN_PASSWORD = os.getenv("RESET_ADMIN_PASSWORD", "Admin12345")


def main():
    skip_confirm = "--yes" in sys.argv or "-y" in sys.argv
    print("=" * 60)
    print("RESET BASE DE DATOS - MedinaAutoDiag")
    print("=" * 60)
    print(f"Admin: {ADMIN_NOMBRE} <{ADMIN_EMAIL}>")
    print()
    if not skip_confirm:
        resp = input("¿Borrar TODOS los datos y dejar solo al administrador? (escribe SI): ")
        if resp.strip().upper() != "SI":
            print("Cancelado.")
            return 1

    with engine.connect() as conn:
        with conn.begin():
            # MySQL: desactivar FK para evitar errores al borrar
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

            # Borrar todas las tablas
            tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
                )
            ).fetchall()
            for (t,) in tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS `{t}`"))
                    print(f"  Eliminada: {t}")
                except Exception as e:
                    print(f"  Advertencia al borrar {t}: {e}")

            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    print("\nRecreando tablas desde modelos...")
    Base.metadata.create_all(bind=engine)

    # Marcar migraciones como aplicadas (evita conflictos con alembic)
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    print("Alembic: stamp head OK")

    # Crear usuario Ramon
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        usuario = Usuario(
            nombre=ADMIN_NOMBRE,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            rol="ADMIN",
            activo=True,
        )
        db.add(usuario)
        db.commit()
        print(f"\nUsuario creado: {ADMIN_NOMBRE} ({ADMIN_EMAIL})")
        print(f"Contraseña: {ADMIN_PASSWORD}")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("RESET COMPLETADO. Ya puedes iniciar sesión.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {e}")
        raise
