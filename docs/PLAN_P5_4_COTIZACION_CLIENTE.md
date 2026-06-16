# PLAN P5.4 — COTIZACIÓN CLIENTE

**Versión:** 1.0  
**Fecha:** 16 de junio de 2026  
**Estado:** 📋 **PLAN APROBADO PARA IMPLEMENTACIÓN** — pendiente Fase 0 (auditoría visual) y autorización explícita por fase  
**Baseline HEAD:** `72faaab3a940375b59f3e412398680671c9fb289`  
**Contrato vigente:** A0 v2 (sin cambio en P5.4)  
**PRE-CHECK P5.4:** ✅ **RECOMENDADA** — veredicto: **FORMATO APTO CON OBSERVACIONES** (junio 2026)

**Relacionado:**

- [PLAN_P5_3_OPTIMIZACION_A0.md](./PLAN_P5_3_OPTIMIZACION_A0.md)
- [PLAN_P5_2_RECEPCION_OPERATIVA.md](./PLAN_P5_2_RECEPCION_OPERATIVA.md)
- [PLAN_FLUJO_COTIZACION_COMPRA.md](./PLAN_FLUJO_COTIZACION_COMPRA.md)
- [CIERRE_P5_2_RECEPCION_OPERATIVA.md](./CIERRE_P5_2_RECEPCION_OPERATIVA.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)

**Independencia:** P5.4 **no mezcla** con P5.3 (performance A0). Pueden ejecutarse en paralelo tras GO por fase.

---

## 1. Contexto

Medina AutoDiag V2 opera en producción con flujo de cotización OT establecido desde fases anteriores:

- El operador crea/edita una OT con servicios (mano de obra) y repuestos (refacciones).
- Desde `DetalleOrdenTrabajo` descarga **Cotización PDF** (naranja, ReportLab).
- El PDF se envía manualmente al cliente (WhatsApp, email).
- El sistema registra «Marcar cotización enviada» y, si aplica, autorización interna.

Tras validación operativa real (junio 2026) y PRE-CHECK P5.4, el formato **funciona** pero presenta **riesgo de percepción de doble cobro** cuando mano de obra y refacciones aparecen sin explicación clara para un cliente no técnico.

P5.2 (Recepción Operativa) y P5.3 (Optimización A0) están cerrados o planificados. P5.4 aborda exclusivamente la **calidad del entregable al cliente** — copy, estructura visual, datos comerciales y preview operativo — **sin rediseño total** del ERP.

### Baseline técnico

| Campo | Valor |
|-------|-------|
| **HEAD** | `72faaab3a940375b59f3e412398680671c9fb289` |
| **build_rev prod** | `72faaab3a940` |
| **PDF OT cliente** | `app/routers/ordenes_trabajo/cotizacion.py` → `_generar_pdf_cotizacion()` |
| **UI descarga** | `frontend/src/pages/DetalleOrdenTrabajo.jsx` |
| **Endpoint** | `GET /api/ordenes-trabajo/{id}/cotizacion` |
| **Flujo documentado** | `docs/PLAN_FLUJO_COTIZACION_COMPRA.md` |
| **Veredicto QA app** | APP OPERATIVA CON OBSERVACIONES |

### Flujo secundario (fuera de foco principal P5.4 v1)

Cotización **refacción especial** (`/cotizaciones-refaccion`, `cotizacion_refaccion_pdf.py`) — importación de piezas. P5.4 v1 se centra en **cotización OT de servicio taller**; alineación visual/copy con refacción especial queda como backlog opcional post-Fase 2.

---

## 2. Problema principal

> El PDF de cotización separa **Mano de obra** y **Refacciones** correctamente a nivel técnico, pero **no explica al cliente la diferencia**, repite subtotales en el resumen final y omite datos comerciales clave (vigencia operativa, datos del taller, tratamiento de IVA, bloque de autorización).

**Síntoma observable:** clientes pueden interpretar que se les cobra dos veces — por ejemplo, servicio «Cambio de aceite y filtro» en mano de obra **y** líneas de filtro/aceite en refacciones — o confundir subtotales repetidos con cargos adicionales.

**Impacto:** fricción en autorización, llamadas de aclaración al mostrador, menor confianza en profesionalismo del documento, dificultad para compartir por WhatsApp en móvil.

**No es un bug de cálculo:** `orden.total = subtotal_servicios + subtotal_repuestos - descuento`. El problema es **comunicación y presentación**.

---

## 3. Diagnóstico del formato actual

