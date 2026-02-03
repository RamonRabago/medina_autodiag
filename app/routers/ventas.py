from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from app.database import get_db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.cliente import Cliente
from app.models.vehiculo import Vehiculo
from app.models.pago import Pago
from app.models.orden_trabajo import OrdenTrabajo
from app.schemas.venta import VentaCreate, VentaUpdate
from app.utils.roles import require_roles
from app.config import settings

router = APIRouter(
    prefix="/ventas",
    tags=["Ventas"]
)


@router.get("/")
def listar_ventas(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    estado: str | None = Query(None, description="Filtrar por estado"),
    id_cliente: int | None = Query(None, description="Filtrar por cliente"),
    fecha_desde: str | None = Query(None, description="Fecha desde YYYY-MM-DD"),
    fecha_hasta: str | None = Query(None, description="Fecha hasta YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
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


@router.get("/ordenes-disponibles")
def ordenes_disponibles_para_vincular(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    """Órdenes ENTREGADAS o COMPLETADAS que aún no tienen venta vinculada."""
    from sqlalchemy.orm import joinedload
    ids_ocupados = [r[0] for r in db.query(Venta.id_orden).filter(Venta.id_orden.isnot(None)).distinct().all()]
    query = db.query(OrdenTrabajo).filter(
        OrdenTrabajo.estado.in_(["ENTREGADA", "COMPLETADA"]),
    )
    if ids_ocupados:
        query = query.filter(OrdenTrabajo.id.notin_(ids_ocupados))
    ordenes = (
        query.options(joinedload(OrdenTrabajo.cliente), joinedload(OrdenTrabajo.vehiculo))
        .order_by(OrdenTrabajo.fecha_ingreso.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": o.id,
            "numero_orden": o.numero_orden,
            "cliente_nombre": o.cliente.nombre if o.cliente else None,
            "vehiculo_info": f"{o.vehiculo.marca} {o.vehiculo.modelo} {o.vehiculo.anio}" if o.vehiculo else None,
            "estado": o.estado.value if hasattr(o.estado, "value") else str(o.estado),
            "total": float(o.total),
        }
        for o in ordenes
    ]


class VincularOrdenBody(BaseModel):
    id_orden: int | None = None


@router.put("/{id_venta}/vincular-orden")
def vincular_orden_venta(
    id_venta: int,
    body: VincularOrdenBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == "CANCELADA":
        raise HTTPException(status_code=400, detail="No se puede vincular orden a una venta cancelada")
    if body.id_orden is None:
        venta.id_orden = None
        db.commit()
        return {"id_venta": id_venta, "id_orden": None, "mensaje": "Orden desvinculada"}
    orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == body.id_orden).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    if orden.estado not in ("ENTREGADA", "COMPLETADA"):
        raise HTTPException(status_code=400, detail="Solo se pueden vincular órdenes ENTREGADAS o COMPLETADAS")
    ya_vinculada = db.query(Venta).filter(Venta.id_orden == body.id_orden, Venta.id_venta != id_venta).first()
    if ya_vinculada:
        raise HTTPException(status_code=400, detail="Esta orden ya está vinculada a otra venta")
    venta.id_orden = body.id_orden
    db.commit()
    return {"id_venta": id_venta, "id_orden": body.id_orden, "mensaje": "Orden vinculada"}


@router.get("/{id_venta}")
def obtener_venta(
    id_venta: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
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
        from sqlalchemy.orm import joinedload
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
        "motivo_cancelacion": getattr(venta, "motivo_cancelacion", None),
        "id_orden": getattr(venta, "id_orden", None),
        "orden_vinculada": orden_vinculada,
        "detalles": [
            {
                "tipo": d.tipo.value if hasattr(d.tipo, "value") else str(d.tipo),
                "id_item": d.id_item,
                "descripcion": d.descripcion,
                "cantidad": d.cantidad,
                "precio_unitario": float(d.precio_unitario or 0),
                "subtotal": float(d.subtotal),
            }
            for d in detalles
        ],
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
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == "CANCELADA":
        raise HTTPException(status_code=400, detail="No se puede editar una venta cancelada")
    if not data.detalles or len(data.detalles) == 0:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos un detalle")

    total_pagado = float(db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == id_venta).scalar() or 0)
    subtotal = sum(item.cantidad * item.precio_unitario for item in data.detalles)
    total_nuevo = round(subtotal * 1.08, 2) if data.requiere_factura else round(subtotal, 2)
    if total_pagado > 0 and total_nuevo < total_pagado:
        raise HTTPException(
            status_code=400,
            detail=f"El total no puede ser menor a lo ya pagado (${total_pagado:.2f})"
        )

    venta.id_cliente = data.id_cliente
    venta.id_vehiculo = data.id_vehiculo
    venta.requiere_factura = data.requiere_factura
    venta.total = total_nuevo

    db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).delete()
    for item in data.detalles:
        sub = item.cantidad * item.precio_unitario
        db.add(DetalleVenta(
            id_venta=id_venta,
            tipo=item.tipo,
            id_item=item.id_item,
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=sub,
        ))
    db.commit()
    return {"id_venta": id_venta, "total": float(total_nuevo)}


# Colores: barras sección (azul oscuro), barra fecha/orden (azul claro), estado
_COLOR_BARRA = HexColor("#1e40af")
_COLOR_AZUL_CLARO = HexColor("#93c5fd")
_COLOR_VERDE = HexColor("#16a34a")
_COLOR_ROJO = HexColor("#dc2626")
_COLOR_GRIS_SUAVE = HexColor("#9ca3af")


def _barra_azul(p, x, y, ancho, alto, texto, font="Helvetica-Bold", size=10):
    """Dibuja barra azul con texto blanco centrado."""
    p.setFillColor(_COLOR_BARRA)
    p.rect(x, y - alto, ancho, alto, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(font, size)
    centro_x = x + ancho / 2
    texto_y = y - alto + 0.06 * inch
    p.drawCentredString(centro_x, texto_y, texto)
    p.setFillColor(HexColor("#000000"))
    return y - alto


def _generar_pdf_ticket(venta_data: dict, tipo: str, app_name: str = "MedinaAutoDiag") -> bytes:
    """Genera PDF con formato original: MANO DE OBRA, PARTES, info cliente/vehículo, estilos azules."""
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    margin = inch
    ancho_util = w - 2 * margin
    y = h - margin

    # === ENCABEZADO ===
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(w / 2, y, app_name)
    y -= 0.28 * inch
    p.setFont("Helvetica", 11)
    p.drawCentredString(w / 2, y, "SERVICIO Y DIAGNOSTICO AUTOMOTRIZ")
    y -= 0.25 * inch
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.5)
    p.line(margin, y, w - margin, y)
    y -= 0.3 * inch

    # === FECHA, ORDEN, ENTREGA (barra azul claro, texto distribuido) ===
    fecha_str = venta_data.get("fecha", "")[:19].replace("T", " ") if venta_data.get("fecha") else "-"
    id_venta = venta_data.get("id_venta", "")
    alto_caja = 0.36 * inch
    p.setFillColor(_COLOR_AZUL_CLARO)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.25)
    p.rect(margin, y - alto_caja, ancho_util, alto_caja, fill=1, stroke=1)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica", 10)
    y_texto = y - 0.14 * inch
    p.drawString(margin + 0.15 * inch, y_texto, f"FECHA: {fecha_str}")
    p.drawCentredString(w / 2, y_texto, f"ORDEN #: Venta #{id_venta}")
    p.drawRightString(w - margin - 0.15 * inch, y_texto, "ENTREGA:")
    y -= alto_caja + 0.18 * inch

    # === ESTADO: verde si PAGADO, rojo si PENDIENTE ===
    estado = (venta_data.get("estado") or "PENDIENTE").upper()
    if estado == "PAGADA":
        estado_linea = "*** PAGADO - COMPROBANTE ***"
        p.setFillColor(_COLOR_VERDE)
    elif estado == "CANCELADA":
        estado_linea = "*** CANCELADA ***"
        p.setFillColor(HexColor("#6b7280"))
    else:
        estado_linea = "*** PENDIENTE DE PAGO ***"
        p.setFillColor(_COLOR_ROJO)
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(w / 2, y, estado_linea)
    p.setFillColor(HexColor("#000000"))
    y -= 0.45 * inch

    # === INFORMACION DEL CLIENTE / INFORMACION DEL VEHICULO (barra azul) ===
    y = _barra_azul(p, margin, y, ancho_util, 0.28 * inch, "INFORMACION DEL CLIENTE / INFORMACION DEL VEHICULO", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "CLIENTE")
    p.drawString(3.5 * inch, y, "VEHICULO")
    y -= 0.22 * inch
    p.setFont("Helvetica", 9)
    cliente = venta_data.get("cliente") or {}
    veh = venta_data.get("vehiculo") or {}
    p.drawString(margin, y, f"Nombre: {cliente.get('nombre') or '-'}")
    p.drawString(3.5 * inch, y, f"Marca: {veh.get('marca') or '-'}")
    y -= 0.2 * inch
    p.drawString(margin, y, f"Direccion: {cliente.get('direccion') or '-'}")
    p.drawString(3.5 * inch, y, f"Modelo: {veh.get('modelo') or '-'}")
    y -= 0.2 * inch
    anio_vin = f"{veh.get('anio') or '-'} {veh.get('vin') or ''}".strip()
    p.drawString(margin, y, f"Año / VIN: {anio_vin or '-'}")
    y -= 0.2 * inch
    p.drawString(margin, y, "KM: -")
    y -= 0.35 * inch

    # === MANO DE OBRA (barra azul) ===
    servicios = venta_data.get("servicios", [])
    y = _barra_azul(p, margin, y, ancho_util, 0.26 * inch, "MANO DE OBRA", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Descripcion")
    p.drawRightString(5.0 * inch, y, "COSTO")
    p.drawRightString(w - margin, y, "TOTAL")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    subtotal_mano = 0.0
    for s in servicios:
        desc = (s.get("descripcion") or "")[:50]
        sub = float(s.get("subtotal", 0) or 0)
        costo = float(s.get("precio_unitario", 0) or 0)
        subtotal_mano += sub
        p.drawString(margin, y, desc)
        p.drawRightString(5.0 * inch, y, f"${costo:.2f}")
        p.drawRightString(w - margin, y, f"${sub:.2f}")
        y -= 0.22 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Subtotal Mano de Obra:")
    p.drawRightString(w - margin, y, f"${subtotal_mano:.2f}")
    y -= 0.35 * inch

    # === PARTES (barra azul) ===
    partes = venta_data.get("partes", [])
    y = _barra_azul(p, margin, y, ancho_util, 0.26 * inch, "PARTES", size=10)
    y -= 0.12 * inch
    col_qty, col_punit, col_total = 4.0 * inch, 5.0 * inch, w - margin
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Descripcion")
    p.drawRightString(col_qty, y, "QTY")
    p.drawRightString(col_punit, y, "P.UNIT.")
    p.drawRightString(col_total, y, "TOTAL")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    subtotal_partes = 0.0
    for pt in partes:
        desc = (pt.get("descripcion") or "")[:50]
        cant = pt.get("cantidad", 0)
        pu = float(pt.get("subtotal", 0) or 0) / max(1, cant)
        sub = float(pt.get("subtotal", 0) or 0)
        subtotal_partes += sub
        p.drawString(margin, y, desc)
        p.drawRightString(col_qty, y, str(cant))
        p.drawRightString(col_punit, y, f"${pu:.2f}")
        p.drawRightString(col_total, y, f"${sub:.2f}")
        y -= 0.22 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Subtotal Partes:")
    p.drawRightString(w - margin, y, f"${subtotal_partes:.2f}")
    y -= 0.35 * inch

    # === COMENTARIOS (barra azul) ===
    y = _barra_azul(p, margin, y, ancho_util, 0.26 * inch, "COMENTARIOS", size=10)
    y -= 0.15 * inch
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(_COLOR_GRIS_SUAVE)
    p.drawString(margin, y, "(Sin comentarios)")
    p.setFillColor(HexColor("#000000"))
    y -= 0.5 * inch

    # === TOTALES (alineados a la derecha, bloque compacto) ===
    total = float(venta_data.get("total", 0) or 0)
    subtotal_gral = subtotal_mano + subtotal_partes
    requiere_factura = venta_data.get("requiere_factura", False)
    if requiere_factura and subtotal_gral > 0:
        impuesto = round(total - subtotal_gral, 2)
        tasa_imp = 8
    else:
        impuesto = 0.0
        tasa_imp = 0
    total_pagado = float(venta_data.get("total_pagado", 0) or 0)
    saldo = float(venta_data.get("saldo_pendiente", 0) or 0)

    # Bloque de totales alineado a la derecha
    x_label = w - margin - 2.5 * inch
    x_val = w - margin
    lh = 0.24 * inch

    p.setFont("Helvetica", 10)
    p.drawRightString(x_label, y, "TOTAL MANO DE OBRA")
    p.drawRightString(x_val, y, f"${subtotal_mano:.2f}")
    y -= lh
    p.drawRightString(x_label, y, "TOTAL PARTES:")
    p.drawRightString(x_val, y, f"${subtotal_partes:.2f}")
    y -= lh
    p.drawRightString(x_label, y, f"IMPUESTO ({tasa_imp}%):")
    p.drawRightString(x_val, y, f"${impuesto:.2f}")
    y -= lh
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(x_val, y, f"TOTAL: ${total:.2f}")
    y -= lh + 0.1 * inch
    p.setFont("Helvetica", 10)
    p.drawRightString(x_label, y, "Total pagado:")
    p.drawRightString(x_val, y, f"${total_pagado:.2f}")
    y -= lh
    p.drawRightString(x_label, y, "Saldo pendiente:")
    p.drawRightString(x_val, y, f"${saldo:.2f}")
    y -= 0.5 * inch

    # === PIE (gris suave, cursiva) ===
    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(_COLOR_GRIS_SUAVE)
    p.drawCentredString(w / 2, y, "Gracias por su preferencia")
    y -= 0.22 * inch
    p.drawCentredString(w / 2, y, "Conserve este documento como comprobante")

    p.save()
    buf.seek(0)
    return buf.read()


@router.get("/{id_venta}/ticket")
def descargar_ticket(
    id_venta: int,
    tipo: str = Query("nota", description="nota o factura"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    cliente = db.query(Cliente).filter(Cliente.id_cliente == venta.id_cliente).first() if venta.id_cliente else None
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == venta.id_vehiculo).first() if venta.id_vehiculo else None
    total_pagado = float(db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(Pago.id_venta == venta.id_venta).scalar() or 0)
    detalles = db.query(DetalleVenta).filter(DetalleVenta.id_venta == id_venta).all()
    total = float(venta.total)
    saldo = max(0, total - total_pagado)
    estado_val = venta.estado.value if hasattr(venta.estado, "value") else str(venta.estado)
    def _d(r):
        cant = r.cantidad or 1
        sub = float(r.subtotal or 0)
        return {"descripcion": r.descripcion, "cantidad": cant, "precio_unitario": float(r.precio_unitario or 0), "subtotal": sub}
    servicios = [_d(d) for d in detalles if (d.tipo.value if hasattr(d.tipo, "value") else str(d.tipo)) == "SERVICIO"]
    partes = [_d(d) for d in detalles if (d.tipo.value if hasattr(d.tipo, "value") else str(d.tipo)) == "PRODUCTO"]
    venta_data = {
        "id_venta": venta.id_venta,
        "fecha": venta.fecha.isoformat() if venta.fecha else None,
        "estado": estado_val,
        "total": total,
        "total_pagado": total_pagado,
        "saldo_pendiente": saldo,
        "requiere_factura": bool(getattr(venta, "requiere_factura", False)),
        "cliente": {"nombre": cliente.nombre, "direccion": cliente.direccion} if cliente else {},
        "vehiculo": {"marca": vehiculo.marca, "modelo": vehiculo.modelo, "anio": vehiculo.anio, "vin": vehiculo.vin} if vehiculo else {},
        "servicios": servicios,
        "partes": partes,
    }
    pdf_bytes = _generar_pdf_ticket(venta_data, tipo, app_name=settings.APP_NAME.replace(" API", ""))
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=venta-{id_venta}-{tipo}.pdf"},
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
def crear_venta(
    data: VentaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO"))
):
    # 1️⃣ Validación mínima
    if not data.detalles or len(data.detalles) == 0:
        raise HTTPException(
            status_code=400,
            detail="La venta debe tener al menos un detalle"
        )

    # 2️⃣ Calcular subtotal
    subtotal = sum(item.cantidad * item.precio_unitario for item in data.detalles)
    total_venta = round(subtotal * 1.08, 2) if getattr(data, "requiere_factura", False) else round(subtotal, 2)

    venta = Venta(
        id_cliente=data.id_cliente,
        id_vehiculo=data.id_vehiculo,
        id_usuario=current_user.id_usuario,
        total=total_venta,
        requiere_factura=getattr(data, "requiere_factura", False)
    )

    db.add(venta)
    db.commit()
    db.refresh(venta)

    # 3️⃣ Crear detalles
    for item in data.detalles:
        subtotal = item.cantidad * item.precio_unitario

        detalle = DetalleVenta(
            id_venta=venta.id_venta,
            tipo=item.tipo,
            id_item=item.id_item,
            descripcion=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=subtotal
        )

        db.add(detalle)

    db.commit()

    return {
        "id_venta": venta.id_venta,
        "total": float(venta.total),
        "estado": venta.estado
    }


class CancelarVentaBody(BaseModel):
    motivo: str = Field(..., min_length=5, description="Motivo obligatorio de la cancelación")


@router.post("/{id_venta}/cancelar")
def cancelar_venta(
    id_venta: int,
    body: CancelarVentaBody,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "CAJA"))
):
    venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == "CANCELADA":
        raise HTTPException(status_code=400, detail="La venta ya está cancelada")
    venta.estado = "CANCELADA"
    venta.motivo_cancelacion = body.motivo.strip()
    db.commit()
    return {"id_venta": id_venta, "estado": "CANCELADA"}
