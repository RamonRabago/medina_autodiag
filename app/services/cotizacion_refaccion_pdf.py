"""PDF formal de cotización de refacción especial (ReportLab, estilo alineado a cotización OT)."""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.cliente import Cliente
from app.models.cotizacion_refaccion_especial import (
    CotizacionRefaccionEspecial,
    LineaCotizacionRefaccion,
    OpcionCompraLineaCotizacion,
)
from app.models.vehiculo import Vehiculo
from app.services.cotizacion_refaccion_calculo import costo_unitario_mxn_opcion, precio_sugerido_con_iva

_COLOR_NARANJA = HexColor("#ea580c")
_COLOR_NARANJA_CLARO = HexColor("#ffedd5")
_LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "static" / "logo_medina_autodiag.png"
_Y_MIN = 1.5 * 72


def _wrap_text(p, text, max_width, font="Helvetica", size=9):
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
    p.setFillColor(_COLOR_NARANJA)
    p.rect(x, y - alto, ancho, alto, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(font, size)
    p.drawCentredString(x + ancho / 2, y - alto + 0.06 * inch, texto)
    p.setFillColor(HexColor("#000000"))
    return y - alto


def _opcion_elegida(linea: LineaCotizacionRefaccion) -> Optional[OpcionCompraLineaCotizacion]:
    pref = [o for o in (linea.opciones or []) if o.es_preferida]
    if len(pref) == 1:
        return pref[0]
    if pref:
        return pref[0]
    if linea.opciones:
        return sorted(linea.opciones, key=lambda x: x.id)[0]
    return None


def _margen(cot: CotizacionRefaccionEspecial) -> Optional[Decimal]:
    if cot.margen_objetivo_pct is None:
        return None
    return Decimal(str(cot.margen_objetivo_pct))


def _tc_cot(cot: CotizacionRefaccionEspecial) -> Optional[Decimal]:
    if cot.tc_referencia_usd_mxn is None:
        return None
    return Decimal(str(cot.tc_referencia_usd_mxn))


def generar_pdf_cotizacion_refaccion(db: Session, cotizacion_id: int) -> tuple[bytes, str]:
    """
    Genera PDF. Retorna (bytes, nombre_archivo sugerido).
    """
    cot = (
        db.query(CotizacionRefaccionEspecial)
        .options(
            joinedload(CotizacionRefaccionEspecial.lineas).joinedload(LineaCotizacionRefaccion.opciones),
        )
        .filter(CotizacionRefaccionEspecial.id == cotizacion_id)
        .first()
    )
    if not cot:
        raise ValueError("Cotización no encontrada")

    cli = db.query(Cliente).filter(Cliente.id_cliente == cot.id_cliente).first()
    veh: Optional[Vehiculo] = None
    if cot.id_vehiculo:
        veh = db.query(Vehiculo).filter(Vehiculo.id_vehiculo == cot.id_vehiculo).first()

    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    margin = inch
    margin_top = 0.45 * inch
    ancho_util = w - 2 * margin
    y = h - margin_top

    logo_w, logo_h = 3.4 * inch, 0.6 * inch
    if _LOGO_PATH.exists():
        p.drawImage(str(_LOGO_PATH), w / 2 - logo_w / 2, y - logo_h, width=logo_w, height=logo_h)
    y -= logo_h + 0.18 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(w / 2, y, "COTIZACIÓN REFACCIÓN ESPECIAL")
    y -= 0.2 * inch
    p.setFont("Helvetica", 9)
    p.drawCentredString(w / 2, y, "Importación / piezas fuera de stock local")
    y -= 0.22 * inch
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.5)
    p.line(margin, y, w - margin, y)
    y -= 0.22 * inch

    fecha_str = "-"
    if cot.creado_en:
        fecha_str = cot.creado_en.strftime("%d/%m/%Y %H:%M")
    estado_str = cot.estado.value if hasattr(cot.estado, "value") else str(cot.estado)

    alto_caja = 0.36 * inch
    p.setFillColor(_COLOR_NARANJA_CLARO)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.25)
    p.rect(margin, y - alto_caja, ancho_util, alto_caja, fill=1, stroke=1)
    p.setFillColor(HexColor("#000000"))
    p.setFont("Helvetica", 10)
    y_texto = y - 0.14 * inch
    p.drawString(margin + 0.12 * inch, y_texto, f"FECHA: {fecha_str}")
    p.drawCentredString(w / 2, y_texto, f"FOLIO: {cot.numero}")
    p.drawRightString(w - margin - 0.12 * inch, y_texto, estado_str[:18])
    y -= alto_caja + 0.12 * inch

    p.setFont("Helvetica", 8)
    p.setFillColor(HexColor("#64748b"))
    p.drawCentredString(
        w / 2,
        y,
        "Propuesta informativa. Precios sujetos a disponibilidad y tipo de cambio al momento de compra.",
    )
    p.setFillColor(HexColor("#000000"))
    y -= 0.28 * inch

    col_width = (ancho_util - 0.2 * inch) / 2
    box_h = 1.25 * inch
    line_h = 0.22 * inch

    p.setFillColor(HexColor("#fafafa"))
    p.setStrokeColor(HexColor("#e5e7eb"))
    p.rect(margin, y - box_h, col_width, box_h, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin + 0.12 * inch, y - 0.26 * inch, "CLIENTE")
    p.setFont("Helvetica", 9)
    yc = y - 0.48 * inch
    if cli:
        for ln in _wrap_text(p, (cli.nombre or "-")[:80], col_width - 0.3 * inch, "Helvetica", 9)[:2]:
            p.drawString(margin + 0.12 * inch, yc, ln)
            yc -= line_h
        p.drawString(margin + 0.12 * inch, yc, f"Tel: {(cli.telefono or '-')[:32]}")
    else:
        p.drawString(margin + 0.12 * inch, yc, "—")

    x2 = margin + col_width + 0.2 * inch
    p.setFillColor(HexColor("#fafafa"))
    p.rect(x2, y - box_h, col_width, box_h, fill=1, stroke=1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(x2 + 0.12 * inch, y - 0.26 * inch, "VEHÍCULO (opcional)")
    p.setFont("Helvetica", 9)
    yv = y - 0.48 * inch
    if veh:
        p.drawString(x2 + 0.12 * inch, yv, f"{(veh.marca or '')} {(veh.modelo or '')} {(veh.anio or '')}".strip() or "-")
        yv -= line_h
        p.drawString(x2 + 0.12 * inch, yv, f"VIN: {(getattr(veh, 'vin', None) or '-')[:36]}")
    else:
        p.drawString(x2 + 0.12 * inch, yv, "No registrado en esta cotización")

    y -= box_h + 0.2 * inch

    if cot.tc_referencia_usd_mxn is not None:
        p.setFont("Helvetica", 9)
        p.drawString(margin, y, f"Tipo de cambio referencia USD→MXN: {cot.tc_referencia_usd_mxn}")
        y -= 0.22 * inch
    if cot.margen_objetivo_pct is not None:
        p.drawString(margin, y, f"Margen objetivo: {cot.margen_objetivo_pct} %")
        y -= 0.22 * inch

    notas_gen = (cot.notas_generales or "").strip()
    if notas_gen:
        y = _barra_naranja(p, margin, y, ancho_util, 0.24 * inch, "NOTAS", size=9)
        y -= 0.1 * inch
        p.setFont("Helvetica", 9)
        for ln in _wrap_text(p, notas_gen, ancho_util - 0.15 * inch, "Helvetica", 9)[:5]:
            p.drawString(margin, y, ln[:100])
            y -= 0.18 * inch
        y -= 0.08 * inch

    y = _barra_naranja(p, margin, y, ancho_util, 0.26 * inch, "PIEZAS Y PRECIO SUGERIDO", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 8)
    p.drawString(margin, y, "Descripción / posición")
    p.drawString(3.0 * inch, y, "Origen")
    p.drawRightString(4.35 * inch, y, "Cant.")
    p.drawRightString(5.35 * inch, y, "P.unit MXN")
    p.drawRightString(w - margin, y, "Total MXN")
    y -= 0.16 * inch
    p.setFont("Helvetica", 8)

    tc_c = _tc_cot(cot)
    margen = _margen(cot)
    iva_d = Decimal(str(settings.IVA_PORCENTAJE))
    suma_precios = Decimal("0")

    lineas_ord = sorted(cot.lineas or [], key=lambda x: x.n_linea)
    for linea in lineas_ord:
        if y < _Y_MIN:
            p.showPage()
            y = h - margin - 0.35 * inch
            p.setFont("Helvetica-Bold", 9)
            p.drawString(margin, y, f"{cot.numero} (continuación)")
            y -= 0.28 * inch

        op = _opcion_elegida(linea)
        desc = (linea.descripcion or "").strip()
        lado = (linea.posicion_lado or "").strip()
        if lado:
            desc = f"{desc} ({lado})"
        cant = Decimal(str(linea.cantidad or 1))

        origen = "—"
        punit_txt = "—"
        total_txt = "—"
        if op:
            origen = (op.origen_nombre or "")[:22]
            mon = op.moneda.value if hasattr(op.moneda, "value") else str(op.moneda)
            try:
                cu = costo_unitario_mxn_opcion(op, tc_c)
                ps = precio_sugerido_con_iva(cu, cant, margen, iva_d)
                suma_precios += ps
                punit_txt = f"${(ps / cant).quantize(Decimal('0.01'))}"
                total_txt = f"${ps}"
            except ValueError as e:
                punit_txt = str(e)[:28]

        for ln in _wrap_text(p, desc, 2.75 * inch, "Helvetica", 8)[:2]:
            p.drawString(margin, y, ln[:55])
            p.drawString(3.0 * inch, y, origen[:24])
            p.drawRightString(4.35 * inch, y, str(cant))
            p.drawRightString(5.35 * inch, y, punit_txt[:14])
            p.drawRightString(w - margin, y, total_txt[:14])
            y -= 0.16 * inch
        y -= 0.06 * inch

    y -= 0.1 * inch
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin, y, "TOTAL ESTIMADO (IVA incl.):")
    p.drawRightString(w - margin, y, f"${suma_precios.quantize(Decimal('0.01'))}")
    y -= 0.35 * inch

    p.setFont("Helvetica", 8)
    p.setFillColor(HexColor("#64748b"))
    ley = (
        f"IVA considerado al {settings.IVA_PORCENTAJE}%. Markup por defecto del sistema si no se indicó margen en la cotización. "
        "Los enlaces de compra y plazos son referencia interna del taller."
    )
    for ln in _wrap_text(p, ley, ancho_util, "Helvetica", 8)[:4]:
        p.drawString(margin, y, ln)
        y -= 0.14 * inch

    p.showPage()
    p.save()
    buf.seek(0)
    raw = buf.getvalue()
    safe_name = (cot.numero or str(cotizacion_id)).replace(" ", "_").replace("/", "-")
    return raw, f"cotizacion-refaccion-{safe_name}.pdf"
