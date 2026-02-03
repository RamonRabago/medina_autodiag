from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import json

from app.database import get_db
from app.models.vehiculo import Vehiculo
from app.models.cliente import Cliente
from app.models.orden_trabajo import OrdenTrabajo
from app.models.venta import Venta
from app.models.pago import Pago
from app.models.registro_eliminacion_vehiculo import RegistroEliminacionVehiculo
from app.schemas.vehiculo import VehiculoCreate, VehiculoOut, VehiculoUpdate
from app.utils.roles import require_roles

router = APIRouter(prefix="/vehiculos", tags=["Vehículos"])


def _color_display(v) -> str | None:
    """Obtiene color: columna real, o motor si parece texto (no numérico como 1.8)."""
    c = getattr(v, "color", None)
    m = getattr(v, "motor", None)
    if c:
        return c
    if m and not str(m).replace(".", "").replace(",", "").isdigit():
        return m
    return None


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
        cliente = db.query(Cliente).filter(Cliente.id_cliente == v.id_cliente).first() if v.id_cliente else None
        color_val = _color_display(v)
        resultado.append({
            "id_vehiculo": v.id_vehiculo,
            "id_cliente": v.id_cliente,
            "cliente_nombre": cliente.nombre if cliente else None,
            "marca": v.marca,
            "modelo": v.modelo,
            "anio": v.anio,
            "color": color_val,
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

    vehiculo = Vehiculo(
        id_cliente=data.id_cliente,
        marca=data.marca,
        modelo=data.modelo,
        anio=data.anio,
        color=data.color or None,
        vin=data.numero_serie or None,
        motor=None,
    )
    db.add(vehiculo)
    db.commit()
    db.refresh(vehiculo)
    return VehiculoOut(
        id_vehiculo=vehiculo.id_vehiculo,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        anio=vehiculo.anio,
        color=_color_display(vehiculo),
        numero_serie=vehiculo.vin,
        id_cliente=vehiculo.id_cliente,
        creado_en=vehiculo.creado_en,
    )


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
    return VehiculoOut(
        id_vehiculo=vehiculo.id_vehiculo,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        anio=vehiculo.anio,
        color=_color_display(vehiculo),
        numero_serie=vehiculo.vin,
        id_cliente=vehiculo.id_cliente,
        creado_en=vehiculo.creado_en,
    )


@router.get("/{id_vehiculo}/historial")
def historial_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    """Historial del vehículo: datos, órdenes de trabajo y ventas asociadas."""
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    cliente = db.query(Cliente).filter(Cliente.id_cliente == vehiculo.id_cliente).first()
    ordenes = (
        db.query(OrdenTrabajo)
        .filter(OrdenTrabajo.vehiculo_id == id_vehiculo)
        .order_by(OrdenTrabajo.fecha_ingreso.desc())
        .all()
    )
    ventas = db.query(Venta).filter(Venta.id_vehiculo == id_vehiculo).all()
    total_pagado_ventas = {}
    for v in ventas:
        pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == v.id_venta).scalar()
        total_pagado_ventas[v.id_venta] = float(pagado or 0)

    color_val = _color_display(vehiculo)
    return {
        "vehiculo": {
            "id_vehiculo": vehiculo.id_vehiculo,
            "marca": vehiculo.marca,
            "modelo": vehiculo.modelo,
            "anio": vehiculo.anio,
            "color": color_val,
            "vin": vehiculo.vin,
            "cliente_nombre": cliente.nombre if cliente else None,
        },
        "resumen": {
            "cantidad_ordenes": len(ordenes),
            "cantidad_ventas": len(ventas),
        },
        "ordenes_trabajo": [
            {
                "id": o.id,
                "numero_orden": o.numero_orden,
                "fecha_ingreso": o.fecha_ingreso.isoformat() if o.fecha_ingreso else None,
                "estado": o.estado.value if hasattr(o.estado, "value") else str(o.estado),
                "total": float(o.total),
            }
            for o in ordenes
        ],
        "ventas": [
            {
                "id_venta": v.id_venta,
                "fecha": v.fecha.isoformat() if v.fecha else None,
                "total": float(v.total),
                "total_pagado": total_pagado_ventas.get(v.id_venta, 0),
                "estado": v.estado.value if hasattr(v.estado, "value") else str(v.estado),
            }
            for v in ventas
        ],
    }


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

    d = data.model_dump(exclude_unset=True)
    mapeo = {"numero_serie": "vin"}
    for campo, valor in d.items():
        campo_modelo = mapeo.get(campo, campo)
        if hasattr(vehiculo, campo_modelo):
            setattr(vehiculo, campo_modelo, valor)

    db.commit()
    db.refresh(vehiculo)
    return VehiculoOut(
        id_vehiculo=vehiculo.id_vehiculo,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        anio=vehiculo.anio,
        color=_color_display(vehiculo),
        numero_serie=vehiculo.vin,
        id_cliente=vehiculo.id_cliente,
        creado_en=vehiculo.creado_en,
    )


class EliminarVehiculoBody(BaseModel):
    motivo: str = Field(..., min_length=10, description="Motivo de la eliminación")


@router.delete("/{id_vehiculo}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_vehiculo(
    id_vehiculo: int,
    body: EliminarVehiculoBody = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    ordenes = db.query(OrdenTrabajo).filter(OrdenTrabajo.vehiculo_id == id_vehiculo).count()
    if ordenes > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {ordenes} orden(es) de trabajo asociada(s). Cancela y elimina las órdenes primero."
        )

    cliente = db.query(Cliente).filter(Cliente.id_cliente == vehiculo.id_cliente).first()
    datos = {
        "marca": vehiculo.marca,
        "modelo": vehiculo.modelo,
        "anio": vehiculo.anio,
        "color": _color_display(vehiculo),
        "cliente": cliente.nombre if cliente else None,
    }
    reg = RegistroEliminacionVehiculo(
        id_vehiculo=id_vehiculo,
        id_usuario=current_user.id_usuario,
        motivo=body.motivo.strip(),
        datos_vehiculo=json.dumps(datos, ensure_ascii=False),
    )
    db.add(reg)
    db.delete(vehiculo)
    db.commit()
