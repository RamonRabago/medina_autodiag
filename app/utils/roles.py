from fastapi import Depends, HTTPException, status
from app.utils.jwt import get_current_user
from app.models.usuario import Usuario


def require_roles(*roles_permitidos):
    """
    Dependency para validar roles por endpoint
    """
    def role_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        if current_user.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción"
            )

        return current_user

    return role_checker