### 3.1 Qué existe hoy

| Capacidad | Estado |
|-----------|--------|
| PDF carta (ReportLab) | ✅ |
| Logo + título «COTIZACIÓN» | ✅ |
| Secciones MO / Refacciones | ✅ |
| Cliente + vehículo | ✅ |
| Diagnóstico / observaciones cliente | ✅ |
| Descuento (si > 0) | ✅ |
| Vigencia (`fecha_vigencia_cotizacion`) | ⚠️ Backend sí; UI no expone campo |
| IVA desglosado | ❌ (sí en ticket venta si `requiere_factura`) |
| Datos comerciales taller (tel, dirección, RFC) | ❌ |
| Preview antes de enviar | ❌ |
| Vista web / link cliente | ❌ |
| HTML imprimible | ❌ |
| Bloque firma / autorización | ❌ (solo texto genérico al pie) |

### 3.2 Hallazgos PRE-CHECK P5.4

| ID | Hallazgo | Severidad |
|----|----------|-----------|
| P5.4-D-001 | Subtotales MO/refacciones repetidos (sección + resumen final) | Alta percepción |
| P5.4-D-002 | Sin copy explicativo MO vs refacciones | Alta percepción |
| P5.4-D-003 | Total sin etiqueta «precio final» ni nota IVA | Media |
| P5.4-D-004 | Vigencia casi nunca visible (sin UI) | Media |
| P5.4-D-005 | Sin datos de contacto del taller en PDF | Media |
| P5.4-D-006 | UI detalle OT mezcla ítems sin subtotales (≠ PDF) | Media operativa |
| P5.4-D-007 | Descripciones truncadas (~55 chars servicios) | Baja |
| P5.4-D-008 | PDF carta poco legible en móvil/WhatsApp | Media UX |

### 3.3 Qué ve cada actor

| Actor | Superficie |
|-------|------------|
| **Cliente** | Solo PDF recibido por canal externo |
| **Operador** | `DetalleOrdenTrabajo`: lista 🔧/📦, total único, botón descarga |
| **Técnico** | Hoja verde (sin precios de venta) — no es entregable cliente |

---

## 4. Alcance P5.4

| # | Entregable | Fase |
|---|------------|------|
| 1 | Auditoría visual con PDFs reales anonimizados | Fase 0 |
| 2 | Copy cliente: explicación MO/refacciones, total, condiciones | Fase 1 |
| 3 | Resumen final sin subtotales duplicados | Fase 1 |
| 4 | Datos comerciales taller en PDF (tel, dirección, nombre) | Fase 1 |
| 5 | Vigencia visible (default + campo UI en edición OT) | Fase 1 |
| 6 | Bloque autorización cliente (texto + espacio firma/fecha) | Fase 1 |
| 7 | Nota IVA / «precio final estimado» alineada con política taller | Fase 1 |
| 8 | Mejoras estructura visual PDF (jerarquía, espaciado, truncado) | Fase 2 |
| 9 | Preview en UI antes de enviar (estructura ≈ PDF) | Fase 3 |
| 10 | QA con cotizaciones reales anonimizadas + checklist visual | Fase 4 |
| 11 | Documento cierre `CIERRE_P5_4_COTIZACION_CLIENTE.md` | Post Fase 4 |

**Archivos probables (referencia — no implementar en este hito documental):**

- `app/routers/ordenes_trabajo/cotizacion.py`
- `frontend/src/pages/DetalleOrdenTrabajo.jsx`
- `frontend/src/pages/OrdenesTrabajo.jsx` (campo vigencia)
- Componente nuevo opcional: `CotizacionClientePreview.jsx`

---

## 5. Fuera de alcance

| Ítem | Notas |
|------|-------|
| Performance A0 | P5.3 |
| Rediseño total ERP / design system global | Backlog |
| Portal cliente público (`/cotizacion/{token}`) | P5.4b o P6 |
| Aceptación digital con firma electrónica | Backlog |
| Unificación PDF refacción especial | Opcional post-Fase 2 |
| Cambios evaluador A0 / P4.x | Prohibido salvo bug |
| Migraciones obligatorias | No requeridas Fase 1–2 |
| Playwright E2E | Backlog |
| Modificar ticket venta (azul) | Fuera v1 — solo alinear criterio IVA en copy |

---

## 6. Principios de diseño

