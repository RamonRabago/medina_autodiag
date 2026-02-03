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
from app.models.vehiculo import Vehiculo
from app.models.venta import Venta
from app.models.servicio import Servicio
from sqlalchemy import or_
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


@router.get("/clientes")
def exportar_clientes(
    buscar: str | None = Query(None, description="Filtrar por nombre, teléfono, email, RFC"),
    limit: int = Query(5000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA"))
):
    """Exporta el listado completo de clientes a Excel."""
    query = db.query(Cliente)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        filters = [
            Cliente.nombre.like(term),
            Cliente.telefono.like(term),
            Cliente.email.like(term),
            Cliente.direccion.like(term),
        ]
        if hasattr(Cliente, "rfc"):
            filters.append(Cliente.rfc.like(term))
        query = query.filter(or_(*filters))
    clientes = query.order_by(Cliente.nombre.asc()).limit(limit).all()

    # Contar ventas y vehículos por cliente
    ventas_count = {}
    vehiculos_count = {}
    for c in clientes:
        ventas_count[c.id_cliente] = db.query(Venta).filter(Venta.id_cliente == c.id_cliente).count()
        vehiculos_count[c.id_cliente] = db.query(Vehiculo).filter(Vehiculo.id_cliente == c.id_cliente).count()

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    _encabezado(ws, ["ID", "Nombre", "Teléfono", "Email", "Dirección", "RFC", "Ventas", "Vehículos", "Fecha alta"])

    for row, c in enumerate(clientes, 2):
        ws.cell(row=row, column=1, value=c.id_cliente)
        ws.cell(row=row, column=2, value=c.nombre or "")
        ws.cell(row=row, column=3, value=c.telefono or "")
        ws.cell(row=row, column=4, value=c.email or "")
        ws.cell(row=row, column=5, value=(c.direccion or "")[:200])
        ws.cell(row=row, column=6, value=getattr(c, "rfc", None) or "")
        ws.cell(row=row, column=7, value=ventas_count.get(c.id_cliente, 0))
        ws.cell(row=row, column=8, value=vehiculos_count.get(c.id_cliente, 0))
        ws.cell(row=row, column=9, value=c.creado_en.strftime("%Y-%m-%d %H:%M") if c.creado_en else "")

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"clientes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )


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


@router.get("/servicios")
def exportar_servicios(
    buscar: str | None = Query(None, description="Buscar en código o nombre"),
    categoria: str | None = Query(None, description="Filtrar por categoría"),
    activo: bool | None = Query(None, description="Filtrar por activo/inactivo"),
    limit: int = Query(5000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA"))
):
    """Exporta el catálogo de servicios a Excel."""
    query = db.query(Servicio)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        query = query.filter(
            (Servicio.codigo.like(term)) | (Servicio.nombre.like(term))
        )
    if categoria:
        query = query.filter(Servicio.categoria == categoria)
    if activo is not None:
        query = query.filter(Servicio.activo == activo)
    servicios = query.order_by(Servicio.codigo.asc()).limit(limit).all()

    cat_display = {
        "MANTENIMIENTO": "Mantenimiento",
        "REPARACION": "Reparación",
        "DIAGNOSTICO": "Diagnóstico",
        "ELECTRICIDAD": "Electricidad",
        "SUSPENSION": "Suspensión",
        "FRENOS": "Frenos",
        "MOTOR": "Motor",
        "TRANSMISION": "Transmisión",
        "AIRE_ACONDICIONADO": "Aire Acondicionado",
        "CARROCERIA": "Carrocería",
        "OTROS": "Otros",
    }

    wb = Workbook()
    ws = wb.active
    ws.title = "Servicios"
    _encabezado(ws, ["ID", "Código", "Nombre", "Categoría", "Descripción", "Precio", "Tiempo (min)", "Requiere repuestos", "Estado"])

    for row, s in enumerate(servicios, 2):
        cat_val = s.categoria.value if hasattr(s.categoria, "value") else str(s.categoria)
        ws.cell(row=row, column=1, value=s.id)
        ws.cell(row=row, column=2, value=s.codigo or "")
        ws.cell(row=row, column=3, value=s.nombre or "")
        ws.cell(row=row, column=4, value=cat_display.get(cat_val, cat_val))
        ws.cell(row=row, column=5, value=(s.descripcion or "")[:200])
        ws.cell(row=row, column=6, value=float(s.precio_base or 0))
        ws.cell(row=row, column=7, value=s.tiempo_estimado_minutos or 0)
        ws.cell(row=row, column=8, value="Sí" if s.requiere_repuestos else "No")
        ws.cell(row=row, column=9, value="Activo" if s.activo else "Inactivo")

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"servicios_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )


@router.get("/vehiculos")
def exportar_vehiculos(
    buscar: str | None = Query(None, description="Buscar en marca, modelo, VIN"),
    id_cliente: int | None = Query(None, description="Filtrar por cliente"),
    limit: int = Query(5000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "TECNICO", "CAJA"))
):
    """Exporta el listado completo de vehículos a Excel."""
    query = db.query(Vehiculo)
    if id_cliente:
        query = query.filter(Vehiculo.id_cliente == id_cliente)
    if buscar and buscar.strip():
        term = f"%{buscar.strip()}%"
        filters = [
            Vehiculo.marca.like(term),
            Vehiculo.modelo.like(term),
            Vehiculo.vin.like(term),
            Vehiculo.motor.like(term),
        ]
        if hasattr(Vehiculo, "color"):
            filters.append(Vehiculo.color.like(term))
        query = query.filter(or_(*filters))
    vehiculos = query.order_by(Vehiculo.id_vehiculo.desc()).limit(limit).all()

    def _color_display(v):
        c = getattr(v, "color", None)
        m = getattr(v, "motor", None)
        if c:
            return c
        if m and not str(m).replace(".", "").replace(",", "").isdigit():
            return m
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Vehículos"
    _encabezado(ws, ["ID", "Cliente", "Marca", "Modelo", "Año", "Color", "VIN", "Motor", "Fecha alta"])

    for row, v in enumerate(vehiculos, 2):
        cliente = db.query(Cliente).filter(Cliente.id_cliente == v.id_cliente).first() if v.id_cliente else None
        color_val = _color_display(v)
        ws.cell(row=row, column=1, value=v.id_vehiculo)
        ws.cell(row=row, column=2, value=cliente.nombre if cliente else "")
        ws.cell(row=row, column=3, value=v.marca or "")
        ws.cell(row=row, column=4, value=v.modelo or "")
        ws.cell(row=row, column=5, value=v.anio or "")
        ws.cell(row=row, column=6, value=color_val or "")
        ws.cell(row=row, column=7, value=v.vin or "")
        ws.cell(row=row, column=8, value=v.motor or "")
        ws.cell(row=row, column=9, value=v.creado_en.strftime("%Y-%m-%d %H:%M") if v.creado_en else "")

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"vehiculos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
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
