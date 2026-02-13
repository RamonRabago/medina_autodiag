"""
Script para corregir/reactivar un usuario admin.
Usa variables de entorno para evitar credenciales en código.

Ejemplo (desde raíz del proyecto):
  CORREGIR_USUARIO_EMAIL=admin@medinaautodiag.com CORREGIR_USUARIO_PASSWORD=Admin1234 python scripts/corregir_usuario.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.utils.security import hash_password

email = os.environ.get("CORREGIR_USUARIO_EMAIL")
password = os.environ.get("CORREGIR_USUARIO_PASSWORD")

if not email or not password:
    print("Uso: CORREGIR_USUARIO_EMAIL=... CORREGIR_USUARIO_PASSWORD=... python scripts/corregir_usuario.py")
    exit(1)

db = SessionLocal()

usuario = db.query(Usuario).filter(Usuario.email == email).first()

if usuario:
    usuario.password_hash = hash_password(password)
    usuario.activo = True
    usuario.rol = "ADMIN"
else:
    usuario = Usuario(
        email=email,
        password_hash=hash_password(password),
        activo=True,
        rol="ADMIN"
    )
    db.add(usuario)

db.commit()
db.close()

print(f"Usuario {email} corregido y activo")
