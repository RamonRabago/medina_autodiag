"""Endpoints de reportes y estadísticas de ventas."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.orden_trabajo import OrdenTrabajo
from app.models.movimiento_inventario import TipoMovimiento, MovimientoInventario
from app.models.cancelacion_producto import CancelacionProducto
from app.utils.roles import require_roles
from app.utils.decimal_utils import to_decimal, money_round, to_float_money

router = APIRouter()


@router.get("/estadisticas/resumen")
def estadisticas_resumen(
    fecha_desde: str | None = Query(None, description="Fecha desde YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha hasta YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    query = db.query(Venta).filter(Venta.estado != "CANCELADA")
    if fecha_desde:
        query = query.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(Venta.fecha) <= fecha_hasta)
    ventas = query.all()
    total_ventas = len(ventas)
    monto_total = sum(float(v.total) for v in ventas)
    por_estado = {"pendientes": 0, "pagadas": 0, "canceladas": 0}
    for v in ventas:
        estado = v.estado.value if hasattr(v.estado, "value") else str(v.estado)
        por_estado["pendientes" if estado == "PENDIENTE" else "pagadas" if estado == "PAGADA" else "canceladas"] += 1
    canceladas = db.query(Venta).filter(Venta.estado == "CANCELADA")
    if fecha_desde:
        canceladas = canceladas.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        canceladas = canceladas.filter(func.date(Venta.fecha) <= fecha_hasta)
    por_estado["canceladas"] = canceladas.count()
    return {
        "total_ventas": total_ventas,
        "monto_total": round(monto_total, 2),
        "promedio_por_venta": round(monto_total / total_ventas, 2) if total_ventas else 0,
        "por_estado": por_estado,
    }


@router.get("/reportes/productos-mas-vendidos")
def reporte_productos_mas_vendidos(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    subq = db.query(
        DetalleVenta.id_item,
        DetalleVenta.descripcion,
        func.sum(DetalleVenta.cantidad).label("cantidad"),
        func.sum(DetalleVenta.subtotal).label("monto"),
    ).join(Venta, Venta.id_venta == DetalleVenta.id_venta).filter(
        DetalleVenta.tipo == "PRODUCTO",
        Venta.estado != "CANCELADA",
    )
    if fecha_desde:
        subq = subq.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        subq = subq.filter(func.date(Venta.fecha) <= fecha_hasta)
    rows = subq.group_by(DetalleVenta.id_item, DetalleVenta.descripcion).order_by(
        func.sum(DetalleVenta.cantidad).desc()
    ).limit(limit).all()
    productos = [{"producto": r.descripcion or f"ID {r.id_item}", "cantidad": int(r.cantidad or 0), "monto": float(r.monto or 0)} for r in rows]
    return {"productos": productos}


@router.get("/reportes/clientes-frecuentes")
def reporte_clientes_frecuentes(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    subq = db.query(
        Venta.id_cliente,
        func.count(Venta.id_venta).label("ventas"),
        func.sum(Venta.total).label("total"),
    ).filter(Venta.estado != "CANCELADA", Venta.id_cliente.isnot(None))
    if fecha_desde:
        subq = subq.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        subq = subq.filter(func.date(Venta.fecha) <= fecha_hasta)
    rows = subq.group_by(Venta.id_cliente).order_by(func.count(Venta.id_venta).desc()).limit(limit).all()
    resultado = []
    for r in rows:
        c = db.query(Cliente).filter(Cliente.id_cliente == r.id_cliente).first()
        resultado.append({
            "cliente": c.nombre if c else f"Cliente #{r.id_cliente}",
            "ventas": r.ventas,
            "total": float(r.total or 0),
        })
    return {"clientes": resultado}


@router.get("/reportes/cuentas-por-cobrar")
def reporte_cuentas_por_cobrar(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    query = db.query(Venta).filter(Venta.estado == "PENDIENTE")
    if fecha_desde:
        query = query.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(Venta.fecha) <= fecha_hasta)
    ventas = query.order_by(Venta.fecha.desc()).all()
    items = []
    for v in ventas:
        total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == v.id_venta).scalar()
        saldo = max(0, float(v.total) - float(total_pagado or 0))
        if saldo <= 0:
            continue
        cliente = db.query(Cliente).filter(Cliente.id_cliente == v.id_cliente).first() if v.id_cliente else None
        items.append({
            "id_venta": v.id_venta,
            "nombre_cliente": cliente.nombre if cliente else "-",
            "total": float(v.total),
            "saldo_pendiente": round(saldo, 2),
        })
    return {"items": items, "ventas": items}


@router.get("/reportes/ingresos-detalle")
def reporte_ingresos_detalle(
    fecha_desde: str = Query(..., description="YYYY-MM-DD obligatorio"),
    fecha_hasta: str = Query(..., description="YYYY-MM-DD obligatorio"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    """
    Detalle de pagos recibidos (ingresos) en un periodo.
    Filtra por fecha del pago.
    """
    query = (
        db.query(Pago)
        .join(Venta, Pago.id_venta == Venta.id_venta)
        .filter(Venta.estado != "CANCELADA")
        .filter(func.date(Pago.fecha) >= fecha_desde)
        .filter(func.date(Pago.fecha) <= fecha_hasta)
        .order_by(Pago.fecha.desc())
    )
    pagos = query.all()
    items = []
    for p in pagos:
        venta = db.query(Venta).filter(Venta.id_venta == p.id_venta).first()
        cliente = None
        if venta and venta.id_cliente:
            cliente = db.query(Cliente).filter(Cliente.id_cliente == venta.id_cliente).first()
        items.append({
            "id_pago": p.id_pago,
            "fecha": p.fecha.isoformat() if p.fecha else None,
            "id_venta": p.id_venta,
            "nombre_cliente": cliente.nombre if cliente else "-",
            "total_venta": float(venta.total) if venta else 0,
            "monto": float(p.monto),
            "metodo": p.metodo.value if hasattr(p.metodo, "value") else str(p.metodo),
            "referencia": p.referencia or None,
        })
    total = sum(float(p.monto) for p in pagos)
    resumen_metodo = {}
    for p in pagos:
        m = p.metodo.value if hasattr(p.metodo, "value") else str(p.metodo)
        resumen_metodo[m] = resumen_metodo.get(m, 0) + float(p.monto)
    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "total": round(total, 2),
        "cantidad_pagos": len(pagos),
        "resumen_por_metodo": resumen_metodo,
        "pagos": items,
    }


@router.get("/reportes/utilidad")
def reporte_utilidad(
    fecha_desde: str | None = Query(None, description="YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA")),
):
    """
    Reporte de utilidad: Ingresos - Costo de productos vendidos - Pérdidas por merma.
    Utilidad = Total ventas - CMV - Pérdidas por merma en cancelaciones.
    """
    query = db.query(Venta).filter(Venta.estado != "CANCELADA")
    if fecha_desde:
        query = query.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(Venta.fecha) <= fecha_hasta)
    ventas = query.order_by(Venta.fecha.asc()).all()

    total_ingresos = to_decimal(0)
    total_costo = to_decimal(0)
    detalle = []

    for v in ventas:
        ingresos = to_decimal(v.total)
        costo = to_decimal(0)

        if v.id_orden:
            orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == v.id_orden).first()
            if orden and not getattr(orden, "cliente_proporciono_refacciones", False):
                res = db.query(func.coalesce(func.sum(MovimientoInventario.costo_total), 0)).filter(
                    MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
                    MovimientoInventario.referencia == orden.numero_orden,
                ).scalar()
                costo = to_decimal(res or 0)
        else:
            res = db.query(func.coalesce(func.sum(MovimientoInventario.costo_total), 0)).filter(
                MovimientoInventario.id_venta == v.id_venta,
                MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
            ).scalar()
            costo = to_decimal(res or 0)

        utilidad = money_round(ingresos - costo)
        total_ingresos += ingresos
        total_costo += costo
        detalle.append({
            "id_venta": v.id_venta,
            "fecha": str(v.fecha.date()) if v.fecha else None,
            "ingresos": to_float_money(ingresos),
            "costo": to_float_money(costo),
            "utilidad": to_float_money(utilidad),
        })

    perdidas_mer = to_decimal(0)
    query_cancel = db.query(Venta).filter(Venta.estado == "CANCELADA")
    if fecha_desde:
        query_cancel = query_cancel.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query_cancel = query_cancel.filter(func.date(Venta.fecha) <= fecha_hasta)
    ids_canceladas = [v.id_venta for v in query_cancel.all()]
    if ids_canceladas:
        res_mer = db.query(func.coalesce(func.sum(CancelacionProducto.costo_total_mer), 0)).filter(
            CancelacionProducto.id_venta.in_(ids_canceladas)
        ).scalar()
        perdidas_mer = to_decimal(res_mer or 0)

    total_utilidad = money_round(total_ingresos - total_costo - perdidas_mer)
    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "total_ingresos": to_float_money(total_ingresos),
        "total_costo": to_float_money(total_costo),
        "perdidas_mer": to_float_money(perdidas_mer),
        "total_utilidad": to_float_money(total_utilidad),
        "cantidad_ventas": len(ventas),
        "detalle": detalle,
    }
