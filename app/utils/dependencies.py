from fastapi import Depends
from app.utils.jwt import get_current_user
from app.models.usuario import Usuario


def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Dependency genérica para obtener el usuario autenticado y activo.
    Reutiliza la lógica centralizada en jwt.py
    """
    return current_user