1. **Claridad antes que estética** — el cliente no técnico debe entender MO vs refacciones sin explicación verbal.
2. **Un solo resumen de totales** — evitar cifras repetidas que parezcan cargos duplicados.
3. **Coherencia operador ↔ cliente** — preview UI debe reflejar lo que sale en PDF.
4. **Incremental, no rediseño** — mejoras acotadas sobre ReportLab existente en Fase 1–2.
5. **Sin romper flujo cotización** — `PLAN_FLUJO_COTIZACION_COMPRA.md` intacto funcionalmente.
6. **Independencia P5.3** — sin dependencia de optimización A0.
7. **Datos comerciales mínimos** — taller identificable y contactable en todo PDF.
8. **Rollback simple** — revert commit PDF/frontend; sin migraciones obligatorias.

```text
Cliente entiende  →  MO (trabajo) + Refacciones (piezas) = Total estimado
Operador confía   →  Preview ≈ PDF antes de WhatsApp
```

---

## 7. Propuesta de mejora visual

### Fase 1 (copy + contenido, cambio mínimo layout)

- Párrafo introductorio bajo subtítulo (2–3 líneas).
- Eliminar repetición de subtotales en bloque final; un solo «Resumen».
- Pie con datos taller + línea de contacto.
- Bloque «Validez y condiciones» compacto antes del total.

### Fase 2 (estructura PDF)

- Reforzar jerarquía: cajas cliente/vehículo sin truncar datos críticos.
- Tabla MO: columnas Descripción | Cant. | Importe (sin repetir subtotal inline si ya va al resumen).
- Tabla refacciones: mantener P.unit. pero mejorar wrap (más líneas, menos truncado 55 chars).
- Total final en caja destacada (borde o fondo naranja claro).
- Paginación «continuación» con encabezado reducido en páginas 2+.

### Fase 3 (preview UI)

- Panel en `DetalleOrdenTrabajo` con mismas secciones que PDF.
- Botones: «Vista previa» | «Descargar PDF» | «Marcar enviada».
- Responsive: legible en tablet/móvil del mostrador.

**Explícitamente fuera de Fase 1–2:** cambio de tipografía corporativa, ilustraciones, QR, multi-idioma.

---

## 8. Propuesta de copy para cliente

### Párrafo introductorio (debajo de «SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ»)

> Esta propuesta detalla el trabajo recomendado para su vehículo. **Mano de obra** es el costo del servicio técnico. **Refacciones** son las piezas y materiales necesarios. Ambos conceptos se suman en un solo total; no representan un cobro duplicado.

### Etiquetas de sección

| Actual | Propuesto |
|--------|-----------|
| MANO DE OBRA | MANO DE OBRA (servicio técnico) |
| REFACCIONES | REFACCIONES (piezas y materiales) |

### Resumen final

| Línea | Copy |
|-------|------|
| Subtotal servicios | Subtotal mano de obra |
| Subtotal piezas | Subtotal refacciones |
| Descuento | Descuento aplicado (si > 0) |
| **Total** | **TOTAL ESTIMADO A PAGAR** |

### Nota IVA (elegir una política y documentar en config)

**Opción A — precios incluyen IVA (recomendada para mostrador):**

> Precios en pesos mexicanos (MXN). El total incluye IVA cuando aplique facturación.

**Opción B — sin IVA en cotización, IVA al facturar:**

> Total estimado sin IVA. En caso de requerir factura, se aplicará el impuesto correspondiente al momento del cobro.

### Pie de página

> Gracias por confiar en Medina AutoDiag. Conserve esta cotización para su referencia.  
> Tel: [TEL_TALLER] · [DIRECCION_TALLER] · [CIUDAD]

### Condiciones (bloque compacto)

> Propuesta sujeta a disponibilidad de refacciones y a variaciones detectadas durante el diagnóstico. Los precios no incluyen trabajos adicionales no listados. Vigencia indicada abajo.

---

## 9. Estructura recomendada del PDF

