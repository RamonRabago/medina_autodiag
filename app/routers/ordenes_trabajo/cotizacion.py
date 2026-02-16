"""Generación de cotización PDF para órdenes de trabajo."""
import logging
from pathlib import Path
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from app.database import get_db
from app.models.orden_trabajo import OrdenTrabajo
from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
from app.utils.roles import require_roles
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_COLOR_NARANJA = HexColor("#ea580c")
_COLOR_NARANJA_CLARO = HexColor("#ffedd5")
_COLOR_GRIS_SUAVE = HexColor("#9ca3af")

_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo_medina_autodiag.png"

# Límite inferior antes de nueva página (reportlab: y=0 abajo)
_Y_MIN = 1.5 * 72


def _wrap_text(p, text, max_width, font="Helvetica", size=9):
    """Divide texto en líneas que caben en max_width."""
    if not text or not str(text).strip():
        return [""]
    text = str(text).strip()
    words = text.split()
    lines = []
    current = []
    for w in words:
        test = " ".join(current + [w]) if current else w
        if p.stringWidth(test, font, size) <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = []
            if p.stringWidth(w, font, size) <= max_width:
                current = [w]
            else:
                while w:
                    for k in range(len(w), 0, -1):
                        if p.stringWidth(w[:k], font, size) <= max_width:
                            lines.append(w[:k])
                            w = w[k:]
                            break
                    else:
                        lines.append(w[:25])
                        w = w[25:]
    if current:
        lines.append(" ".join(current))
    return lines if lines else [""]


