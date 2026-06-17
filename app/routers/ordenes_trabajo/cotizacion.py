"""Generación de cotización PDF para órdenes de trabajo."""

import logging
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.detalle_orden import DetalleRepuestoOrden
from app.models.orden_trabajo import OrdenTrabajo
from app.utils.roles import require_roles

router = APIRouter()
logger = logging.getLogger(__name__)

_COLOR_ROJO = HexColor("#c8102e")
_COLOR_ROJO_OSCURO = HexColor("#9b0d24")
_COLOR_HEADER_BG = HexColor("#2d2d2d")
_COLOR_GRIS_BORDE = HexColor("#d1d5db")
_COLOR_GRIS_SUAVE = HexColor("#6b7280")
_COLOR_GRIS_CLARO = HexColor("#f9fafb")

_LOGO_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "logo_medina_autodiag.png"

# Límite inferior antes de nueva página (reportlab: y=0 abajo)
_Y_MIN = 1.15 * 72

_COTIZACION_VIGENCIA_DEFAULT = "7 días naturales"

# Filas mínimas de relleno en tablas (compacto)
_TABLA_MIN_FILAS = 2
# Separación vertical barra roja → encabezados DESCRIPCIÓN / CANT. / …
_TABLA_GAP_BARRA_ENCABEZADO = 0.18 * inch

_TALLER_NOMBRE_COMERCIAL = "Medina AutoDiag"
_TALLER_TELEFONO = "868 114 1865"
_TALLER_WHATSAPP = "868 394 5536"
_TALLER_DIRECCION = "Ave. Lauro Villar #930A Col. Las Palmas C.P. 87420 Matamoros, Tamps., México"
_TALLER_CORREO = "recepcion@medinamedinaautodiag.com"


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


def _ensure_y(p, y, needed, h, margin):
    """Salta de página si no hay espacio vertical suficiente."""
    if y - needed < _Y_MIN:
        p.showPage()
        return h - margin - 0.3 * inch
    return y


def _draw_wrapped_block(p, text, x, y, max_width, font="Helvetica", size=9, line_h=0.17 * inch):
    """Dibuja párrafo con wrap; retorna nueva posición y."""
    p.setFont(font, size)
    for ln in _wrap_text(p, text, max_width, font, size):
        p.drawString(x, y, ln)
        y -= line_h
    return y


def _format_vigencia_fecha(vigencia) -> str | None:
    """Formatea fecha de vigencia a DD/MM/YYYY si es parseable."""
    if not vigencia:
        return None
    try:
        from datetime import datetime as dt

        if isinstance(vigencia, str) and len(vigencia) >= 10:
            d = dt.strptime(vigencia[:10], "%Y-%m-%d")
            return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        pass
    return None


def _format_fecha_ingreso(fecha_str) -> str:
    if not fecha_str:
        return "-"
    raw = str(fecha_str).strip()
    try:
        from datetime import datetime as dt

        if "T" in raw:
            d = dt.fromisoformat(raw.replace("Z", "+00:00")[:19])
            return d.strftime("%d/%m/%Y %H:%M")
        if len(raw) >= 10:
            d = dt.strptime(raw[:10], "%Y-%m-%d")
            return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        pass
    return raw[:19].replace("T", " ")


def _texto_vigencia_metadata(vigencia) -> str:
    fmt = _format_vigencia_fecha(vigencia)
    if fmt:
        return f"hasta {fmt}"
    return _COTIZACION_VIGENCIA_DEFAULT


def _comentarios_compactos(diagnostico: str, observaciones: str) -> str:
    d = (diagnostico or "").strip()
    o = (observaciones or "").strip()
    if d and o and d.lower() == o.lower():
        return d
    partes = []
    if d:
        partes.append(d)
    if o and o != d:
        partes.append(o)
    return "\n".join(partes) if partes else "-"


