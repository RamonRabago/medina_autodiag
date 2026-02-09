from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
import json

from app.database import get_db
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.models.venta import Venta
from app.models.orden_trabajo import OrdenTrabajo
from app.models.pago import Pago
from app.models.cita import Cita
from app.models.registro_eliminacion_cliente import RegistroEliminacionCliente
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate
from app.utils.roles import require_roles


class EliminarClienteBody(BaseModel):
    motivo: str = Field(..., min_length=10, description="Motivo de la eliminación")

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


@router.get("/")
def listar_clientes(
    buscar: str | None = Query(None, description="Buscar en nombre, teléfono, email, RFC"),
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=500, description="Límite por página"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA"))
):
    query = db.query(Cliente)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        query = query.filter(
            or_(
                Cliente.nombre.like(term),
                Cliente.telefono.like(term),
                Cliente.email.like(term),
                Cliente.direccion.like(term),
                Cliente.rfc.like(term),
            )
        )
    total = query.count()
    clientes = query.order_by(Cliente.nombre.asc()).offset(skip).limit(limit).all()
    return {
        "clientes": clientes,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit,
    }


@router.get("/{id_cliente}/historial")
def obtener_historial_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    vehiculos = db.query(Vehiculo).filter(Vehiculo.id_cliente == id_cliente).all()
    ventas = db.query(Venta).filter(Venta.id_cliente == id_cliente).all()
    ordenes = (
        db.query(OrdenTrabajo)
        .options(joinedload(OrdenTrabajo.vehiculo))
        .filter(OrdenTrabajo.cliente_id == id_cliente)
        .order_by(OrdenTrabajo.fecha_ingreso.desc())
        .all()
    )
    citas = (
        db.query(Cita)
        .filter(Cita.id_cliente == id_cliente)
        .order_by(Cita.fecha_hora.desc())
        .limit(50)
        .all()
    )

    total_ventas = sum(float(v.total) for v in ventas)
    total_pagado_ventas = {}
    for v in ventas:
        pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == v.id_venta).scalar()
        total_pagado_ventas[v.id_venta] = float(pagado or 0)

    return {
        "cliente": {
            "id_cliente": cliente.id_cliente,
            "nombre": cliente.nombre,
            "telefono": cliente.telefono,
            "email": cliente.email,
            "direccion": cliente.direccion,
            "rfc": getattr(cliente, "rfc", None),
        },
        "resumen": {
            "cantidad_ventas": len(ventas),
            "total_ventas": total_ventas,
            "cantidad_ordenes": len(ordenes),
            "cantidad_citas": len(citas),
            "cantidad_vehiculos": len(vehiculos),
        },
        "vehiculos": [
            {"id_vehiculo": v.id_vehiculo, "marca": v.marca, "modelo": v.modelo, "anio": v.anio, "vin": v.vin}
            for v in vehiculos
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
        "ordenes_trabajo": [
            {
                "id": o.id,
                "numero_orden": o.numero_orden,
                "vehiculo": f"{o.vehiculo.marca} {o.vehiculo.modelo}" if o.vehiculo else None,
                "estado": o.estado.value if hasattr(o.estado, "value") else str(o.estado),
                "total": float(o.total),
            }
            for o in ordenes
        ],
        "citas": [
            {
                "id_cita": c.id_cita,
                "fecha_hora": c.fecha_hora.isoformat() if c.fecha_hora else None,
                "tipo": c.tipo.value if hasattr(c.tipo, "value") else str(c.tipo),
                "estado": c.estado.value if hasattr(c.estado, "value") else str(c.estado),
                "motivo": c.motivo,
            }
            for c in citas
        ],
    }


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
    body: EliminarClienteBody = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    n_ventas = db.query(Venta).filter(Venta.id_cliente == id_cliente).count()
    n_ordenes = db.query(OrdenTrabajo).filter(OrdenTrabajo.cliente_id == id_cliente).count()
    n_vehiculos = db.query(Vehiculo).filter(Vehiculo.id_cliente == id_cliente).count()

    bloqueos = []
    if n_ventas > 0:
        bloqueos.append(f"{n_ventas} venta(s)")
    if n_ordenes > 0:
        bloqueos.append(f"{n_ordenes} orden(es) de trabajo")
    if n_vehiculos > 0:
        bloqueos.append(f"{n_vehiculos} vehículo(s)")

    if bloqueos:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: tiene {', '.join(bloqueos)} asociados. Cancela/elimina las órdenes desde la ventana de eliminación o reasigna ventas y vehículos primero."
        )

    datos = {"nombre": cliente.nombre, "telefono": cliente.telefono, "email": cliente.email}
    reg = RegistroEliminacionCliente(
        id_cliente=id_cliente,
        id_usuario=current_user.id_usuario,
        motivo=body.motivo.strip(),
        datos_cliente=json.dumps(datos, ensure_ascii=False),
    )
    db.add(reg)
    db.delete(cliente)
    db.commit()
