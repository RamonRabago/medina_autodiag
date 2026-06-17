"""P5.4 — tests de estructura del PDF de cotización OT (Fase 2 compacto)."""

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


def _page_count(pdf_bytes: bytes) -> int:
    if not HAS_PYMUPDF:
        pytest.skip("pymupdf no instalado")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = doc.page_count
    doc.close()
    return n


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
        "cliente_proporciono_refacciones": False,
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


def _escenario_aceite(**overrides):
    """Fixture equivalente OT-20260617-0002 — cambio de aceite simple."""
    data = {
        "numero_orden": "OT-20260617-0002",
        "fecha_ingreso": datetime.now().isoformat(),
        "fecha_vigencia_cotizacion": (date.today() + timedelta(days=7)).isoformat(),
        "kilometraje": None,
        "diagnostico_inicial": "Cambio de Aceite de Motor",
        "observaciones_cliente": "Cambio de Aceite de Motor",
        "descuento": 0,
        "total": 250.0,
        "cliente_proporciono_refacciones": True,
        "cliente": {
            "nombre": "Angel Aaron Rabago Garcia",
            "telefono": "8683036775",
            "email": "-",
            "direccion": "Calle Arcos de Belen #74",
        },
        "vehiculo": {"marca": "Nissan", "modelo": "Sentra", "anio": 2018, "vin": ""},
        "servicios": [
            {
                "descripcion": "Cambio de aceite y filtro",
                "cantidad": 1,
                "precio_unitario": 250,
                "subtotal": 250,
            },
        ],
        "partes": [],
    }
    data.update(overrides)
    return data


def test_pdf_genera_bytes_validos():
    pdf = _generar_pdf_cotizacion(_base_orden())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_fase2_estructura_compacta():
    pdf = _generar_pdf_cotizacion(_base_orden())
    text = _extract_pdf_text(pdf)

    assert "COTIZACIÓN" in text
    assert "SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ" in text
    assert "Esta propuesta detalla el trabajo recomendado" not in text
    assert "Mano de obra corresponde al trabajo técnico" not in text
    assert "DATOS DEL CLIENTE" in text
    assert "DATOS DEL VEHÍCULO" in text
    assert "MANO DE OBRA (SERVICIO TÉCNICO)" in text
    assert "REFACCIONES (PIEZAS Y MATERIALES)" in text
    assert "PRECIO UNIT." in text
    assert "TOTAL MANO DE OBRA" in text
    assert "TOTAL REFACCIONES" in text
    assert "COMENTARIOS" in text
    assert "Cliente proporcionó refacciones" in text
    assert "RESUMEN DE INVERSIÓN" in text
    assert "TOTAL ESTIMADO A PAGAR:" in text
    assert "Impuestos (0%)" in text
    assert "AUTORIZACIÓN DEL CLIENTE" in text
    assert "VIGENCIA:" in text
    assert "868 114 1865" in text
    assert "868 394 5536" in text
    assert "recepcion@medinamedinaautodiag.com" in text
    assert "Ave. Lauro Villar #930A" in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_caso_simple_una_pagina():
    """OT aceite + cliente proporciona refacciones debe caber en 1 hoja."""
    pdf = _generar_pdf_cotizacion(_escenario_aceite())
    assert _page_count(pdf) == 1
    text = _extract_pdf_text(pdf)
    assert "Página 1 de 1" in text
    assert "Cambio de Aceite de Motor" in text
    assert "[X] Cliente proporcionó refacciones" in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_comentarios_deduplicados():
    pdf = _generar_pdf_cotizacion(_escenario_aceite())
    text = _extract_pdf_text(pdf)
    assert text.count("Cambio de Aceite de Motor") == 1


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_vigencia_metadata_default():
    pdf = _generar_pdf_cotizacion(_base_orden(fecha_vigencia_cotizacion=None))
    text = _extract_pdf_text(pdf)
    assert "VIGENCIA:" in text
    assert "7 días naturales" in text


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
def test_pdf_escenario_afinacion_multipagina():
    pdf = _generar_pdf_cotizacion(
        _base_orden(
            numero_orden="OT-P54-A-001",
            diagnostico_inicial="Afinación mayor",
            observaciones_cliente="Motor falla en ralentí",
            servicios=[
                {
                    "descripcion": "Afinación mayor - mano de obra",
                    "cantidad": 1,
                    "precio_unitario": 650,
                    "subtotal": 650,
                },
                {
                    "descripcion": "Limpieza de cuerpo de aceleración",
                    "cantidad": 1,
                    "precio_unitario": 350,
                    "subtotal": 350,
                },
            ],
            partes=[
                {
                    "descripcion": "[BKR6E] Bujías iridium (set 4)",
                    "cantidad": 4,
                    "precio_unitario": 85,
                    "subtotal": 340,
                },
                {"descripcion": "[AF1234] Filtro de aire", "cantidad": 1, "precio_unitario": 180, "subtotal": 180},
                {"descripcion": "[OF456] Filtro de aceite", "cantidad": 1, "precio_unitario": 95, "subtotal": 95},
                {"descripcion": "Aceite sintético 5W-30 (5L)", "cantidad": 1, "precio_unitario": 435, "subtotal": 435},
            ],
            descuento=0,
            total=1850.0,
        )
    )
    doc = fitz.open(stream=pdf, filetype="pdf")
    assert doc.page_count >= 1
    full = "\n".join(p.get_text() for p in doc)
    assert "RESUMEN DE INVERSIÓN" in full
    doc.close()


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_pie_comercial_sin_placeholders():
    pdf = _generar_pdf_cotizacion(_base_orden())
    text = _extract_pdf_text(pdf)
    assert "000 0000" not in text
    assert "[Dirección" not in text
    assert "TODO" not in text


@pytest.mark.skipif(not HAS_PYMUPDF, reason="pymupdf no instalado")
def test_pdf_numeracion_unica_por_pagina():
    pdf = _generar_pdf_cotizacion(
        _base_orden(
            numero_orden="OT-P54-XL",
            servicios=[
                {
                    "descripcion": f"Servicio técnico #{i}",
                    "cantidad": 1,
                    "precio_unitario": 200 + i * 10,
                    "subtotal": 200 + i * 10,
                }
                for i in range(8)
            ],
            partes=[
                {
                    "descripcion": f"Refacción componente {i} descripción larga",
                    "cantidad": 1,
                    "precio_unitario": 150 + i * 20,
                    "subtotal": 150 + i * 20,
                }
                for i in range(12)
            ],
            descuento=0,
            total=5000.0,
        )
    )
    doc = fitz.open(stream=pdf, filetype="pdf")
    total = doc.page_count
    assert total >= 2
    for i, page in enumerate(doc):
        label = f"Página {i + 1} de {total}"
        assert page.get_text().count(label) == 1
    doc.close()