```text
┌─────────────────────────────────────────┐
│ [LOGO]                                  │
│ COTIZACIÓN                              │
│ SERVICIO Y DIAGNÓSTICO AUTOMOTRIZ       │
│ ─────────────────────────────────────── │
│ [Copy introductorio MO vs refacciones]  │
│ FECHA | ORDEN # | PROPUESTA             │
│ Válida hasta: DD/MM/YYYY (si aplica)    │
├─────────────────────────────────────────┤
│ CLIENTE          │ VEHÍCULO             │
├─────────────────────────────────────────┤
│ DIAGNÓSTICO / OBSERVACIONES             │
├─────────────────────────────────────────┤
│ MANO DE OBRA (servicio técnico)         │
│  Descripción          Cant.    Importe │
│  ...                                    │
├─────────────────────────────────────────┤
│ REFACCIONES (piezas y materiales)       │
│  Descripción    Cant.  P.unit.  Importe│
│  ...                                    │
├─────────────────────────────────────────┤
│ RESUMEN                                 │
│  Subtotal mano de obra        $XXX     │
│  Subtotal refacciones         $XXX     │
│  Descuento (si aplica)       -$XXX     │
│  ─────────────────────────────────     │
│  TOTAL ESTIMADO A PAGAR       $XXX     │
│  [Nota IVA según política]             │
├─────────────────────────────────────────┤
│ VALIDEZ · GARANTÍA · CONDICIONES        │
│ AUTORIZACIÓN DEL CLIENTE                │
│  Nombre: _______________               │
│  Firma:  _______________  Fecha: _____ │
├─────────────────────────────────────────┤
│ Datos taller · Tel · Dirección          │
└─────────────────────────────────────────┘
```

**Regla:** subtotales por sección **no** se repiten en el resumen si ya se listaron arriba — el resumen es la **única** consolidación numérica final.

---

## 10. Datos comerciales requeridos

| Dato | Fuente propuesta | Obligatorio Fase 1 |
|------|------------------|-------------------|
| Nombre comercial | `settings` / config estática | ✅ |
| Teléfono taller | Config o env | ✅ |
| Dirección taller | Config o env | ✅ |
| RFC (opcional v1) | Config | ⚠️ Opcional |
| Email contacto | Config | ⚠️ Opcional |
| Horario atención | Config estática en PDF | Backlog |

**Implementación sugerida (Fase 1):** variables en `app/config.py` o bloque en `/api/config` (solo lectura, sin secretos) — **sin migración** si se usan env vars existentes o constantes documentadas.

---

## 11. Vigencia, garantía y autorización

### Vigencia

| Aspecto | Actual | P5.4 Fase 1 |
|---------|--------|-------------|
| Campo BD | `fecha_vigencia_cotizacion` (Date) | Sin cambio schema |
| UI edición OT | ❌ No expuesto | ✅ Campo fecha + default 7 días |
| PDF | Solo si fecha presente | Siempre visible (fecha o default calculada) |

### Garantía

Copy estándar propuesto (no legal vinculante — revisión negocio):

> Garantía de mano de obra y refacciones instaladas según política del taller. Consulte condiciones al autorizar.

### Autorización

- Texto: *«Autorizo la realización de los trabajos y la compra de refacciones descritas, por el total estimado indicado.»*
- Espacio firma + fecha + nombre.
- **Flujo interno actual se mantiene** (botón «Autorizar» en sistema); el bloque PDF es para firma física/WhatsApp impreso.

### Anticipo

Copy opcional (si negocio lo activa):

> Anticipo requerido para iniciar: ___% · Monto: $___ (según política del taller).

Default Fase 1: **no mostrar** salvo config explícita.

### Disponibilidad de piezas

Incluido en condiciones generales (sección 8). No requiere stock en tiempo real en PDF v1.

### Tiempo estimado

Backlog Fase 2: sumar `tiempo_estimado_minutos` de servicios si está disponible en detalle OT.

---

## 12. Tratamiento de mano de obra vs refacciones

### Regla de negocio (comunicación)

| Concepto | Qué incluye | Qué NO incluye |
|----------|-------------|----------------|
| **Mano de obra** | Diagnóstico, desmontaje, instalación, pruebas, servicios del catálogo | El costo de las piezas físicas |
| **Refacciones** | Piezas, filtros, fluidos, materiales consumibles facturables | El tiempo del técnico |

### Casos que generan confusión

| Caso | Mitigación P5.4 |
|------|-----------------|
| Servicio «Cambio de aceite y filtro» + línea filtro | Copy introductorio; en MO usar descripción «Mano de obra: cambio de aceite y filtro» |
| Servicio con `requiere_repuestos=true` en catálogo | Nota al pie de sección MO: *«Las piezas necesarias se listan en Refacciones.»* |
| Cliente proporciona refacciones | Ya existe flag `cliente_proporciono_refacciones` — PDF debe omitir o marcar «Cliente suministra» en refacciones afectadas (Fase 2) |

### Validación operativa

En Fase 4, revisar **≥3 cotizaciones reales** donde MO y refacciones coexisten; criterio: cliente piloto entiende sin llamada telefónica.

