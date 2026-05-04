# Plan: Cotizaciones de refacción especial (no local / importación)

**Estado:** Fase 1 + PDF (2026-05-04)

## Objetivo

Módulo aparte para cotizar refacciones fuera del mercado local: varias **opciones de compra** por línea (origen, URL, USD/MXN, TC, días), **cálculo de precio sugerido y ganancia estimada**, **comentarios internos**, flujo **BORRADOR → ENVIADA → ACEPTADA_CLIENTE → EN_COMPRA → RECIBIDA → ENTREGADA** y **registro de compras** (PayPal/tarjeta/…) sin depender de orden de compra formal.

## Reglas acordadas

| Tema | Decisión |
|------|----------|
| Vínculo OT | Opcional (`id_orden_trabajo`) |
| Quién acepta | Oficina: **ADMIN, CAJA, EMPLEADO** (TECNICO no puede marcar “cliente aceptó”) |
| Compra | Directa PayPal/tarjeta registrada en tabla `compras_ejecutadas_cotizacion_refaccion` |
| Multimoneda | USD/MXN; TC global (`tc_referencia_usd_mxn`) o por opción (`tipo_cambio_a_mxn`) |
| Opción elegida para totales | Preferida (`es_preferida`); si varias, primera preferida; si ninguna, primera opción de la línea |

## Implementado

### Backend

- Modelos: `CotizacionRefaccionEspecial`, `LineaCotizacionRefaccion`, `OpcionCompraLineaCotizacion`, `ComentarioCotizacionRefaccion`, `CompraEjecutadaCotizacionRefaccion`
- Migración: `a7b8c9d0e1f2_add_cotizaciones_refaccion_especial.py`
- Router: `/api/cotizaciones-refaccion/` (lista, CRUD cabecera/líneas/opciones, comentarios, enviar, aceptar-cliente, registrar-compra, marcar recibida/entregada, cancelar)
- **PDF:** `GET /api/cotizaciones-refaccion/{id}/pdf` — `app/services/cotizacion_refaccion_pdf.py` (ReportLab, logo y estilo alineado a cotización OT)
- Cálculo: `app/services/cotizacion_refaccion_calculo.py` (costo MXN, precio con margen + IVA desde `settings`)

### Frontend

- Listado: `/cotizaciones-refaccion`
- Detalle: `/cotizaciones-refaccion/:id` (botón **PDF cotización**)
- Menú: **Cotiz. refacción**

### Tests

- `tests/test_cotizacion_refaccion_calculo.py`

## Pendiente (siguientes iteraciones)

- Enlace automático a **venta** o **entrada a inventario** tras compra
- Adjuntos por línea (foto referencia)
- Reportes dedicados (pendientes, ganancia real vs estimada)