def _barra_roja(p, x, y, ancho, alto, texto, font="Helvetica-Bold", size=9):
    """Barra roja con texto blanco (secciones cotización compacta)."""
    p.setFillColor(_COLOR_ROJO)
    p.rect(x, y - alto, ancho, alto, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont(font, size)
    p.drawString(x + 0.08 * inch, y - alto + 0.055 * inch, texto)
    p.setFillColor(HexColor("#000000"))
    return y - alto


def _barra_header_negra(p, x, y, ancho, alto, texto, size=8):
    p.setFillColor(_COLOR_HEADER_BG)
    p.rect(x, y - alto, ancho, alto, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Helvetica-Bold", size)
    p.drawString(x + 0.08 * inch, y - alto + 0.05 * inch, texto)
    p.setFillColor(HexColor("#000000"))
    return y - alto


def _draw_header_compacto(p, w, y, margin, ancho_util):
    """Logo izquierda, título COTIZACIÓN derecha, línea roja."""
    logo_w, logo_h = 2.35 * inch, 0.48 * inch
    if _LOGO_PATH.exists():
        p.drawImage(str(_LOGO_PATH), margin, y - logo_h, width=logo_w, height=logo_h, mask="auto")
    title_x = w - margin
    p.setFont("Helvetica-Bold", 20)
    p.drawRightString(title_x, y - 0.22 * inch, "COTIZACIÓN")
    p.setFont("Helvetica", 9)
    p.drawRightString(title_x, y - 0.42 * inch, "SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ")
    y -= logo_h + 0.12 * inch
    p.setStrokeColor(_COLOR_ROJO)
    p.setLineWidth(2)
    p.line(margin, y, w - margin, y)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.5)
    return y - 0.14 * inch


def _draw_metadata_bar(p, w, y, margin, fecha_str, numero_orden, vigencia_meta):
    p.setFont("Helvetica-Bold", 8)
    p.drawString(margin, y, "FECHA:")
    p.setFont("Helvetica", 8)
    x = margin + 0.42 * inch
    p.drawString(x, y, fecha_str)
    mid = w / 2 - 0.55 * inch
    p.setFont("Helvetica-Bold", 8)
    p.drawString(mid, y, "ORDEN:")
    p.setFont("Helvetica", 8)
    p.drawString(mid + 0.48 * inch, y, numero_orden or "-")
    rx = w - margin - 2.0 * inch
    p.setFont("Helvetica-Bold", 8)
    p.drawString(rx, y, "VIGENCIA:")
    p.setFont("Helvetica", 8)
    p.drawString(rx + 0.62 * inch, y, vigencia_meta)
    return y - 0.22 * inch


def _draw_caja_datos(p, x, y, ancho, titulo, lineas: list[tuple[str, str]], *, body_h=None):
    """Recuadro datos cliente/vehículo con encabezado oscuro."""
    line_h = 0.17 * inch
    if body_h is None:
        body_h = max(0.55 * inch, len(lineas) * line_h + 0.14 * inch)
    header_h = 0.22 * inch
    total_h = header_h + body_h
    p.setStrokeColor(_COLOR_GRIS_BORDE)
    p.setLineWidth(0.5)
    p.setFillColor(HexColor("#ffffff"))
    p.rect(x, y - total_h, ancho, total_h, fill=1, stroke=1)
    _barra_header_negra(p, x, y, ancho, header_h, titulo, size=7.5)
    p.setFont("Helvetica", 7.5)
    yy = y - header_h - 0.14 * inch
    for label, valor in lineas:
        p.setFillColor(_COLOR_GRIS_SUAVE)
        p.drawString(x + 0.08 * inch, yy, f"{label}:")
        p.setFillColor(HexColor("#000000"))
        p.drawString(x + 0.72 * inch, yy, (valor or "-")[:42])
        yy -= line_h
    return y - total_h


def _cols_tabla(w, margin):
    """Columnas con zonas fijas a lo ancho de la hoja (encabezados legibles y separados)."""
    table_right = w - margin - 0.05 * inch
    desc_x = margin + 0.08 * inch
    # Posiciones desde el borde izquierdo de la página (letter): zonas visuales claras
    cant_zone = 4.05 * inch
    punit_zone = 5.35 * inch
    total_zone = 6.60 * inch
    cant_end = 5.05 * inch
    punit_end = 6.35 * inch

    return {
        "desc": desc_x,
        "desc_max": cant_zone - desc_x - 0.06 * inch,
        "cant": cant_end,
        "punit": punit_end,
        "total": table_right,
        "cant_left": cant_zone,
        "cant_w": cant_end - cant_zone,
        "punit_left": punit_zone,
        "punit_w": punit_end - punit_zone,
        "total_left": total_zone,
        "total_w": table_right - total_zone,
    }


def _draw_header_en_celda(p, x_left, width, text, y, *, align="center", font="Helvetica-Bold", size=7.5):
    """Dibuja encabezado de columna centrado o alineado dentro de su celda."""
    p.setFont(font, size)
    tw = p.stringWidth(text, font, size)
    if align == "right":
        x = x_left + width - tw
    elif align == "center":
        x = x_left + max(0, (width - tw) / 2)
    else:
        x = x_left
    p.drawString(x, y, text)


def _draw_tabla_encabezado(p, y, cols, margin, w):
    # Encabezados alineados al inicio de cada zona (lectura horizontal clara)
    _draw_header_en_celda(p, cols["desc"], cols["desc_max"], "DESCRIPCIÓN", y, align="left")
    _draw_header_en_celda(p, cols["cant_left"], cols["cant_w"], "CANT.", y, align="left")
    _draw_header_en_celda(p, cols["punit_left"], cols["punit_w"], "PRECIO UNIT.", y, align="left")
    _draw_header_en_celda(p, cols["total_left"], cols["total_w"], "TOTAL", y, align="left")
    p.setStrokeColor(_COLOR_GRIS_BORDE)
    p.line(margin, y - 0.06 * inch, w - margin, y - 0.06 * inch)
    return y - 0.2 * inch


def _draw_fila_tabla(p, y, cols, desc, cant, pu, sub, vacia=False):
    p.setFont("Helvetica", 8 if not vacia else 8)
    if vacia:
        p.setFillColor(_COLOR_GRIS_SUAVE)
        p.drawString(cols["desc"], y, "")
        p.drawRightString(cols["cant"], y, "—")
        p.drawRightString(cols["punit"], y, "—")
        p.drawRightString(cols["total"], y, "—")
        p.setFillColor(HexColor("#000000"))
    else:
        desc_lines = _wrap_text(p, desc, cols["desc_max"], "Helvetica", 8)
        first = True
        for dl in desc_lines[:2]:
            p.drawString(cols["desc"], y, (dl or "")[:52])
            if first:
                p.drawRightString(cols["cant"], y, str(cant))
                p.drawRightString(cols["punit"], y, f"${pu:.2f}")
                p.drawRightString(cols["total"], y, f"${sub:.2f}")
                first = False
            y -= 0.16 * inch
        if len(desc_lines) <= 1:
            return y - 0.04 * inch
        return y - 0.02 * inch
    return y - 0.18 * inch


def _draw_seccion_tabla(
    p,
    y,
    w,
    h,
    margin,
    ancho_util,
    titulo,
    items,
    total_label,
    total_val,
    *,
    cols=None,
):
    """Dibuja sección MO o Refacciones; retorna nueva y."""
    if cols is None:
        cols = _cols_tabla(w, margin)
    row_h = 0.18 * inch
    header_block = 0.26 * inch + _TABLA_GAP_BARRA_ENCABEZADO + 0.2 * inch + 0.22 * inch + 0.24 * inch
    n_rows = max(len(items), 1)
    needed = header_block + n_rows * row_h + 0.28 * inch
    y = _ensure_y(p, y, min(needed, 2.5 * inch), h, margin)

    y = _barra_roja(p, margin, y, ancho_util, 0.24 * inch, titulo, size=8)
    y -= _TABLA_GAP_BARRA_ENCABEZADO
    y = _draw_tabla_encabezado(p, y, cols, margin, w)

    p.setFont("Helvetica", 8)
    drawn = 0
    for it in items:
        if y < _Y_MIN + 0.35 * inch:
            p.showPage()
            y = h - margin - 0.35 * inch
            y = _barra_roja(p, margin, y, ancho_util, 0.24 * inch, f"{titulo} (cont.)", size=8)
            y -= _TABLA_GAP_BARRA_ENCABEZADO
            y = _draw_tabla_encabezado(p, y, cols, margin, w)
        desc = it.get("descripcion") or "-"
        cant = it.get("cantidad", 1)
        sub = float(it.get("subtotal", 0) or 0)
        try:
            cant_num = max(0.001, float(cant))
        except (TypeError, ValueError):
            cant_num = 1
        pu = float(it.get("precio_unitario") or 0) or (sub / cant_num if cant_num else 0)
        y = _draw_fila_tabla(p, y, cols, desc, cant, pu, sub)
        drawn += 1

    # Filas vacías de relleno solo si hay espacio y pocas líneas reales
    pad = 0
    if drawn < _TABLA_MIN_FILAS:
        for _ in range(_TABLA_MIN_FILAS - drawn):
            if y < _Y_MIN + 0.5 * inch:
                break
            y = _draw_fila_tabla(p, y, cols, "", "", 0, 0, vacia=True)
            pad += 1

    p.setStrokeColor(_COLOR_GRIS_BORDE)
    p.line(margin, y, w - margin, y)
    y -= 0.16 * inch
    p.setFont("Helvetica-Bold", 8)
    p.drawRightString(cols["total_left"] - 0.08 * inch, y, total_label)
    p.setFillColor(_COLOR_ROJO)
    p.drawRightString(cols["total"], y, f"${total_val:.2f}")
    p.setFillColor(HexColor("#000000"))
    return y - 0.14 * inch


def _draw_comentarios_y_resumen(
    p,
    y,
    w,
    h,
    margin,
    ancho_util,
    comentarios: str,
    cliente_proporciono: bool,
    subtotal_mano: float,
    subtotal_partes: float,
    descuento: float,
    total: float,
):
    gap = 0.12 * inch
    col_w = (ancho_util - gap) / 2
    x_left = margin
    x_right = margin + col_w + gap
    box_h = 1.55 * inch
    y = _ensure_y(p, y, box_h + 0.1 * inch, h, margin)
    y_top = y

    # --- Comentarios (izquierda) ---
    p.setStrokeColor(_COLOR_GRIS_BORDE)
    p.setFillColor(HexColor("#ffffff"))
    p.rect(x_left, y_top - box_h, col_w, box_h, fill=1, stroke=1)
    yy = _barra_header_negra(p, x_left, y_top, col_w, 0.22 * inch, "COMENTARIOS", size=7.5)
    p.setFont("Helvetica", 8)
    yy -= 0.12 * inch
    for ln in _wrap_text(p, comentarios, col_w - 0.2 * inch, "Helvetica", 8)[:4]:
        p.drawString(x_left + 0.08 * inch, yy, ln)
        yy -= 0.15 * inch
    yy = y_top - box_h + 0.28 * inch
    marca = "[X]" if cliente_proporciono else "[ ]"
    p.setFont("Helvetica", 7.5)
    p.drawString(x_left + 0.08 * inch, yy, f"{marca} Cliente proporcionó refacciones")

    # --- Resumen (derecha) ---
    p.setFillColor(HexColor("#ffffff"))
    p.rect(x_right, y_top - box_h, col_w, box_h, fill=1, stroke=1)
    yy = _barra_header_negra(p, x_right, y_top, col_w, 0.22 * inch, "RESUMEN DE INVERSIÓN", size=7.5)
    lh = 0.17 * inch
    yy -= 0.14 * inch
    x_lbl = x_right + col_w - 1.35 * inch
    x_val = x_right + col_w - 0.1 * inch
    p.setFont("Helvetica", 8)
    for lbl, val in [
        ("Total mano de obra:", subtotal_mano),
        ("Total refacciones:", subtotal_partes),
    ]:
        p.drawRightString(x_lbl, yy, lbl)
        p.drawRightString(x_val, yy, f"${val:.2f}")
        yy -= lh
    subtotal = subtotal_mano + subtotal_partes
    p.drawRightString(x_lbl, yy, "Subtotal:")
    p.drawRightString(x_val, yy, f"${subtotal:.2f}")
    yy -= lh
    if descuento > 0:
        p.drawRightString(x_lbl, yy, "Descuento:")
        p.drawRightString(x_val, yy, f"-${descuento:.2f}")
        yy -= lh
    p.drawRightString(x_lbl, yy, "Impuestos (0%):")
    p.drawRightString(x_val, yy, "$0.00")
    yy -= lh + 0.04 * inch

    total_h = 0.3 * inch
    p.setFillColor(_COLOR_HEADER_BG)
    p.rect(x_right + 0.08 * inch, yy - total_h + 0.06 * inch, col_w - 0.16 * inch, total_h, fill=1, stroke=0)
    p.setFillColor(HexColor("#ffffff"))
    p.setFont("Helvetica-Bold", 8)
    p.drawString(x_right + 0.14 * inch, yy - 0.08 * inch, "TOTAL ESTIMADO A PAGAR:")
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(x_val, yy - 0.1 * inch, f"${total:.2f}")
    p.setFillColor(HexColor("#000000"))

    return y_top - box_h - 0.12 * inch


def _draw_autorizacion_compacta(p, y, w, h, margin, ancho_util):
    y = _ensure_y(p, y, 1.05 * inch, h, margin)
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(_COLOR_ROJO)
    p.drawString(margin, y, "AUTORIZACIÓN DEL CLIENTE")
    p.setFillColor(HexColor("#000000"))
    y -= 0.16 * inch
    auth_text = (
        "Autorizo la realización de los trabajos descritos en esta cotización, " "conforme al total estimado a pagar."
    )
    p.setFont("Helvetica", 8)
    y = _draw_wrapped_block(p, auth_text, margin, y, ancho_util, font="Helvetica", size=8, line_h=0.13 * inch)
    y -= 0.1 * inch
    p.drawString(margin, y, "Nombre: _________________________")
    p.drawString(margin + 3.2 * inch, y, "Firma: _________________________")
    y -= 0.28 * inch
    p.drawString(margin, y, "Fecha:  ____ / ____ / ________")
    return y - 0.18 * inch


def _draw_pie_comercial(p, y, w, margin, ancho_util):
    p.setStrokeColor(_COLOR_ROJO)
    p.setLineWidth(1)
    p.line(margin, y, w - margin, y)
    y -= 0.16 * inch
    p.setFont("Helvetica", 7.5)
    p.setFillColor(HexColor("#000000"))
    p.drawCentredString(
        w / 2,
        y,
        f"Tel: {_TALLER_TELEFONO}  |  WhatsApp: {_TALLER_WHATSAPP}  |  {_TALLER_CORREO}",
    )
    y -= 0.14 * inch
    for ln in _wrap_text(p, _TALLER_DIRECCION, ancho_util - 0.2 * inch, "Helvetica", 7.5):
        p.drawCentredString(w / 2, y, ln)
        y -= 0.13 * inch
    return y


def _barra_naranja(p, x, y, ancho, alto, texto, font="Helvetica-Bold", size=10):
    """Alias legacy — hoja técnico no usa esto; cotización usa _barra_roja."""
    return _barra_roja(p, x, y, ancho, alto, texto, font=font, size=size)


class _CotizacionPaginationCanvas(canvas.Canvas):
    """Añade «Página X de Y» antes de cerrar cada página (cotización cliente)."""

    def __init__(self, *args, total_pages: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self._total_pages_for_pagination = total_pages

    def showPage(self):
        self._draw_paginacion()
        super().showPage()

    def _draw_paginacion(self):
        w, _ = self._pagesize
        margin = inch
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#64748b"))
        text = f"Página {self._pageNumber} de {self._total_pages_for_pagination}"
        self.drawRightString(w - margin, 0.4 * inch, text)
        self.setFillColor(HexColor("#000000"))


def _generar_pdf_cotizacion(
    orden_data: dict,
    app_name: str = "MedinaAutoDiag",
    *,
    _pagination_total: int | None = None,
) -> bytes:
    """Genera PDF de cotización compacta (P5.4 Fase 2) para el cliente."""
    page_count: dict[str, int] = {}

    if _pagination_total is None:

        class _CountingCanvas(canvas.Canvas):
            def save(self):
                page_count["total"] = self._pageNumber
                canvas.Canvas.save(self)

        canvas_cls = _CountingCanvas
        canvas_kwargs: dict = {}
    else:
        canvas_cls = _CotizacionPaginationCanvas
        canvas_kwargs = {"total_pages": _pagination_total}

    buf = BytesIO()
    p = canvas_cls(buf, pagesize=letter, **canvas_kwargs)
    w, h = letter
    margin = 0.65 * inch
    ancho_util = w - 2 * margin
    y = h - 0.4 * inch

    # --- Encabezado ---
    y = _draw_header_compacto(p, w, y, margin, ancho_util)

    fecha_str = _format_fecha_ingreso(orden_data.get("fecha_ingreso"))
    numero_orden = orden_data.get("numero_orden", "") or "-"
    vigencia_meta = _texto_vigencia_metadata(orden_data.get("fecha_vigencia_cotizacion"))
    y = _draw_metadata_bar(p, w, y, margin, fecha_str, numero_orden, vigencia_meta)

    # --- Cliente / Vehículo (misma altura en ambos cuadros) ---
    cliente = orden_data.get("cliente") or {}
    veh = orden_data.get("vehiculo") or {}
    gap_cajas = 0.12 * inch
    col_w = (ancho_util - gap_cajas) / 2
    lineas_cli = [
        ("Nombre", (cliente.get("nombre") or "-")[:45]),
        ("Teléfono", (cliente.get("telefono") or "-")[:30]),
        ("Email", (cliente.get("email") or "-")[:38]),
        ("Dirección", (cliente.get("direccion") or "-")[:45]),
    ]
    lineas_veh = [
        ("Marca", veh.get("marca") or "-"),
        ("Modelo", veh.get("modelo") or "-"),
        ("Año", str(veh.get("anio") or "-")),
        ("VIN", (veh.get("vin") or "-")[:20]),
        (
            "Kilometraje",
            str(orden_data.get("kilometraje")) if orden_data.get("kilometraje") is not None else "-",
        ),
    ]
    line_h_caja = 0.17 * inch
    body_h_cajas = max(0.55 * inch, max(len(lineas_cli), len(lineas_veh)) * line_h_caja + 0.14 * inch)
    y_cli_top = y
    y_after_cli = _draw_caja_datos(
        p,
        margin,
        y_cli_top,
        col_w,
        "DATOS DEL CLIENTE",
        lineas_cli,
        body_h=body_h_cajas,
    )
    y_after_veh = _draw_caja_datos(
        p,
        margin + col_w + gap_cajas,
        y_cli_top,
        col_w,
        "DATOS DEL VEHÍCULO",
        lineas_veh,
        body_h=body_h_cajas,
    )
    y = min(y_after_cli, y_after_veh) - 0.12 * inch

    servicios = orden_data.get("servicios", [])
    partes = orden_data.get("partes", [])
    subtotal_mano = sum(float(s.get("subtotal", 0) or 0) for s in servicios)
    subtotal_partes = sum(float(pt.get("subtotal", 0) or 0) for pt in partes)
    descuento = float(orden_data.get("descuento", 0) or 0)
    total = float(orden_data.get("total", 0) or 0)

    # --- Mano de obra ---
    y = _draw_seccion_tabla(
        p,
        y,
        w,
        h,
        margin,
        ancho_util,
        "MANO DE OBRA (SERVICIO TÉCNICO)",
        servicios,
        "TOTAL MANO DE OBRA",
        subtotal_mano,
    )

    # --- Refacciones ---
    y = _draw_seccion_tabla(
        p,
        y,
        w,
        h,
        margin,
        ancho_util,
        "REFACCIONES (PIEZAS Y MATERIALES)",
        partes,
        "TOTAL REFACCIONES",
        subtotal_partes,
    )

    comentarios = _comentarios_compactos(
        orden_data.get("diagnostico_inicial") or "",
        orden_data.get("observaciones_cliente") or "",
    )
    cliente_proporciono = bool(orden_data.get("cliente_proporciono_refacciones"))

    y = _draw_comentarios_y_resumen(
        p,
        y,
        w,
        h,
        margin,
        ancho_util,
        comentarios,
        cliente_proporciono,
        subtotal_mano,
        subtotal_partes,
        descuento,
        total,
    )

    y = _draw_autorizacion_compacta(p, y, w, h, margin, ancho_util)
    y = _draw_pie_comercial(p, y, w, margin, ancho_util)

    p.save()
    if _pagination_total is None:
        total_pages = page_count.get("total", p._pageNumber) or 1
        return _generar_pdf_cotizacion(orden_data, app_name=app_name, _pagination_total=total_pages)
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
            "cliente_proporciono_refacciones": bool(getattr(orden, "cliente_proporciono_refacciones", False)),
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
    margin_top = 0.45 * inch
    ancho_util = w - 2 * margin
    y = h - margin_top

    # Logo centrado: más ancho y delgado
    logo_w, logo_h = 3.4 * inch, 0.6 * inch
    if _LOGO_PATH.exists():
        p.drawImage(str(_LOGO_PATH), w / 2 - logo_w / 2, y - logo_h, width=logo_w, height=logo_h)
    y -= logo_h + 0.2 * inch
    p.setFont("Helvetica", 12)
    p.drawCentredString(w / 2, y, "HOJA DE TRABAJO")
    y -= 0.18 * inch
    p.setFont("Helvetica", 10)
    p.drawCentredString(w / 2, y, "SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ")
    y -= 0.22 * inch
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.5)
    p.line(margin, y, w - margin, y)
    y -= 0.25 * inch

    numero_orden = orden_data.get("numero_orden", "")
    fecha_str = orden_data.get("fecha_ingreso", "")
    if fecha_str:
        fecha_str = str(fecha_str)[:19].replace("T", " ")
    else:
        fecha_str = "-"

    alto_caja = 0.5 * inch
    p.setFillColor(_COLOR_VERDE_CLARO)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.25)
    p.rect(margin, y - alto_caja, ancho_util, alto_caja, fill=1, stroke=1)
    y_linea1 = y - 0.14 * inch
    y_linea2 = y - 0.32 * inch
    # Layout tipo doc azul: FECHA izq, ORDEN # derecha línea 1; TÉCNICO izq línea 2 (verde = labels)
    right_x = w - margin - 0.15 * inch
    x_izq = margin + 0.15 * inch
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(_COLOR_VERDE)
    p.drawString(x_izq, y_linea1, "FECHA")
    p.setFont("Helvetica", 10)
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_izq + p.stringWidth("FECHA ", "Helvetica-Bold", 10), y_linea1, fecha_str)
    num_orden = (numero_orden or "-")[:25]
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(_COLOR_VERDE)
    lbl_orden = "ORDEN # "
    p.drawString(right_x - p.stringWidth(lbl_orden + num_orden, "Helvetica", 10), y_linea1, lbl_orden)
    p.setFont("Helvetica", 10)
    p.setFillColor(HexColor("#000000"))
    p.drawRightString(right_x, y_linea1, num_orden)
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(_COLOR_VERDE)
    p.drawString(x_izq, y_linea2, "TÉCNICO")
    p.setFont("Helvetica", 10)
    p.setFillColor(HexColor("#000000"))
    tecnico_val = (orden_data.get("tecnico_nombre") or "-")[:28]
    prioridad_val = orden_data.get("prioridad", "-")
    p.drawString(
        x_izq + p.stringWidth("TÉCNICO ", "Helvetica-Bold", 10),
        y_linea2,
        f"{tecnico_val}  |  Prioridad: {prioridad_val}",
    )
    y -= alto_caja + 0.15 * inch

    y = _barra_verde(p, margin, y, ancho_util, 0.28 * inch, "CLIENTE / VEHÍCULO", size=10)
    y -= 0.1 * inch
    cliente = orden_data.get("cliente") or {}
    veh = orden_data.get("vehiculo") or {}
    # Layout CLIENTE | VEHÍCULO con columnas bien separadas (evitar solapamiento)
    col_ancho = ancho_util / 2
    x_label_izq = margin + 0.2 * inch
    x_val_izq = margin + 1.0 * inch
    x_fin_izq = margin + col_ancho - 0.15 * inch  # valores izquierda no pasan de aquí
    x_label_der = margin + col_ancho + 0.2 * inch
    x_val_der = margin + col_ancho + 1.0 * inch
    line_h = 0.26 * inch
    n_lineas = 6
    alto_bloque = n_lineas * line_h + 0.2 * inch

    def _truncar(p, texto, x_inicio, x_fin, font="Helvetica", size=9):
        """Trunca texto para que no exceda el ancho disponible."""
        txt = texto or "-"
        if txt == "-":
            return "-"
        txt = str(txt).strip()
        max_w = x_fin - x_inicio - 0.05 * inch
        while len(txt) > 1 and p.stringWidth(txt, font, size) > max_w:
            txt = txt[:-1]
        return txt or "-"

    p.setFillColor(_COLOR_VERDE_CLARO)
    p.setStrokeColor(HexColor("#000000"))
    p.setLineWidth(0.2)
    p.rect(margin, y - alto_bloque, ancho_util, alto_bloque, fill=1, stroke=1)
    # Línea vertical separando columnas
    p.setStrokeColor(HexColor("#9ca3af"))
    p.setLineWidth(0.5)
    p.line(margin + col_ancho, y - alto_bloque, margin + col_ancho, y)
    p.setStrokeColor(HexColor("#000000"))
    p.setFillColor(HexColor("#000000"))
    y -= 0.15 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(x_label_izq, y, "CLIENTE")
    p.drawString(x_label_der, y, "VEHÍCULO")
    y -= line_h
    p.setFont("Helvetica", 9)
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_izq, y, "NOMBRE:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_izq, y, _truncar(p, cliente.get("nombre"), x_val_izq, x_fin_izq))
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_der, y, "MARCA:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_der, y, (veh.get("marca") or "-")[:18])
    y -= line_h
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_izq, y, "TEL:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_izq, y, _truncar(p, cliente.get("telefono"), x_val_izq, x_fin_izq))
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_der, y, "MODELO:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_der, y, (veh.get("modelo") or "-")[:18])
    y -= line_h
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_izq, y, "DIRECCIÓN:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_izq, y, _truncar(p, cliente.get("direccion"), x_val_izq, x_fin_izq))
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_der, y, "AÑO:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_der, y, str(veh.get("anio") or "-")[:10])
    y -= line_h
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_der, y, "VIN:")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_der, y, (veh.get("vin") or "-")[:18])
    y -= line_h
    p.setFillColor(HexColor("#1e3a2f"))
    p.drawString(x_label_der, y, "KM:")
    km_val = orden_data.get("kilometraje")
    p.setFillColor(HexColor("#000000"))
    p.drawString(x_val_der, y, str(km_val) if km_val is not None and km_val != "" else "-")
    y -= line_h + 0.15 * inch

    diagnostico = (orden_data.get("diagnostico_inicial") or "").strip()
    if diagnostico:
        y = _barra_verde(p, margin, y, ancho_util, 0.26 * inch, "DIAGNÓSTICO O SERVICIO", size=10)
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
    partes = orden_data.get("partes", [])
    y = _barra_verde(p, margin, y, ancho_util, 0.26 * inch, "SERVICIOS Y REFACCIONES A REALIZAR", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica-Bold", 9)
    p.drawString(margin, y, "Cant.")
    p.drawString(margin + 0.5 * inch, y, "Descripción")
    y -= 0.18 * inch
    p.setFont("Helvetica", 9)
    for s in servicios:
        desc = (s.get("descripcion") or "")[:70]
        cant = s.get("cantidad", 1)
        p.drawString(margin, y, str(cant) if isinstance(cant, int) else f"{cant:.3g}")
        p.drawString(margin + 0.5 * inch, y, desc)
        y -= 0.22 * inch
    for pt in partes:
        desc = (pt.get("descripcion") or "")[:70]
        cant = pt.get("cantidad", 1)
        p.drawString(margin, y, str(cant) if isinstance(cant, int) else f"{cant:.3g}")
        p.drawString(margin + 0.5 * inch, y, desc)
        y -= 0.22 * inch
    if not servicios and not partes:
        p.drawString(margin + 0.5 * inch, y, "(Sin ítems)")
        y -= 0.22 * inch
    y -= 0.25 * inch

    obs_tecnico = (orden_data.get("observaciones_tecnico") or "").strip()
    y = _barra_verde(p, margin, y, ancho_util, 0.26 * inch, "COMENTARIOS DEL TÉCNICO", size=10)
    y -= 0.12 * inch
    p.setFont("Helvetica", 9)
    if obs_tecnico:
        for line in obs_tecnico.split("\n")[:10]:
            line = (line.strip())[:95]
            if line:
                p.drawString(margin, y, line)
                y -= 0.2 * inch
        y -= 0.15 * inch
    else:
        p.setFont("Helvetica-Oblique", 9)
        p.setFillColor(_COLOR_GRIS_SUAVE)
        p.drawString(margin, y, "Hallazgos durante el servicio:")
        y -= 0.25 * inch
        for _ in range(3):
            p.setStrokeColor(HexColor("#cccccc"))
            p.line(margin, y, w - margin, y)
            y -= 0.28 * inch
        y -= 0.1 * inch
        p.setFillColor(HexColor("#000000"))
        p.drawString(margin, y, "Recomendaciones al cliente:")
        y -= 0.25 * inch
        for _ in range(2):
            p.setStrokeColor(HexColor("#cccccc"))
            p.line(margin, y, w - margin, y)
            y -= 0.28 * inch
        y -= 0.1 * inch

    p.setFont("Helvetica-Oblique", 8)
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
                "direccion": (orden.cliente.direccion or "").strip() or "",
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

        prioridad = getattr(orden.prioridad, "value", None) or str(orden.prioridad) if orden.prioridad else "-"
        orden_data = {
            "numero_orden": orden.numero_orden,
            "fecha_ingreso": orden.fecha_ingreso.isoformat() if orden.fecha_ingreso else None,
            "fecha_vigencia_cotizacion": (
                orden.fecha_vigencia_cotizacion.isoformat() if orden.fecha_vigencia_cotizacion else None
            ),
            "kilometraje": orden.kilometraje,
            "diagnostico_inicial": orden.diagnostico_inicial,
            "observaciones_cliente": orden.observaciones_cliente,
            "observaciones_tecnico": orden.observaciones_tecnico,
            "prioridad": prioridad,
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