def _barra_naranja(p, x, y, ancho, alto, texto, font="Helvetica-Bold", size=10):
    """Dibuja barra naranja con texto blanco centrado (cotización)."""
    p.setFillColor(_COLOR_NARANJA)
    p.rect(x, y - alto, ancho, alto, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(font, size)
    centro_x = x + ancho / 2
    texto_y = y - alto + 0.06 * inch
    p.drawCentredString(centro_x, texto_y, texto)
    p.setFillColor(HexColor("#000000"))
    return y - alto


def _generar_pdf_cotizacion(orden_data: dict, app_name: str = "MedinaAutoDiag") -> bytes:
    """Genera PDF de cotización: propuesta formal para el cliente."""
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    margin = inch
    ancho_util = w - 2 * margin
    y = h - margin

    # Logo centrado (donde iba el nombre de la app)
    logo_w, logo_h = 1.5 * inch, 0.6 * inch
    if _LOGO_PATH.exists():
        p.drawImage(str(_LOGO_PATH), w / 2 - logo_w / 2, y - logo_h, width=logo_w, height=logo_h)
    y -= logo_h + 0.08 * inch
    p.setFont("Helvetica", 12)
    p.drawCentredString(w / 2, y, "COTIZACIÓN")
    y -= 0.2 * inch
    p.setFont("Helvetica", 10)
    p.drawCentredString(w / 2, y, "SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ")
    y -= 0.3 * inch
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.5)
    p.line(margin, y, w - margin, y)
    y -= 0.35 * inch

    numero_orden = orden_data.get("numero_orden", "")
    fecha_str = orden_data.get("fecha_ingreso", "")
    if fecha_str:
        fecha_str = str(fecha_str)[:19].replace("T", " ")
    else:
        fecha_str = "-"

    alto_caja = 0.36 * inch
    p.setFillColor(_COLOR_NARANJA_CLARO)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.25)
    p.rect(margin, y - alto_caja, ancho_util, alto_caja, fill=1, stroke=1)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica", 10)
    y_texto = y - 0.14 * inch
    p.drawString(margin + 0.15 * inch, y_texto, f"FECHA: {fecha_str}")
    p.drawCentredString(w / 2, y_texto, f"ORDEN: {numero_orden}")
    p.drawRightString(w - margin - 0.15 * inch, y_texto, "PROPUESTA")
    y -= alto_caja + 0.15 * inch

    vigencia = orden_data.get("fecha_vigencia_cotizacion")
    p.setFont("Helvetica", 9)
    p.setFillColor(HexColor("#64748b"))
    if vigencia:
        try:
            from datetime import datetime as dt
            if isinstance(vigencia, str) and len(vigencia) >= 10:
                d = dt.strptime(vigencia[:10], "%Y-%m-%d")
                p.drawCentredString(w / 2, y, f"Válida hasta: {d.strftime('%d/%m/%Y')}")
                y -= 0.2 * inch
        except (ValueError, TypeError):
            pass
    p.drawCentredString(w / 2, y, "Esta cotización es una propuesta. Los precios pueden variar según disponibilidad.")
    p.setFillColor(HexColor("#000000"))
    y -= 0.45 * inch

    # --- CLIENTE Y VEHÍCULO: dos cajas separadas con más espacio ---
    col_width = (ancho_util - 0.25 * inch) / 2
    box_height = 1.5 * inch
    line_h = 0.24 * inch

    # Caja CLIENTE (izquierda)
    p.setFillColor(HexColor("#fafafa"))
    p.setStrokeColor(HexColor("#e5e7eb"))
    p.setLineWidth(0.25)
    p.rect(margin, y - box_height, col_width, box_height, fill=1, stroke=1)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin + 0.15 * inch, y - 0.28 * inch, "CLIENTE")
    p.setFont("Helvetica", 9)
    cliente = orden_data.get("cliente") or {}
    max_w_cli = col_width - 0.35 * inch
    yc = y - 0.52 * inch
    nombre = (cliente.get("nombre") or "-").strip()
    # Nombre puede ocupar 2 líneas si es largo
    nom_lines = _wrap_text(p, nombre, max_w_cli - 0.75 * inch, "Helvetica", 9)
    for i, ln in enumerate(nom_lines[:2]):
        pref = "Nombre: " if i == 0 else ""
        p.drawString(margin + 0.15 * inch, yc, pref + (ln or "-")[:45])
        yc -= line_h
    p.drawString(margin + 0.15 * inch, yc, f"Tel: {(cliente.get('telefono') or '-')[:30]}")
    yc -= line_h
    p.drawString(margin + 0.15 * inch, yc, f"Email: {(cliente.get('email') or '-')[:38]}")
    dir_cli = (cliente.get("direccion") or "").strip()
    if dir_cli:
        yc -= line_h
        for dln in _wrap_text(p, dir_cli, max_w_cli - 0.1 * inch, "Helvetica", 9)[:2]:
            p.drawString(margin + 0.15 * inch, yc, (dln or "")[:50])
            yc -= 0.2 * inch

    # Caja VEHÍCULO (derecha)
    x_veh = margin + col_width + 0.25 * inch
    p.setFillColor(HexColor("#fafafa"))
    p.rect(x_veh, y - box_height, col_width, box_height, fill=1, stroke=1)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(x_veh + 0.15 * inch, y - 0.28 * inch, "VEHÍCULO")
    p.setFont("Helvetica", 9)
    veh = orden_data.get("vehiculo") or {}
    yv = y - 0.52 * inch
    p.drawString(x_veh + 0.15 * inch, yv, f"Marca: {veh.get('marca') or '-'}")
    yv -= line_h
    p.drawString(x_veh + 0.15 * inch, yv, f"Modelo: {veh.get('modelo') or '-'}")
    yv -= line_h
    anio_vin = f"{veh.get('anio') or '-'}  {veh.get('vin') or ''}".strip()
    p.drawString(x_veh + 0.15 * inch, yv, f"Año/VIN: {(anio_vin or '-')[:38]}")
    yv -= line_h
    p.drawString(x_veh + 0.15 * inch, yv, f"Kilometraje: {orden_data.get('kilometraje') if orden_data.get('kilometraje') is not None else '-'}")

    y -= box_height + 0.4 * inch

    diagnostico = (orden_data.get("diagnostico_inicial") or "").strip()
    if diagnostico:
        y = _barra_naranja(p, margin, y, ancho_util, 0.26 * inch, "DIAGNÓSTICO / OBSERVACIONES", size=10)
        y -= 0.15 * inch
        p.setFont("Helvetica", 9)
        max_w_diag = ancho_util - 0.2 * inch
        for line in diagnostico.split("\n")[:6]:
            line = (line or "").strip()
            if line:
                for ln in _wrap_text(p, line, max_w_diag, "Helvetica", 9)[:2]:
                    p.drawString(margin, y, (ln or "")[:95])
                    y -= 0.2 * inch
        obs_cli = (orden_data.get("observaciones_cliente") or "").strip()
        if obs_cli:
            y -= 0.08 * inch
            p.setFont("Helvetica-Oblique", 9)
            p.drawString(margin, y, "Cliente reporta:")
            y -= 0.22 * inch
            p.setFont("Helvetica", 9)
            for line in obs_cli.split("\n")[:4]:
                line = (line or "").strip()
                if line:
                    for ln in _wrap_text(p, line, max_w_diag, "Helvetica", 9)[:2]:
                        p.drawString(margin, y, (ln or "")[:95])
                        y -= 0.2 * inch
        y -= 0.2 * inch

    servicios = orden_data.get("servicios", [])
    y = _barra_naranja(p, margin, y, ancho_util, 0.26 * inch, "MANO DE OBRA", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Descripción")
    p.drawRightString(5.0 * inch, y, "CANT.")
    p.drawRightString(w - margin, y, "TOTAL")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    subtotal_mano = 0.0
    for s in servicios:
        desc = (s.get("descripcion") or "")[:55]
        sub = float(s.get("subtotal", 0) or 0)
        cant = s.get("cantidad", 1)
        subtotal_mano += sub
        p.drawString(margin, y, desc)
        p.drawRightString(5.0 * inch, y, str(cant))
        p.drawRightString(w - margin, y, f"${sub:.2f}")
        y -= 0.22 * inch
    if subtotal_mano > 0:
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin, y, "Subtotal Mano de Obra:")
        p.drawRightString(w - margin, y, f"${subtotal_mano:.2f}")
        y -= 0.25 * inch
    y -= 0.2 * inch

    partes = orden_data.get("partes", [])
    y = _barra_naranja(p, margin, y, ancho_util, 0.26 * inch, "REFACCIONES", size=10)
    y -= 0.12 * inch
    col_desc_max = 3.8 * inch
    col_qty = 4.5 * inch
    col_punit = 5.5 * inch
    col_total = w - margin
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Descripción")
    p.drawRightString(col_qty, y, "CANT.")
    p.drawRightString(col_punit, y, "P.UNIT.")
    p.drawRightString(col_total, y, "TOTAL")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    subtotal_partes = 0.0
    row_h_base = 0.18 * inch
    for pt in partes:
        if y < _Y_MIN:
            p.showPage()
            y = h - margin - 0.3 * inch
            p.setFont("Helvetica-Bold", 9)
            p.drawString(margin, y, "(Refacciones - continuación)")
            y -= 0.25 * inch
        desc = (pt.get("descripcion") or "").strip()
        cant = pt.get("cantidad", 1)
        try:
            cant_num = max(0.001, float(cant)) if cant is not None else 1
        except (TypeError, ValueError):
            cant_num = 1
        sub = float(pt.get("subtotal", 0) or 0)
        pu = sub / cant_num if cant_num else 0
        subtotal_partes += sub
        desc_lines = _wrap_text(p, desc, col_desc_max - 0.2 * inch, "Helvetica", 9)
        if len(desc_lines) > 1:
            for i, dl in enumerate(desc_lines):
                p.drawString(margin, y, (dl or "")[:55])
                if i == 0:
                    p.drawRightString(col_qty, y, str(cant) if isinstance(cant, int) else f"{cant:.3g}")
                    p.drawRightString(col_punit, y, f"${pu:.2f}")
                    p.drawRightString(col_total, y, f"${sub:.2f}")
                y -= row_h_base
        else:
            p.drawString(margin, y, (desc or "-")[:55])
            p.drawRightString(col_qty, y, str(cant) if isinstance(cant, int) else f"{cant:.3g}")
            p.drawRightString(col_punit, y, f"${pu:.2f}")
            p.drawRightString(col_total, y, f"${sub:.2f}")
            y -= 0.22 * inch
    if subtotal_partes > 0:
        p.setFont("Helvetica-Bold", 9)
        p.drawString(margin, y, "Subtotal Refacciones:")
        p.drawRightString(w - margin, y, f"${subtotal_partes:.2f}")
        y -= 0.25 * inch
    y -= 0.2 * inch

    descuento = float(orden_data.get("descuento", 0) or 0)
    total = float(orden_data.get("total", 0) or 0)

    x_label = w - margin - 2.5 * inch
    x_val = w - margin
    lh = 0.24 * inch

    p.setFont("Helvetica", 10)
    p.drawRightString(x_label, y, "Subtotal Mano de Obra:")
    p.drawRightString(x_val, y, f"${subtotal_mano:.2f}")
    y -= lh
    p.drawRightString(x_label, y, "Subtotal Refacciones:")
    p.drawRightString(x_val, y, f"${subtotal_partes:.2f}")
    y -= lh
    if descuento > 0:
        p.drawRightString(x_label, y, "Descuento:")
        p.drawRightString(x_val, y, f"-${descuento:.2f}")
        y -= lh
    p.setFont("Helvetica-Bold", 12)
    p.drawRightString(x_val, y, f"TOTAL: ${total:.2f}")
    y -= lh + 0.3 * inch

    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(_COLOR_GRIS_SUAVE)
    p.drawCentredString(w / 2, y, "Gracias por su preferencia")
    y -= 0.22 * inch
    p.drawCentredString(w / 2, y, "Conserve esta cotización para su referencia")
    y -= 0.2 * inch
    p.setFont("Helvetica", 8)
    p.drawCentredString(w / 2, y, "Al autorizar, se procederá con el trabajo y compra de refacciones según disponibilidad.")

    p.save()
    buf.seek(0)
    return buf.read()


