"""Router para Festivos (Checador Fase 2). Solo ADMIN."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.models.festivo import Festivo
from app.models.usuario import Usuario
from app.schemas.festivo import FestivoCreate, FestivoUpdate, FestivoOut
from app.utils.roles import require_roles

router = APIRouter(prefix="/festivos", tags=["Festivos"])


@router.post("/", response_model=FestivoOut, status_code=201)
def crear_festivo(
    data: FestivoCreate,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    f = Festivo(fecha=data.fecha, nombre=data.nombre.strip(), anio=data.anio)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.get("/", response_model=list[FestivoOut])
def listar_festivos(
    anio: int | None = Query(None, ge=2000, le=2100),
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "TECNICO", "EMPLEADO")),
):
    q = db.query(Festivo)
    if anio is not None:
        q = q.filter(Festivo.anio == anio)
    return q.order_by(Festivo.fecha).all()


@router.get("/{id_festivo}", response_model=FestivoOut)
def obtener_festivo(
    id_festivo: int,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    f = db.query(Festivo).filter(Festivo.id == id_festivo).first()
    if not f:
        raise HTTPException(status_code=404, detail="Festivo no encontrado")
    return f


@router.put("/{id_festivo}", response_model=FestivoOut)
def actualizar_festivo(
    id_festivo: int,
    data: FestivoUpdate,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    f = db.query(Festivo).filter(Festivo.id == id_festivo).first()
    if not f:
        raise HTTPException(status_code=404, detail="Festivo no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    if data.nombre is not None:
        f.nombre = data.nombre.strip()
    db.commit()
    db.refresh(f)
    return f


@router.delete("/{id_festivo}", status_code=204)
def eliminar_festivo(
    id_festivo: int,
    db=Depends(get_db),
    current_user=Depends(require_roles("ADMIN")),
):
    f = db.query(Festivo).filter(Festivo.id == id_festivo).first()
    if not f:
        raise HTTPException(status_code=404, detail="Festivo no encontrado")
    db.delete(f)
    db.commit()