---

## 13. Impacto frontend

| Archivo | Cambio | Fase |
|---------|--------|------|
| `DetalleOrdenTrabajo.jsx` | Preview cotización; opcional reordenar lista MO/refacciones | 3 |
| `OrdenesTrabajo.jsx` | Campo `fecha_vigencia_cotizacion` en formulario editar | 1 |
| Nuevo `CotizacionClientePreview.jsx` | Componente preview (opcional) | 3 |
| `Layout.jsx` / rutas | Sin cambio | — |

**Sin cambios:** Recepción, Caja, A0, Mi Taller (P5.2/P5.3 congelados).

---

## 14. Impacto backend/PDF

| Archivo | Cambio | Fase |
|---------|--------|------|
| `app/routers/ordenes_trabajo/cotizacion.py` | Copy, estructura resumen, datos taller, vigencia default, bloque autorización | 1–2 |
| `app/config.py` o config pública | Tel/dirección taller | 1 |
| `app/schemas/orden_trabajo_schema.py` | Sin cambio breaking | — |
| `app/models/orden_trabajo.py` | Sin migración obligatoria | — |
| Tests nuevos | Smoke PDF secciones presentes | 4 |

**Endpoint:** mismo `GET /api/ordenes-trabajo/{id}/cotizacion` — **sin cambio de contrato HTTP** (solo contenido PDF).

**Hoja técnico verde:** fuera de alcance v1 (no confundir con entregable cliente).

---

## 15. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|--------|-------|---------|------------|
| Copy legal insuficiente | Media | Medio | Revisión negocio antes Fase 1 GO |
| Política IVA ambigua | Media | Alto | Decisión explícita Opción A/B (sección 8) |
| Regresión layout PDF largo | Baja | Medio | Fase 0 con OT reales multilínea |
| Preview ≠ PDF | Media | Medio | Misma fuente datos; checklist Fase 4 |
| Scope creep portal cliente | Media | Medio | Fuera de alcance explícito |
| Conflicto paralelo P5.3 | Baja | Bajo | Archivos distintos; ramas separadas |
| Truncado descripciones | Media | Bajo | Fase 2 wrap mejorado |

---

## 16. Plan por fases

| Fase | Nombre | Entregables | Depende de |
|------|--------|-------------|------------|
| **0** | Auditoría visual | `docs/AUDITORIA_P5_4_COTIZACION_PDF.md` + ≥5 PDFs anonimizados + checklist | — |
| **1** | Copy y contenido | PDF: intro MO/refacciones, resumen único, vigencia, autorización, datos taller, nota IVA; UI vigencia | Fase 0 GO |
| **2** | Estructura visual PDF | Jerarquía, caja total, wrap textos, «cliente suministra» | Fase 1 PASS |
| **3** | Preview UI | Panel preview en DetalleOrdenTrabajo ≈ PDF | Fase 2 PASS |
| **4** | QA real | Review cotizaciones anonimizadas + pytest smoke PDF + cierre documental | Fases 1–3 |

### Fase 0 — Auditoría visual (prioridad inmediata)

- Recolectar PDFs prod/staging de OT con: solo MO, MO+refacciones, descuento, vigencia, muchas líneas.
- Matriz percepción cliente (escala 1–5): claridad, confianza, riesgo doble cobro.
- GO Fase 1: top 3 fricciones confirmadas por evidencia.

### Fase 1 — Copy y contenido (prioridad negocio)

- Implementar copy secciones 8–12.
- Campo vigencia en UI.
- Config datos taller.

### Fase 2 — Estructura visual PDF

- Layout según sección 9.
- Sin cambiar motor (ReportLab).

### Fase 3 — Preview UI

- Operador ve documento antes de WhatsApp.

### Fase 4 — QA

- Gate visual + regresión flujo cotizar → enviar → autorizar.

---

## 17. Criterios PASS/FAIL

### PASS global P5.4

- [ ] Fase 0 completada con evidencia archivada.
- [ ] Copy MO/refacciones presente en todo PDF nuevo.
- [ ] Resumen final **sin subtotales duplicados** respecto a secciones.
- [ ] Vigencia visible en ≥90% cotizaciones creadas tras Fase 1 (con default).
- [ ] Datos taller (tel + dirección) en pie de PDF.
- [ ] Bloque autorización con espacio firma/fecha.
- [ ] Nota IVA/precio final según política acordada.
- [ ] Preview UI disponible (Fase 3) y coherente con PDF en review.
- [ ] ≥3 cotizaciones piloto: cliente entiende sin aclaración telefónica.
- [ ] Flujo `PLAN_FLUJO_COTIZACION_COMPRA.md` sin regresión.
- [ ] pytest existentes PASS + smoke PDF nuevo PASS.

