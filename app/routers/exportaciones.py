"""
Router para exportar reportes a Excel.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from datetime import datetime

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.utils.roles import require_roles

router = APIRouter(
    prefix="/exportaciones",
    tags=["Exportaciones"]
)


def _encabezado(ws, titulos: list):
    """Estilo de encabezado."""
    for col, titulo in enumerate(titulos, 1):
        cell = ws.cell(row=1, column=col, value=titulo)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")


@router.get("/ventas")
def exportar_ventas(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    query = db.query(Venta)
    if fecha_desde:
        query = query.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        query = query.filter(func.date(Venta.fecha) <= fecha_hasta)
    ventas = query.order_by(Venta.fecha.desc()).limit(limit).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"
    _encabezado(ws, ["ID", "Fecha", "Cliente", "Total", "Saldo pendiente", "Estado"])

    for row, v in enumerate(ventas, 2):
        cliente = db.query(Cliente).filter(Cliente.id_cliente == v.id_cliente).first() if v.id_cliente else None
        total_pagado = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == v.id_venta).scalar()
        saldo = max(0, float(v.total) - float(total_pagado or 0))
        estado = v.estado.value if hasattr(v.estado, "value") else str(v.estado)
        ws.cell(row=row, column=1, value=v.id_venta)
        ws.cell(row=row, column=2, value=v.fecha.strftime("%Y-%m-%d %H:%M") if v.fecha else "")
        ws.cell(row=row, column=3, value=cliente.nombre if cliente else "-")
        ws.cell(row=row, column=4, value=float(v.total))
        ws.cell(row=row, column=5, value=round(saldo, 2))
        ws.cell(row=row, column=6, value=estado)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"ventas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )


@router.get("/productos-vendidos")
def exportar_productos_vendidos(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    subq = (
        db.query(
            DetalleVenta.id_item,
            DetalleVenta.descripcion,
            func.sum(DetalleVenta.cantidad).label("cantidad"),
            func.sum(DetalleVenta.subtotal).label("monto"),
        )
        .join(Venta, Venta.id_venta == DetalleVenta.id_venta)
        .filter(DetalleVenta.tipo == "PRODUCTO", Venta.estado != "CANCELADA")
    )
    if fecha_desde:
        subq = subq.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        subq = subq.filter(func.date(Venta.fecha) <= fecha_hasta)
    rows = (
        subq.group_by(DetalleVenta.id_item, DetalleVenta.descripcion)
        .order_by(func.sum(DetalleVenta.cantidad).desc())
        .limit(limit)
        .all()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Productos más vendidos"
    _encabezado(ws, ["Producto", "Cantidad", "Monto"])

    for row, r in enumerate(rows, 2):
        ws.cell(row=row, column=1, value=r.descripcion or f"ID {r.id_item}")
        ws.cell(row=row, column=2, value=int(r.cantidad or 0))
        ws.cell(row=row, column=3, value=float(r.monto or 0))

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"productos_vendidos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )


@router.get("/clientes-frecuentes")
def exportar_clientes_frecuentes(
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    subq = (
        db.query(
            Venta.id_cliente,
            func.count(Venta.id_venta).label("ventas"),
            func.sum(Venta.total).label("total"),
        )
        .filter(Venta.estado != "CANCELADA", Venta.id_cliente.isnot(None))
    )
    if fecha_desde:
        subq = subq.filter(func.date(Venta.fecha) >= fecha_desde)
    if fecha_hasta:
        subq = subq.filter(func.date(Venta.fecha) <= fecha_hasta)
    rows = (
        subq.group_by(Venta.id_cliente)
        .order_by(func.count(Venta.id_venta).desc())
        .limit(limit)
        .all()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes frecuentes"
    _encabezado(ws, ["Cliente", "Ventas", "Total"])

    for row, r in enumerate(rows, 2):
        c = db.query(Cliente).filter(Cliente.id_cliente == r.id_cliente).first()
        ws.cell(row=row, column=1, value=c.nombre if c else f"Cliente #{r.id_cliente}")
        ws.cell(row=row, column=2, value=r.ventas)
        ws.cell(row=row, column=3, value=float(r.total or 0))

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"clientes_frecuentes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )


@router.get("/cuentas-por-cobrar")
def exportar_cuentas_por_cobrar(
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

    wb = Workbook()
    ws = wb.active
    ws.title = "Cuentas por cobrar"
    _encabezado(ws, ["ID", "Cliente", "Total", "Saldo pendiente"])

    for row, it in enumerate(items, 2):
        ws.cell(row=row, column=1, value=it["id_venta"])
        ws.cell(row=row, column=2, value=it["nombre_cliente"])
        ws.cell(row=row, column=3, value=it["total"])
        ws.cell(row=row, column=4, value=it["saldo_pendiente"])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"cuentas_por_cobrar_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )
