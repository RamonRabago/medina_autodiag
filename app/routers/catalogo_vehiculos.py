"""Router para catálogo de vehículos (independiente de clientes). Usado en órdenes de compra."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.catalogo_vehiculo import CatalogoVehiculo
from app.schemas.catalogo_vehiculo import CatalogoVehiculoCreate, CatalogoVehiculoOut
from app.utils.roles import require_roles

router = APIRouter(prefix="/catalogo-vehiculos", tags=["Catálogo de vehículos"])


def _descripcion(v: CatalogoVehiculo) -> str:
    """Marca Modelo Año [+ Versión] [+ Motor]"""
    parts = [v.marca, v.modelo, str(v.anio)]
    if v.version_trim and v.version_trim.strip():
        parts.append(v.version_trim.strip())
    if v.motor and v.motor.strip():
        parts.append(v.motor.strip())
    return " ".join(parts)


@router.get("/", response_model=dict)
def listar(
    buscar: str | None = Query(None, description="Buscar en marca, modelo, versión, motor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "EMPLEADO", "TECNICO")),
):
    """Lista el catálogo de vehículos. Sin duplicados (validación al crear)."""
    query = db.query(CatalogoVehiculo)
    if buscar and buscar.strip():
        pat = f"%{buscar.strip()}%"
        query = query.filter(
            or_(
                CatalogoVehiculo.marca.like(pat),
                CatalogoVehiculo.modelo.like(pat),
                CatalogoVehiculo.version_trim.like(pat),
                CatalogoVehiculo.motor.like(pat),
            )
        )
    total = query.count()
    items = query.order_by(CatalogoVehiculo.anio.desc(), CatalogoVehiculo.marca, CatalogoVehiculo.modelo).offset(skip).limit(limit).all()
    return {
        "vehiculos": [
            {
                "id": v.id,
                "anio": v.anio,
                "marca": v.marca,
                "modelo": v.modelo,
                "version_trim": v.version_trim,
                "motor": v.motor,
                "vin": v.vin,
                "descripcion": _descripcion(v),
            }
            for v in items
        ],
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.post("/", status_code=201, response_model=dict)
def crear(
    data: CatalogoVehiculoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA", "EMPLEADO", "TECNICO")),
):
    """Crea entrada en catálogo. Evita duplicados (anio+marca+modelo+version_trim+motor)."""
    v_trim = (data.version_trim or "").strip() or None
    mot = (data.motor or "").strip() or None
    # Buscar duplicado
    q = db.query(CatalogoVehiculo).filter(
        CatalogoVehiculo.anio == data.anio,
        CatalogoVehiculo.marca == data.marca.strip().title(),
        CatalogoVehiculo.modelo == data.modelo.strip().title(),
    )
    if v_trim:
        q = q.filter(CatalogoVehiculo.version_trim == v_trim)
    else:
        q = q.filter((CatalogoVehiculo.version_trim.is_(None)) | (CatalogoVehiculo.version_trim == ""))
    if mot:
        q = q.filter(CatalogoVehiculo.motor == mot)
    else:
        q = q.filter((CatalogoVehiculo.motor.is_(None)) | (CatalogoVehiculo.motor == ""))
    existente = q.first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe: {existente.marca} {existente.modelo} {existente.anio}" + (f" {existente.version_trim}" if existente.version_trim else "") + (f" {existente.motor}" if existente.motor else ""),
        )

    v = CatalogoVehiculo(
        anio=data.anio,
        marca=data.marca.strip().title(),
        modelo=data.modelo.strip().title(),
        version_trim=v_trim,
        motor=mot,
        vin=(data.vin or "").strip().upper() or None,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return {
        "id": v.id,
        "anio": v.anio,
        "marca": v.marca,
        "modelo": v.modelo,
        "version_trim": v.version_trim,
        "motor": v.motor,
        "vin": v.vin,
        "descripcion": _descripcion(v),
    }
