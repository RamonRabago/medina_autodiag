from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate
from app.utils.roles import require_roles

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("/", response_model=list[ClienteOut])
def listar_clientes(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    return db.query(Cliente).all()


@router.get("/{id_cliente}", response_model=ClienteOut)
def obtener_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.put("/{id_cliente}", response_model=ClienteOut)
def actualizar_cliente(
    id_cliente: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{id_cliente}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db.delete(cliente)
    db.commit()
