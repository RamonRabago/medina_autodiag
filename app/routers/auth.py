from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import TokenResponse
from app.utils.security import verify_password, hash_password
from app.utils.jwt import create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


class RegistroBody(BaseModel):
    """Solo para crear el primer usuario (cuando no hay ninguno)."""
    nombre: str
    email: EmailStr
    password: str  # mínimo 4 caracteres


@router.post("/registro")
def registro_primero(body: RegistroBody, db: Session = Depends(get_db)):
    """
    Crea el primer usuario (solo si no hay ninguno). Útil en producción nueva.
    El primer usuario se crea como ADMIN. No requiere autenticación.
    """
    if db.query(Usuario).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ya existen usuarios. El registro está deshabilitado."
        )
    if len(body.password) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres")
    existe = db.query(Usuario).filter(Usuario.email == body.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    usuario = Usuario(
        nombre=body.nombre,
        email=body.email,
        password_hash=hash_password(body.password),
        rol="ADMIN",
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return {"mensaje": "Usuario creado. Ya puedes iniciar sesión.", "email": usuario.email}


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login usando email
    OAuth2 requiere 'username', aquí se usa como email
    """
    usuario = db.query(Usuario).filter(
        Usuario.email == form_data.username
    ).first()

    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    if not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    access_token = create_access_token(
        data={
            "sub": str(usuario.id_usuario),  # 👈 CLAVE SEGÚN TU BD
            "rol": usuario.rol
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