### FAIL global

- Persiste confusión doble cobro en review piloto.
- Totales PDF ≠ `orden.total` en BD.
- Regresión «Marcar cotización enviada» / autorización OT.
- Preview engañoso (cifras distintas al PDF).

---

## 18. QA visual

### Checklist Gate Visual (Fase 4)

| # | Criterio | PASS |
|---|----------|------|
| 1 | Logo y título legibles impreso y en móvil | ☐ |
| 2 | Párrafo MO vs refacciones visible | ☐ |
| 3 | Cliente y vehículo completos (no truncados críticos) | ☐ |
| 4 | Lista MO clara | ☐ |
| 5 | Lista refacciones clara | ☐ |
| 6 | Un solo bloque resumen numérico | ☐ |
| 7 | TOTAL ESTIMADO destacado | ☐ |
| 8 | Vigencia con fecha | ☐ |
| 9 | Datos taller en pie | ☐ |
| 10 | Bloque autorización presente | ☐ |
| 11 | Sin sensación doble cobro (review ≥3 usuarios) | ☐ |
| 12 | WhatsApp: PDF abrible en smartphone | ☐ |

### Gate funcional (sin cambio)

- Descarga PDF desde DetalleOrdenTrabajo.
- Permisos rol ADMIN/CAJA/TECNICO/EMPLEADO según backend actual.
- Marcar cotización enviada → estados COTIZADA / ESPERANDO_AUTORIZACION.

---

## 19. Estrategia de rollback

| Escenario | Acción |
|-----------|--------|
| PDF Fase 1–2 degrade percepción | Revert commit(s) PDF; restaurar `_generar_pdf_cotizacion` anterior |
| Preview UI confunde | Ocultar preview; mantener PDF mejorado |
| Campo vigencia UI bug | Revert solo frontend; PDF sigue con default backend |
| Prod inestable | Railway rollback a `72faaab` (último HEAD pre-P5.4 feature) |

**Sin migraciones obligatorias** → rollback = revert git + redeploy.

---

## 20. Checklist antes de implementación

### Documental

- [x] PRE-CHECK P5.4 completado — FORMATO APTO CON OBSERVACIONES
- [x] Plan P5.4 documentado (este archivo)
- [ ] Decisión IVA Opción A o B (negocio)
- [ ] Datos taller confirmados (tel, dirección)
- [ ] GO explícito Fase 0

### Técnico

- [ ] Branch `feat/p5.4-cotizacion-cliente` creado
- [ ] CI verde en `main` antes de fork
- [ ] PDFs baseline Fase 0 archivados
- [ ] Lista OT ejemplo para pruebas (IDs anonimizados)

### Operativo

- [ ] Mostrador informado del cambio de formato
- [ ] Cliente piloto acordado para Fase 4
- [ ] Ventana deploy acordada

### Prohibiciones pre-implementación

- [ ] No iniciar Fase 1 sin Fase 0 GO
- [ ] No mezclar P5.3 en mismo PR
- [ ] No rediseño total ni portal cliente en v1
- [ ] No modificar ticket venta sin autorización

---

## Anexo A — Mapa de archivos actuales

| Rol | Ruta |
|-----|------|
| PDF OT cliente | `app/routers/ordenes_trabajo/cotizacion.py` |
| PDF hoja técnico | mismo (verde, interno) |
| PDF refacción especial | `app/services/cotizacion_refaccion_pdf.py` |
| UI descarga | `frontend/src/pages/DetalleOrdenTrabajo.jsx` |
| Flujo negocio | `docs/PLAN_FLUJO_COTIZACION_COMPRA.md` |
| Ticket post-venta | `app/routers/ventas/ticket.py` (referencia IVA) |

## Anexo B — Roadmap post P5.4

| Ítem | Hito |
|------|------|
| Link público cotización | P5.4b |
| Alineación PDF refacción especial | P5.4b |
| Playwright E2E cotización | P5.x |
| Anticipo configurable en PDF | Backlog negocio |

---

*Plan P5.4 — generado tras PRE-CHECK RECOMENDADA y validación operativa junio 2026. Sin implementación ni modificación de código en este hito documental.*
