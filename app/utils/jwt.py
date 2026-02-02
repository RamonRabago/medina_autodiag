"""
Gestión de autenticación JWT
"""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.usuario import Usuario
from app.config import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Esquema OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict) -> str:
    """
    Crea un JWT con expiración
    
    Args:
        data: Diccionario con la información a codificar (ej: {"sub": user_id})
    
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    logger.info(f"Token creado para usuario ID: {data.get('sub')}")
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Obtiene el usuario autenticado desde el JWT
    
    Args:
        token: Token JWT del header Authorization
        db: Sesión de base de datos
    
    Returns:
        Usuario autenticado
    
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decodificar token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        
        if user_id is None:
            logger.warning("Token sin campo 'sub'")
            raise credentials_exception
    
    except JWTError as e:
        logger.error(f"Error al decodificar JWT: {str(e)}")
        raise credentials_exception

    # Buscar usuario en base de datos
    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == int(user_id)
    ).first()

    if not usuario:
        logger.warning(f"Usuario no encontrado: {user_id}")
        raise credentials_exception

    if not usuario.activo:
        logger.warning(f"Usuario inactivo intentó autenticarse: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo"
        )

    logger.debug(f"Usuario autenticado: {usuario.id_usuario} - {usuario.nombre}")
    return usuario
