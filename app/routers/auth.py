import secrets
import threading
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.password_reset_token import PasswordResetToken
from app.models.usuario import Usuario
from app.schemas.auth import TokenResponse
from app.services.email_service import enviar_email_simple
from app.utils.jwt import create_access_token
from app.utils.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


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
            status_code=status.HTTP_403_FORBIDDEN, detail="Ya existen usuarios. El registro está deshabilitado."
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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login usando email
    OAuth2 requiere 'username', aquí se usa como email
    """
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()

    if not usuario or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = create_access_token(
        data={"sub": str(usuario.id_usuario), "rol": usuario.rol}  # 👈 CLAVE SEGÚN TU BD
    )

    return {"access_token": access_token, "token_type": "bearer"}


# --- Recuperación de contraseña ---


class OlvideContrasenaBody(BaseModel):
    email: EmailStr


@router.post("/olvide-contrasena")
def olvide_contrasena(body: OlvideContrasenaBody, db: Session = Depends(get_db)):
    """
    Solicita recuperación de contraseña. Si el email existe y el correo está configurado,
    envía un link. Siempre devuelve éxito para no revelar si el email está registrado.
    """
    email = body.email.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.activo:
        return {"mensaje": "Si el email está registrado, recibirás un enlace para restablecer tu contraseña."}

    # Invalidar tokens previos para este email
    db.query(PasswordResetToken).filter(PasswordResetToken.email == email).delete()

    token = secrets.token_urlsafe(48)
    expira = datetime.utcnow() + timedelta(hours=1)
    pr = PasswordResetToken(email=email, token=token, expira_en=expira)
    db.add(pr)
    db.commit()

    base_url = settings.APP_PUBLIC_URL.rstrip("/")
    link = f"{base_url}/restablecer-contrasena?token={token}"

    subject = f"Recuperar contraseña - {settings.APP_NAME}"
    cuerpo = f"""Hola,

Recibiste este correo porque solicitaste restablecer la contraseña de tu cuenta en MedinaAutoDiag.

Haz clic en el siguiente enlace para crear una nueva contraseña (válido por 1 hora):

{link}

Si no solicitaste este cambio, ignora este correo. Tu contraseña no se modificará.

Saludos,
Medina AutoDiag
"""

    def _enviar_en_background():
        import logging

        log = logging.getLogger(__name__)
        try:
            ok, err = enviar_email_simple(email, subject, cuerpo)
            if not ok:
                log.warning(f"Recuperacion contrasena: email no enviado a {email}: {err}")
            else:
                log.info(f"Recuperacion contrasena: email enviado a {email}")
        except Exception as e:
            log.exception(f"Recuperacion contrasena: error al enviar email: {e}")

    threading.Thread(target=_enviar_en_background, daemon=True).start()
    return {"mensaje": "Si el email está registrado, recibirás un enlace para restablecer tu contraseña."}


@router.get("/validar-token-reset")
def validar_token_reset(token: str = Query(..., min_length=10), db: Session = Depends(get_db)):
    """Verifica si un token de recuperación es válido (sin consumirlo)."""
    pr = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == token,
            PasswordResetToken.expira_en > datetime.utcnow(),
        )
        .first()
    )
    if not pr:
        return {"valido": False}
    return {"valido": True, "email": pr.email}


class RestablecerContrasenaBody(BaseModel):
    token: str = Field(..., min_length=10)
    nueva_password: str = Field(..., min_length=4)


@router.post("/restablecer-contrasena")
def restablecer_contrasena(body: RestablecerContrasenaBody, db: Session = Depends(get_db)):
    """Restablece la contraseña usando el token enviado por email."""
    pr = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == body.token,
            PasswordResetToken.expira_en > datetime.utcnow(),
        )
        .first()
    )
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El enlace ha caducado o no es válido. Solicita uno nuevo."
        )

    usuario = db.query(Usuario).filter(Usuario.email == pr.email).first()
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=400, detail="Usuario no encontrado o inactivo.")

    usuario.password_hash = hash_password(body.nueva_password)
    db.delete(pr)
    db.commit()

    return {"mensaje": "Contraseña actualizada. Ya puedes iniciar sesión."}
