from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.usuario import Usuario
from app.models.usuario_bodega import UsuarioBodega
from app.models.bodega import Bodega
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioOut
from app.utils.security import hash_password
from app.utils.roles import require_roles

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


class BodegasPermitidasUpdate(BaseModel):
    id_bodegas: List[int] = []


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


@router.put("/{id_usuario}", response_model=UsuarioOut)
def actualizar_usuario(
    id_usuario: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.nombre is not None:
        usuario.nombre = data.nombre
    if data.email is not None:
        existe = db.query(Usuario).filter(Usuario.email == data.email, Usuario.id_usuario != id_usuario).first()
        if existe:
            raise HTTPException(status_code=400, detail="Email ya está en uso por otro usuario")
        usuario.email = data.email
    if data.rol is not None:
        usuario.rol = data.rol
    if data.activo is not None:
        usuario.activo = data.activo
    if data.password is not None and data.password.strip():
        usuario.password_hash = hash_password(data.password)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/", response_model=list[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    return db.query(Usuario).all()


@router.get("/{id_usuario}/bodegas-permitidas")
def obtener_bodegas_permitidas(
    id_usuario: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    """Lista las bodegas permitidas de un usuario. Vacío = ve todas."""
    u = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    ids = [r[0] for r in db.query(UsuarioBodega.id_bodega).filter(
        UsuarioBodega.id_usuario == id_usuario
    ).all()]
    bodegas = db.query(Bodega).filter(Bodega.id.in_(ids)).order_by(Bodega.nombre).all() if ids else []
    return {
        "id_usuario": id_usuario,
        "nombre": u.nombre,
        "email": u.email,
        "rol": u.rol,
        "id_bodegas": ids,
        "bodegas": [{"id": b.id, "nombre": b.nombre} for b in bodegas],
    }


@router.put("/{id_usuario}/bodegas-permitidas")
def actualizar_bodegas_permitidas(
    id_usuario: int,
    data: BodegasPermitidasUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    """Asigna bodegas permitidas a un usuario. Vacío = ve todas."""
    u = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.query(UsuarioBodega).filter(UsuarioBodega.id_usuario == id_usuario).delete()
    for id_b in data.id_bodegas or []:
        b = db.query(Bodega).filter(Bodega.id == id_b).first()
        if b:
            db.add(UsuarioBodega(id_usuario=id_usuario, id_bodega=id_b))
    db.commit()
    ids = [r[0] for r in db.query(UsuarioBodega.id_bodega).filter(
        UsuarioBodega.id_usuario == id_usuario
    ).all()]
    bodegas = db.query(Bodega).filter(Bodega.id.in_(ids)).order_by(Bodega.nombre).all() if ids else []
    return {
        "mensaje": "Bodegas actualizadas",
        "id_bodegas": ids,
        "bodegas": [{"id": b.id, "nombre": b.nombre} for b in bodegas],
    }
