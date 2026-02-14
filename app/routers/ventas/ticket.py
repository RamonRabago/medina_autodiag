"""Generación de tickets PDF para ventas."""
import logging
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
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
from app.utils.roles import require_roles
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

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
    """Genera PDF con formato: MANO DE OBRA, PARTES, info cliente/vehículo."""
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    margin = inch
    ancho_util = w - 2 * margin
    y = h - margin

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
        cant = pt.get("cantidad", 1)
        try:
            cant_num = max(1, int(float(cant))) if cant is not None else 1
        except (TypeError, ValueError):
            cant_num = 1
        sub = float(pt.get("subtotal", 0) or 0)
        pu = sub / cant_num if cant_num else 0
        subtotal_partes += sub
        p.drawString(margin, y, desc)
        p.drawRightString(col_qty, y, str(cant_num))
        p.drawRightString(col_punit, y, f"${pu:.2f}")
        p.drawRightString(col_total, y, f"${sub:.2f}")
        y -= 0.22 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Subtotal Partes:")
    p.drawRightString(w - margin, y, f"${subtotal_partes:.2f}")
    y -= 0.35 * inch

    y = _barra_azul(p, margin, y, ancho_util, 0.26 * inch, "COMENTARIOS", size=10)
    y -= 0.15 * inch
    p.setFont("Helvetica-Oblique", 9)
    comentarios = (venta_data.get("comentarios") or "").strip()
    if comentarios:
        p.setFillColor(HexColor("#000000"))
        p.setFont("Helvetica", 9)
        for line in comentarios.split("\n")[:6]:
            if line.strip():
                p.drawString(margin, y, (line.strip())[:80])
                y -= 0.2 * inch
    else:
        p.setFillColor(_COLOR_GRIS_SUAVE)
        p.drawString(margin, y, "(Sin comentarios)")
        p.setFillColor(HexColor("#000000"))
    y -= 0.4 * inch

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
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA", "TECNICO"))
):
    try:
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
            "comentarios": getattr(venta, "comentarios", None) or None,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al generar ticket PDF para venta %s", id_venta)
        raise HTTPException(status_code=500, detail=str(e))
