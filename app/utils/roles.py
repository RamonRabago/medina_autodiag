from fastapi import Depends, HTTPException, status
from app.utils.jwt import get_current_user
from app.models.usuario import Usuario


def require_roles(*roles_permitidos):
    """
    Dependency para validar roles por endpoint.
    Acepta: require_roles("ADMIN", "CAJA") o require_roles(["ADMIN", "CAJA"])
    """
    def role_checker(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        roles = list(roles_permitidos[0]) if (len(roles_permitidos) == 1 and isinstance(roles_permitidos[0], (list, tuple))) else list(roles_permitidos)
        rol_actual = current_user.rol.value if hasattr(current_user.rol, "value") else str(current_user.rol)
        if rol_actual not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción"
            )
        return current_user

    return role_checker
