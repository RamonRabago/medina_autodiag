from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.database import get_db
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.models.venta import Venta
from app.models.orden_trabajo import OrdenTrabajo
from app.models.pago import Pago
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
    buscar: str | None = Query(None, description="Buscar en nombre, teléfono, email, RFC"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO"))
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
    return query.order_by(Cliente.nombre.asc()).all()


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
            "cantidad_citas": 0,
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
        "citas": [],
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
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN"))
):
    cliente = db.query(Cliente).filter(Cliente.id_cliente == id_cliente).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db.delete(cliente)
    db.commit()
