from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioOut
from app.utils.security import hash_password
from app.utils.roles import require_roles

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    existe = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol,
        activo=data.activo
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/", response_model=list[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    return db.query(Usuario).all()