@router.get("/{orden_id}/cotizacion")
def descargar_cotizacion(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA", "TECNICO")),
):
    """Genera y descarga la cotización en PDF para enviar al cliente."""
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.cliente),
            joinedload(OrdenTrabajo.vehiculo),
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver esta orden")

    try:
        cliente_dict = {}
        if orden.cliente:
            cliente_dict = {
                "nombre": orden.cliente.nombre,
                "telefono": orden.cliente.telefono or "",
                "email": orden.cliente.email or "",
                "direccion": orden.cliente.direccion or "",
            }
        vehiculo_dict = {}
        if orden.vehiculo:
            vehiculo_dict = {
                "marca": orden.vehiculo.marca or "",
                "modelo": orden.vehiculo.modelo or "",
                "anio": orden.vehiculo.anio or "",
                "vin": orden.vehiculo.vin or "",
            }

        def _serv(d):
            return {
                "descripcion": d.descripcion or f"Servicio #{d.servicio_id}",
                "cantidad": d.cantidad or 1,
                "precio_unitario": float(d.precio_unitario or 0),
                "subtotal": float(d.subtotal or 0),
            }

        def _rep(d):
            if d.repuesto:
                desc = d.repuesto.nombre
                if d.repuesto.codigo:
                    desc = f"[{d.repuesto.codigo}] {desc}"
            else:
                desc = (d.descripcion_libre or "").strip() or f"Repuesto #{d.repuesto_id or 'N/A'}"
            return {
                "descripcion": desc,
                "cantidad": float(d.cantidad or 1),
                "precio_unitario": float(d.precio_unitario or 0),
                "subtotal": float(d.subtotal or 0),
            }

        vigencia_str = None
        if getattr(orden, "fecha_vigencia_cotizacion", None):
            fv = orden.fecha_vigencia_cotizacion
            vigencia_str = fv.isoformat() if hasattr(fv, "isoformat") else str(fv)[:10]

        orden_data = {
            "numero_orden": orden.numero_orden,
            "fecha_ingreso": orden.fecha_ingreso.isoformat() if orden.fecha_ingreso else None,
            "fecha_vigencia_cotizacion": vigencia_str,
            "kilometraje": orden.kilometraje,
            "diagnostico_inicial": orden.diagnostico_inicial,
            "observaciones_cliente": orden.observaciones_cliente,
            "descuento": float(orden.descuento or 0),
            "total": float(orden.total or 0),
            "cliente": cliente_dict,
            "vehiculo": vehiculo_dict,
            "servicios": [_serv(d) for d in (orden.detalles_servicio or [])],
            "partes": [_rep(d) for d in (orden.detalles_repuesto or [])],
        }

        app_name = settings.APP_NAME.replace(" API", "")
        pdf_bytes = _generar_pdf_cotizacion(orden_data, app_name=app_name)
        filename = f"cotizacion-{orden.numero_orden.replace(' ', '-')}.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al generar cotización PDF para orden %s", orden_id)
        raise HTTPException(status_code=500, detail=str(e))


