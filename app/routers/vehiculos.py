from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vehiculo import Vehiculo
from app.models.cliente import Cliente
from app.schemas.vehiculo import VehiculoCreate, VehiculoOut, VehiculoUpdate
from app.utils.roles import require_roles

router = APIRouter(prefix="/vehiculos", tags=["Vehículos"])


@router.get("/")
def listar_vehiculos(
    id_cliente: int | None = Query(None, description="Filtrar por cliente"),
    buscar: str | None = Query(None, description="Buscar en marca, modelo, VIN"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    query = db.query(Vehiculo)
    if id_cliente:
        query = query.filter(Vehiculo.id_cliente == id_cliente)
    if buscar and buscar.strip():
        buscar_pattern = f"%{buscar.strip()}%"
        query = query.filter(
            (Vehiculo.marca.like(buscar_pattern)) |
            (Vehiculo.modelo.like(buscar_pattern)) |
            (Vehiculo.vin.like(buscar_pattern)) |
            (Vehiculo.motor.like(buscar_pattern))
        )
    total = query.count()
    vehiculos = query.order_by(Vehiculo.id_vehiculo.desc()).offset(skip).limit(limit).all()
    resultado = []
    for v in vehiculos:
        resultado.append({
            "id_vehiculo": v.id_vehiculo,
            "id_cliente": v.id_cliente,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
            "color": v.motor,
            "numero_serie": v.vin,
            "vin": v.vin,
            "motor": v.motor,
        })
    return {
        "vehiculos": resultado,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.post("/", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    data: VehiculoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    # Validar que el cliente exista
    cliente = db.query(Cliente).filter(Cliente.id_cliente == data.id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    vehiculo = Vehiculo(**data.model_dump())
    db.add(vehiculo)
    db.commit()
    db.refresh(vehiculo)
    return vehiculo


@router.get("/cliente/{id_cliente}", response_model=list[VehiculoOut])
def vehiculos_por_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    return db.query(Vehiculo).filter(Vehiculo.id_cliente == id_cliente).all()


@router.get("/{id_vehiculo}", response_model=VehiculoOut)
def obtener_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return vehiculo


@router.put("/{id_vehiculo}", response_model=VehiculoOut)
def actualizar_vehiculo(
    id_vehiculo: int,
    data: VehiculoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(vehiculo, campo, valor)

    db.commit()
    db.refresh(vehiculo)
    return vehiculo


@router.delete("/{id_vehiculo}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    db.delete(vehiculo)
    db.commit()
