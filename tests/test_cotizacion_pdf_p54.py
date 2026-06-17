"""P5.4 Fase 1 — tests de copy y estructura del PDF de cotización OT."""

from datetime import date, datetime, timedelta

import pytest

from app.routers.ordenes_trabajo.cotizacion import _generar_pdf_cotizacion

try:
    import fitz  # pymupdf

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    if not HAS_PYMUPDF:
        pytest.skip("pymupdf no instalado")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def _base_orden(**overrides):
    data = {
        "numero_orden": "OT-P54-TEST-001",
        "fecha_ingreso": datetime.now().isoformat(),
        "fecha_vigencia_cotizacion": (date.today() + timedelta(days=7)).isoformat(),
        "kilometraje": 50000,
        "diagnostico_inicial": "Diagnóstico de prueba.",
        "observaciones_cliente": "Ruido en motor.",
        "descuento": 100,
        "total": 900.0,
        "cliente": {
            "nombre": "Cliente Prueba",
            "telefono": "5550000000",
            "email": "test@ejemplo.com",
            "direccion": "Calle Test 1",
        },
        "vehiculo": {"marca": "Nissan", "modelo": "Sentra", "anio": 2020, "vin": "VIN123"},
        "servicios": [
            {"descripcion": "Servicio prueba", "cantidad": 1, "precio_unitario": 500, "subtotal": 500},
        ],
        "partes": [
            {"descripcion": "[TST] Pieza prueba", "cantidad": 1, "precio_unitario": 500, "subtotal": 500},
        ],
    }
    data.update(overrides)
    return data


def test_pdf_genera_bytes_validos():
    pdf = _generar_pdf_cotizacion(_base_orden())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_fase1_copy_y_estructura():
    pdf = _generar_pdf_cotizacion(_base_orden())
    text = _extract_pdf_text(pdf)

    assert "Esta propuesta detalla el trabajo recomendado" in text
    assert "MANO DE OBRA (SERVICIO TÉCNICO)" in text
    assert "REFACCIONES (PIEZAS Y MATERIALES)" in text
    assert "Incluye el trabajo técnico realizado por nuestros especialistas" in text
    assert "RESUMEN DE INVERSIÓN" in text
    assert "Servicio técnico:" in text
    assert "Refacciones:" in text
    assert "TOTAL ESTIMADO A PAGAR:" in text
    assert "Precios expresados en pesos mexicanos (MXN)." in text
    assert "AUTORIZACIÓN DEL CLIENTE" in text
    assert "VIGENCIA" in text
    assert "Válida hasta:" in text
    assert "Medina AutoDiag" in text

    assert "Subtotal Mano de Obra:" not in text
    assert "Subtotal Refacciones:" not in text
    assert "Subtotal general" not in text
    assert "TOTAL: $" not in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_vigencia_default_sin_fecha():
    pdf = _generar_pdf_cotizacion(_base_orden(fecha_vigencia_cotizacion=None))
    text = _extract_pdf_text(pdf)
    assert "Vigencia de esta propuesta: 7 días naturales." in text
    assert "Válida hasta:" not in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_sin_descuento_no_muestra_linea():
    pdf = _generar_pdf_cotizacion(_base_orden(descuento=0, total=1000.0))
    text = _extract_pdf_text(pdf)
    assert "Descuento:" not in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_numeracion_paginas():
    pdf = _generar_pdf_cotizacion(_base_orden())
    doc = fitz.open(stream=pdf, filetype="pdf")
    total = doc.page_count
    assert total >= 1
    for i, page in enumerate(doc):
        text = page.get_text()
        assert f"Página {i + 1} de {total}" in text
    doc.close()


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_numeracion_multipagina():
    """Escenario tipo A/C: bloque comercial en pág. 2."""
    pdf = _generar_pdf_cotizacion(
        _base_orden(
            numero_orden="OT-P54-A-001",
            servicios=[
                {"descripcion": "Afinación mayor - mano de obra", "cantidad": 1, "precio_unitario": 650, "subtotal": 650},
                {"descripcion": "Limpieza de cuerpo de aceleración", "cantidad": 1, "precio_unitario": 350, "subtotal": 350},
            ],
            partes=[
                {"descripcion": "[BKR6E] Bujías iridium (set 4)", "cantidad": 4, "precio_unitario": 85, "subtotal": 340},
                {"descripcion": "[AF1234] Filtro de aire", "cantidad": 1, "precio_unitario": 180, "subtotal": 180},
                {"descripcion": "[OF456] Filtro de aceite", "cantidad": 1, "precio_unitario": 95, "subtotal": 95},
                {"descripcion": "Aceite sintético 5W-30 (5L)", "cantidad": 1, "precio_unitario": 435, "subtotal": 435},
            ],
            descuento=0,
            total=1850.0,
        )
    )
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert doc.page_count == 2
    assert "Página 1 de 2" in doc[0].get_text()
    assert "Página 2 de 2" in doc[1].get_text()
    assert "RESUMEN DE INVERSIÓN" in doc[1].get_text()
    doc.close()


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_pie_comercial_sin_placeholders():
    pdf = _generar_pdf_cotizacion(_base_orden())
    text = _extract_pdf_text(pdf)
    assert "868 114 1865" in text
    assert "868 394 5536" in text
    assert "recepcion@medinamedinaautodiag.com" in text
    assert "Ave. Lauro Villar #930A" in text
    assert "000 0000" not in text
    assert "[Dirección" not in text
    assert "TODO" not in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_numeracion_unica_por_pagina():
    pdf = _generar_pdf_cotizacion(
        _base_orden(
            numero_orden="OT-P54-A-001",
            servicios=[
                {"descripcion": "Afinación mayor - mano de obra", "cantidad": 1, "precio_unitario": 650, "subtotal": 650},
                {"descripcion": "Limpieza de cuerpo de aceleración", "cantidad": 1, "precio_unitario": 350, "subtotal": 350},
            ],
            partes=[
                {"descripcion": "[BKR6E] Bujías iridium (set 4)", "cantidad": 4, "precio_unitario": 85, "subtotal": 340},
                {"descripcion": "[AF1234] Filtro de aire", "cantidad": 1, "precio_unitario": 180, "subtotal": 180},
                {"descripcion": "[OF456] Filtro de aceite", "cantidad": 1, "precio_unitario": 95, "subtotal": 95},
                {"descripcion": "Aceite sintético 5W-30 (5L)", "cantidad": 1, "precio_unitario": 435, "subtotal": 435},
            ],
            descuento=0,
            total=1850.0,
        )
    )
    doc = fitz.open(stream=pdf, filetype="pdf")
    total = doc.page_count
    for i, page in enumerate(doc):
        label = f"Página {i + 1} de {total}"
        assert page.get_text().count(label) == 1
    doc.close()