# --- Hoja de trabajo para técnico (verde) ---
_COLOR_VERDE = HexColor("#16a34a")
_COLOR_VERDE_CLARO = HexColor("#dcfce7")


def _barra_verde(p, x, y, ancho, alto, texto, font="Helvetica-Bold", size=10):
    """Dibuja barra verde con texto blanco centrado (hoja técnico)."""
    p.setFillColor(_COLOR_VERDE)
    p.rect(x, y - alto, ancho, alto, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(font, size)
    centro_x = x + ancho / 2
    texto_y = y - alto + 0.06 * inch
    p.drawCentredString(centro_x, texto_y, texto)
    p.setFillColor(HexColor("#000000"))
    return y - alto


def _generar_pdf_hoja_tecnico(orden_data: dict, app_name: str = "MedinaAutoDiag") -> bytes:
    """Genera PDF hoja de trabajo para el técnico (verde)."""
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    margin = inch
    ancho_util = w - 2 * margin
    y = h - margin

    # Logo centrado (donde iba el nombre de la app)
    logo_w, logo_h = 1.5 * inch, 0.6 * inch
    if _LOGO_PATH.exists():
        p.drawImage(str(_LOGO_PATH), w / 2 - logo_w / 2, y - logo_h, width=logo_w, height=logo_h)
    y -= logo_h + 0.08 * inch
    p.setFont("Helvetica", 12)
    p.drawCentredString(w / 2, y, "HOJA DE TRABAJO")
    y -= 0.2 * inch
    p.setFont("Helvetica", 10)
    p.drawCentredString(w / 2, y, "SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ")
    y -= 0.3 * inch
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.5)
    p.line(margin, y, w - margin, y)
    y -= 0.35 * inch

    numero_orden = orden_data.get("numero_orden", "")
    fecha_str = orden_data.get("fecha_ingreso", "")
    if fecha_str:
        fecha_str = str(fecha_str)[:19].replace("T", " ")
    else:
        fecha_str = "-"

    alto_caja = 0.36 * inch
    p.setFillColor(_COLOR_VERDE_CLARO)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.25)
    p.rect(margin, y - alto_caja, ancho_util, alto_caja, fill=1, stroke=1)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica", 10)
    y_texto = y - 0.14 * inch
    p.drawString(margin + 0.15 * inch, y_texto, f"FECHA: {fecha_str}")
    p.drawCentredString(w / 2, y_texto, f"ORDEN: {numero_orden}")
    tecnico = orden_data.get("tecnico_nombre") or "-"
    p.drawRightString(w - margin - 0.15 * inch, y_texto, f"TÉCNICO: {tecnico[:20]}")
    y -= alto_caja + 0.25 * inch

    y = _barra_verde(p, margin, y, ancho_util, 0.28 * inch, "CLIENTE / VEHÍCULO", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "CLIENTE")
    p.drawString(3.5 * inch, y, "VEHÍCULO")
    y -= 0.22 * inch
    p.setFont("Helvetica", 9)
    cliente = orden_data.get("cliente") or {}
    veh = orden_data.get("vehiculo") or {}
    p.drawString(margin, y, f"Nombre: {cliente.get('nombre') or '-'}")
    p.drawString(3.5 * inch, y, f"Marca: {veh.get('marca') or '-'}")
    y -= 0.2 * inch
    p.drawString(margin, y, f"Tel: {cliente.get('telefono') or '-'}")
    p.drawString(3.5 * inch, y, f"Modelo: {veh.get('modelo') or '-'}")
    y -= 0.2 * inch
    anio_vin = f"{veh.get('anio') or '-'}  {veh.get('vin') or ''}".strip()
    p.drawString(margin, y, f"Kilometraje: {orden_data.get('kilometraje') or '-'}")
    p.drawString(3.5 * inch, y, f"Año / VIN: {anio_vin or '-'}")
    y -= 0.35 * inch

    diagnostico = (orden_data.get("diagnostico_inicial") or "").strip()
    if diagnostico:
        y = _barra_verde(p, margin, y, ancho_util, 0.26 * inch, "DIAGNÓSTICO", size=10)
        y -= 0.15 * inch
        p.setFont("Helvetica", 9)
        for line in diagnostico.split("\n")[:6]:
            line = (line.strip())[:90]
            if line:
                p.drawString(margin, y, line)
                y -= 0.2 * inch
        obs_cli = (orden_data.get("observaciones_cliente") or "").strip()
        if obs_cli:
            y -= 0.1 * inch
            p.setFont("Helvetica-Oblique", 9)
            p.drawString(margin, y, "Cliente reporta:")
            y -= 0.2 * inch
            p.setFont("Helvetica", 9)
            for line in obs_cli.split("\n")[:4]:
                line = (line.strip())[:90]
                if line:
                    p.drawString(margin, y, line)
                    y -= 0.2 * inch
        y -= 0.25 * inch

    servicios = orden_data.get("servicios", [])
    y = _barra_verde(p, margin, y, ancho_util, 0.26 * inch, "SERVICIOS A REALIZAR", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Descripción")
    p.drawRightString(5.0 * inch, y, "CANT.")
    p.drawRightString(w - margin, y, "TOTAL")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    for s in servicios:
        desc = (s.get("descripcion") or "")[:55]
        cant = s.get("cantidad", 1)
        sub = float(s.get("subtotal", 0) or 0)
        p.drawString(margin, y, desc)
        p.drawRightString(5.0 * inch, y, str(cant))
        p.drawRightString(w - margin, y, f"${sub:.2f}")
        y -= 0.22 * inch
    y -= 0.2 * inch

    partes = orden_data.get("partes", [])
    y = _barra_verde(p, margin, y, ancho_util, 0.26 * inch, "REFACCIONES A USAR", size=10)
    y -= 0.12 * inch
    col_qty, col_total = 4.0 * inch, w - margin
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Descripción")
    p.drawRightString(col_qty, y, "CANT.")
    p.drawRightString(col_total, y, "TOTAL")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    for pt in partes:
        desc = (pt.get("descripcion") or "")[:55]
        cant = pt.get("cantidad", 1)
        sub = float(pt.get("subtotal", 0) or 0)
        p.drawString(margin, y, desc)
        p.drawRightString(col_qty, y, str(cant) if isinstance(cant, int) else f"{cant:.3g}")
        p.drawRightString(col_total, y, f"${sub:.2f}")
        y -= 0.22 * inch
    y -= 0.3 * inch

    p.setFont("Helvetica-Bold", 10)
    p.drawRightString(w - margin, y, f"TOTAL: ${float(orden_data.get('total', 0) or 0):.2f}")
    y -= 0.4 * inch

    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(_COLOR_GRIS_SUAVE)
    p.drawCentredString(w / 2, y, "Documento para el técnico — Conserve durante el trabajo")

    p.save()
    buf.seek(0)
    return buf.read()


@router.get("/{orden_id}/hoja-tecnico")
def descargar_hoja_tecnico(
    orden_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA", "TECNICO")),
):
    """Genera y descarga la hoja de trabajo en PDF para el técnico (verde)."""
    orden = (
        db.query(OrdenTrabajo)
        .options(
            joinedload(OrdenTrabajo.cliente),
            joinedload(OrdenTrabajo.vehiculo),
            joinedload(OrdenTrabajo.tecnico),
            joinedload(OrdenTrabajo.detalles_servicio),
            joinedload(OrdenTrabajo.detalles_repuesto).joinedload(DetalleRepuestoOrden.repuesto),
        )
        .filter(OrdenTrabajo.id == orden_id)
        .first()
    )
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    if current_user.rol == "TECNICO" and orden.tecnico_id != current_user.id_usuario:
        raise HTTPException(status_code=403, detail="No tiene permiso para ver esta orden")

    try:
        cliente_dict = {}
        if orden.cliente:
            cliente_dict = {
                "nombre": orden.cliente.nombre,
                "telefono": orden.cliente.telefono or "",
            }
        vehiculo_dict = {}
        if orden.vehiculo:
            vehiculo_dict = {
                "marca": orden.vehiculo.marca or "",
                "modelo": orden.vehiculo.modelo or "",
                "anio": orden.vehiculo.anio or "",
                "vin": orden.vehiculo.vin or "",
            }
        tecnico_nombre = orden.tecnico.nombre if orden.tecnico else None

        def _serv(d):
            return {
                "descripcion": d.descripcion or f"Servicio #{d.servicio_id}",
                "cantidad": d.cantidad or 1,
                "subtotal": float(d.subtotal or 0),
            }

        def _rep(d):
            if d.repuesto:
                desc = d.repuesto.nombre
                if d.repuesto.codigo:
                    desc = f"[{d.repuesto.codigo}] {desc}"
            else:
                desc = (d.descripcion_libre or "").strip() or f"Repuesto #{d.repuesto_id or 'N/A'}"
            return {
                "descripcion": desc,
                "cantidad": float(d.cantidad or 1),
                "subtotal": float(d.subtotal or 0),
            }

        orden_data = {
            "numero_orden": orden.numero_orden,
            "fecha_ingreso": orden.fecha_ingreso.isoformat() if orden.fecha_ingreso else None,
            "fecha_vigencia_cotizacion": orden.fecha_vigencia_cotizacion.isoformat() if orden.fecha_vigencia_cotizacion else None,
            "kilometraje": orden.kilometraje,
            "diagnostico_inicial": orden.diagnostico_inicial,
            "observaciones_cliente": orden.observaciones_cliente,
            "total": float(orden.total or 0),
            "tecnico_nombre": tecnico_nombre,
            "cliente": cliente_dict,
            "vehiculo": vehiculo_dict,
            "servicios": [_serv(d) for d in (orden.detalles_servicio or [])],
            "partes": [_rep(d) for d in (orden.detalles_repuesto or [])],
        }

        app_name = settings.APP_NAME.replace(" API", "")
        pdf_bytes = _generar_pdf_hoja_tecnico(orden_data, app_name=app_name)
        filename = f"hoja-tecnico-{orden.numero_orden.replace(' ', '-')}.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al generar hoja técnico PDF para orden %s", orden_id)
        raise HTTPException(status_code=500, detail=str(e))
