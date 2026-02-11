"""Endpoints CRUD de ventas: listar, obtener, actualizar, crear."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.cliente import Cliente
from app.models.orden_trabajo import OrdenTrabajo
from app.models.pago import Pago
from app.schemas.venta import VentaCreate, VentaUpdate
from app.services.ventas_service import VentasService
from app.utils.roles import require_roles
from app.services.auditoria_service import registrar as registrar_auditoria

from .helpers import serializar_detalles_venta

router = APIRouter()


def _valor_err_a_http(e: ValueError) -> HTTPException:
    msg = str(e).lower()
    if "no encontrad" in msg:
        return HTTPException(status_code=404, detail=str(e))
    return HTTPException(status_code=400, detail=str(e))


@router.get("/")
def listar_ventas(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    estado: str | None = Query(None, description="Filtrar por estado"),
    id_cliente: int | None = Query(None, description="Filtrar por cliente"),
    fecha_desde: str | None = Query(None, description="Fecha desde YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha hasta YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA")),
):
    query = db.query(Venta)
    if estado:
        query = query.filter(Venta.estado == estado)
    if id_cliente:
        query = query.filter(Venta.id_cliente == id_cliente)
    if fecha_desde:
        query = query.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(Venta.fecha) <= fecha_hasta)
    total = query.count()
    ventas = query.order_by(Venta.fecha.desc()).offset(skip).limit(limit).all()
    resultado = []
    for v in ventas:
        cliente = db.query(Cliente).filter(Cliente.id_cliente == v.id_cliente).first() if v.id_cliente else None
        total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == v.id_venta).scalar()
        saldo = float(v.total) - float(total_pagado or 0)
        resultado.append({
            "id_venta": v.id_venta,
            "fecha": v.fecha.isoformat() if v.fecha else None,
            "nombre_cliente": cliente.nombre if cliente else None,
            "total": float(v.total),
            "saldo_pendiente": max(0, saldo),
            "estado": v.estado.value if hasattr(v.estado, "value") else str(v.estado),
        })
    return {
        "ventas": resultado,
        "total": total,
        "pagina": skip // limit + 1 if limit > 0 else 1,
        "total_paginas": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get("/{id_venta}")
def obtener_venta(
    id_venta: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA")),
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    cliente = db.query(Cliente).filter(Cliente.id_cliente == venta.id_cliente).first() if venta.id_cliente else None
    total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == venta.id_venta).scalar()
    detalles = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
    pagos = db.query(Pago).filter(Pago.id_venta == id_venta).order_by(Pago.fecha.asc()).all()
    orden_vinculada = None
    if getattr(venta, "id_orden", None):
        orden = db.query(OrdenTrabajo).options(
            joinedload(OrdenTrabajo.cliente), joinedload(OrdenTrabajo.vehiculo)
        ).filter(OrdenTrabajo.id == venta.id_orden).first()
        if orden:
            orden_vinculada = {
                "id": orden.id,
                "numero_orden": orden.numero_orden,
                "cliente_nombre": orden.cliente.nombre if orden.cliente else None,
                "vehiculo_info": f"{orden.vehiculo.marca} {orden.vehiculo.modelo} {orden.vehiculo.anio}" if orden.vehiculo else None,
                "estado": orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado),
            }
    return {
        "id_venta": venta.id_venta,
        "fecha": venta.fecha.isoformat() if venta.fecha else None,
        "id_cliente": venta.id_cliente,
        "id_vehiculo": venta.id_vehiculo,
        "nombre_cliente": cliente.nombre if cliente else None,
        "total": float(venta.total),
        "saldo_pendiente": max(0, float(venta.total) - float(total_pagado or 0)),
        "estado": venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado),
        "requiere_factura": bool(getattr(venta, "requiere_factura", False)),
        "comentarios": getattr(venta, "comentarios", None),
        "motivo_cancelacion": getattr(venta, "motivo_cancelacion", None),
        "fecha_cancelacion": venta.fecha_cancelacion.isoformat() if getattr(venta, "fecha_cancelacion", None) else None,
        "id_usuario_cancelacion": getattr(venta, "id_usuario_cancelacion", None),
        "id_orden": getattr(venta, "id_orden", None),
        "orden_vinculada": orden_vinculada,
        "detalles": serializar_detalles_venta(db, detalles),
        "pagos": [
            {
                "id_pago": p.id_pago,
                "fecha": p.fecha.isoformat() if p.fecha else None,
                "metodo": p.metodo.value if hasattr(p.metodo, "value") else str(p.metodo),
                "monto": float(p.monto),
                "referencia": p.referencia or None,
            }
            for p in pagos
        ],
    }


@router.put("/{id_venta}")
def actualizar_venta(
    id_venta: int,
    data: VentaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA")),
):
    try:
        venta = VentasService.actualizar_venta(
            db, id_venta, data, current_user.id_usuario
        )
        registrar_auditoria(db, current_user.id_usuario, "ACTUALIZAR", "VENTA", id_venta, {"campos": list(data.model_dump(exclude_unset=True).keys())})
        return venta
    except ValueError as e:
        raise _valor_err_a_http(e)


@router.post("/desde-orden/{orden_id}", status_code=status.HTTP_201_CREATED)
def crear_venta_desde_orden(
    orden_id: int,
    requiere_factura: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA")),
):
    try:
        venta = VentasService.crear_venta_desde_orden(
            db, orden_id, requiere_factura, current_user.id_usuario
        )
        registrar_auditoria(db, current_user.id_usuario, "CREAR", "VENTA", venta.id_venta, {"desde_orden": orden_id})
        return venta
    except ValueError as e:
        raise _valor_err_a_http(e)


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_venta(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO")),
):
    try:
        venta = VentasService.crear_venta(db, data, current_user.id_usuario)
        registrar_auditoria(db, current_user.id_usuario, "CREAR", "VENTA", venta.id_venta, {})
        return venta
    except ValueError as e:
        raise _valor_err_a_http(e)
