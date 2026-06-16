# PLAN P5.3 — OPTIMIZACIÓN A0

**Versión:** 1.0  
**Fecha:** 16 de junio de 2026  
**Estado:** 📋 **PLAN APROBADO PARA IMPLEMENTACIÓN** — pendiente Fase 0 (medición) y autorización explícita por fase  
**Baseline HEAD:** `afc34ba31d2a111763286233b240b6eaa3f193e0`  
**Baseline funcional P5.2:** `9a5d2cdf4a8592615e64053081b52d665131b794`  
**Contrato vigente:** A0 v2 (`meta.version_contrato = "a0-v2"`)  
**PRE-CHECK P5.3:** ✅ **RECOMENDADA** (junio 2026)

**Relacionado:**

- [PLAN_P5_DASHBOARD_POR_ROL.md](./PLAN_P5_DASHBOARD_POR_ROL.md)
- [PLAN_P5_2_RECEPCION_OPERATIVA.md](./PLAN_P5_2_RECEPCION_OPERATIVA.md)
- [CIERRE_P5_2_RECEPCION_OPERATIVA.md](./CIERRE_P5_2_RECEPCION_OPERATIVA.md)
- [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)
- [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)

---

## 1. Contexto

Medina AutoDiag V2 tiene la **Capa Operativa Central A0** desplegada y consumida por Dashboard ADMIN (P5.1), Mi Taller (P3.1), Caja Operativa (P4.x) y Recepción Operativa Enriquecida (P5.2). Todos los módulos operativos dependen de:

```http
GET /api/operaciones/resumen?limit_items=N&incluir_items=true|false
```

Tras el cierre estable de P5.2, la validación base controlada y el PRE-CHECK P5.3 identificaron que la latencia de A0 en producción (~11–16 s para ADMIN/CAJA) **no se debe principalmente a frontend ni red**, sino al diseño actual de `construir_resumen_operativo` en `app/services/operaciones_service.py`.

**Hallazgo clave:** el parámetro `incluir_items=false` — introducido en P5.1 para un dashboard «ligero» — **solo omite serializar `bandejas.*.items[]`**, pero **no evita** las consultas y evaluaciones pesadas que calculan `metricas.*.total`, especialmente en bandejas financieras O1/O2/V1.

P5.3 aborda este gap como hito **backend-first**, con extensiones aditivas opcionales al contrato y frontend mínimo al final.

---

## 2. Baseline actual

| Campo | Valor |
|-------|-------|
| **HEAD documental** | `afc34ba31d2a111763286233b240b6eaa3f193e0` |
| **Feature P5.2** | `9a5d2cdf4a8592615e64053081b52d665131b794` |
| **Cierre P5.2** | `afc34ba31d2a111763286233b240b6eaa3f193e0` |
| **build_rev prod** | `afc34ba31d2a` |
| **Contrato** | A0 v2 |
| **QA V2** | APP ESTABLE CON OBSERVACIONES |
| **Gates P5.2** | Gate 1 PASS · Gate 2 PASS · Gate 3 PASS CON OBSERVACIONES |
| **pytest** | 185 passed (baseline junio 2026) |
| **Entorno prod** | `https://medinaautodiag.up.railway.app` — Railway/CI verdes |

### Tiempos A0 en producción (baseline medido)

| Rol | `incluir_items=false` | `incluir_items=true` |
|-----|----------------------|----------------------|
| ADMIN | ~12 s | ~15–16 s |
| CAJA | ~12 s | ~14–15 s |
| TECNICO | ~3 s | ~3 s |

---

## 3. Observaciones que motivan P5.3

| ID | Observación | Relación P5.3 |
|----|-------------|---------------|
| **P5.2-OBS-001** | Latencia A0 `incluir_items=true` ~20–30 s UI (~15 s API) | Objetivo principal Fase 2 |
| **P5.2-OBS-005** | Latencia A0 `incluir_items=false` ~11–12 s (dashboard «ligero») | Objetivo principal Fase 1 |
| **P5.1-OBS-001** | Turno caja por usuario (ADMIN vs CAJA) | Motivador Fase 3 (`alertas_turno[]`) |
| P5.1-OBS-002 | EMPLEADO sin usuario prod | Fuera de P5.3 (higiene operativa) |
| P5.2-OBS-002 | Solapamiento citas en bandejas | Sin cambio P5.3 (contrato A0) |
| P5.2-OBS-004 | PATCH asistencia no smokeado prod | Fuera de P5.3 (QA operativa) |

---

## 4. Diagnóstico A0

### 4.1 Comportamiento actual de `incluir_items`

En `construir_resumen_operativo` (`operaciones_service.py`):

1. Se invocan **todas** las funciones `bandeja_*` relevantes al rol, pasando `limit = limit_items if incluir_items else 0`.
2. Al final, `items` se vacían si `incluir_items=false` (L760–792).
3. **`metricas.*.total` se calcula siempre** con el trabajo completo de cada bandeja.

### 4.2 Cuellos de botella identificados

| Área | Síntoma | Causa en código | Impacto |
|------|---------|----------------|---------|
| **O1 — ot_pendientes_cobro** | Lento incluso sin ítems | `_iter_ot_pendientes_cobro`: `q.all()` sobre **todas** OT COMPLETADAS + query venta/saldo por OT | **Crítico** |
| **O2 — ot_listas_entrega** | Idem | `bandeja_ot_listas_entrega`: `q.all()` COMPLETADAS + evaluación saldo c/u | **Crítico** |
| **V1 — ventas_saldo_pendiente** | Idem | `bandeja_ventas_saldo_pendiente`: **todas** ventas + `calcular_saldo_venta` (N+1 pagos) | **Crítico** |
| **Citas bandejas** | Moderado con ítems | `count()` + loop evaluadores por cita | Medio |
| **OT bandejas** | Moderado con ítems | `_query_ot_base` joinedload detalles servicio/repuesto + evaluadores | Medio |
| **TECNICO rápido** | ~3 s | Sin O1/O2/V1; filtro `tecnico_id` | Confirma diagnóstico |
| **Alertas operativas** | Siempre | `_resumen_inventario_alertas` + lógica métricas | Bajo-medio |

### 4.3 Conclusión diagnóstica

> **`incluir_items=false` no es un modo «ligero» real.** Es un modo «sin serializar ítems» que sigue pagando el costo computacional de bandejas financieras completas.

P5.3 debe introducir un **fast path de métricas** genuino, separado del camino de bandejas con evaluadores.

---

## 5. Alcance

| # | Entregable | Fase |
|---|------------|------|
| 1 | Script/medición timing por sub-función A0 | Fase 0 |
| 2 | Fast path `incluir_items=false`: contadores SQL sin evaluadores ni scans completos | Fase 1 |
| 3 | Optimización O1/O2/V1: agregaciones SQL, eliminar N+1 saldos | Fase 2 |
| 4 | joinedload OT condicional (solo cuando hay evaluadores) | Fase 2 |
| 5 | `caja.alertas_turno[]` estructurado (aditivo) | Fase 3 |
| 6 | Consumo frontend mínimo de alertas turno | Fase 4 |
| 7 | Tests paridad métricas vs bandejas + gates QA | Fase 5 |
| 8 | Documento cierre `CIERRE_P5_3_OPTIMIZACION_A0.md` | Post Fase 5 |

**Consumidores A0 a preservar:**

| Consumidor | Query actual | Beneficio esperado |
|------------|--------------|-------------------|
| Dashboard ADMIN | `limit_items=1`, `incluir_items=false` | Fase 1 — mayor impacto |
| Recepción Operativa | `limit_items=30`, `incluir_items=true` | Fase 2 — bandejas citas |
| Caja Operativa | `limit_items=30`, `incluir_items=true` | Fase 2 — O1/O2/V1 |
| Mi Taller | `limit_items=30`, `incluir_items=true` | Fase 2 — OT bandejas |

---

## 6. Fuera de alcance

| Ítem | Notas |
|------|-------|
| Dashboard CAJA en `/` (P5.2b) | Backlog negocio |
| Playwright E2E (P5.4) | Backlog |
| Refacciones / Flujo B (P6) | Backlog |
| Nav redesign | Backlog |
| Cambios evaluador P4.0 (reglas negocio) | Prohibido salvo bug demostrado |
| Modificar P5.2 / P5.1 / P4.x funcionalmente | Solo regresión |
| Crear usuario EMPLEADO prod | Higiene operativa |
| Mutaciones nuevas en `/api/operaciones/*` | A0 sigue solo lectura |
| Cache Redis / CDN | Fuera v1 P5.3 |
| Reescritura total de A0 | Incremental por fases |

---

## 7. Principios de diseño

1. **Backend == A0 == acciones[] == UI** — no mover reglas de negocio al frontend.
2. **Separar métricas de bandejas** — contadores baratos ≠ ítems con evaluadores.
3. **Backward compatibility** — mismo JSON shape en v2; campos nuevos aditivos en v2.1.
4. **No romper evaluadores P4** — optimizar *cuándo* invocar, no *qué* deciden.
5. **Paridad verificable** — `metricas.total` debe coincidir con `bandeja.total` en fixtures.
6. **Fases pequeñas** — cada fase commiteable, testeable y desplegable.
7. **Medición antes de optimizar** — Fase 0 obligatoria con GO explícito.
8. **Rollback simple** — feature flag interno o revert commit; sin migraciones obligatorias Fase 1–2.

```text
incluir_items=false  →  fast path métricas (Fase 1)
incluir_items=true   →  bandejas + evaluadores optimizados (Fase 2)
```

---

## 8. Contrato A0 v2 / posible v2.1

### 8.1 Contrato actual (A0 v2 — congelado)

| Campo | Descripción |
|-------|-------------|
| `meta.version_contrato` | `"a0-v2"` |
| `meta.limit_items` | int 1–50 |
| `meta.incluir_items` | bool |
| `metricas` | 10 contadores |
| `bandejas` | 8 × `{ total, items[] }` |
| `alertas_operativas[]` | `{ codigo, severidad, mensaje, cantidad }` |
| `caja` | `{ turno_abierto, id_turno, alerta_turno_largo }` |
| `acciones_globales[]` | Sesión + financieras `item_only` |

### 8.2 Estrategia de versión

| Fase | Versión contrato | Cambio |
|------|------------------|--------|
| Fase 1–2 | **a0-v2** (sin cambio) | Optimización interna; mismo JSON |
| Fase 3 (opcional) | **a0-v2.1 aditivo** | Nuevos campos; consumidores v2 ignoran |

### 8.3 Campos candidatos v2.1 (aditivos)

| Campo | Tipo | Obligatorio |
|-------|------|-------------|
| `meta.modo` | `"metricas"` \| `"completo"` | No — default implícito |
| `caja.alertas_turno[]` | `{ codigo, severidad, mensaje }` | No — fallback a bool existente |

**Prohibido en P5.3:** renombrar/eliminar campos v2; cambiar semántica de `acciones[]`; breaking changes en evaluadores.

---

## 9. Plan por fases (resumen)

| Fase | Nombre | Tipo | Depende de |
|------|--------|------|------------|
| **0** | Medición | Docs + script | — |
| **1** | A0 ligera | Backend | Fase 0 GO |
| **2** | Bandejas pesadas | Backend | Fase 1 PASS |
| **3** | Alertas turno | Backend + schema aditivo | Fase 2 PASS (opcional paralelo) |
| **4** | Frontend mínimo | Frontend | Fase 3 |
| **5** | QA / smoke | Validación | Fases 1–4 |

---

## 10. Fase 0 — Medición obligatoria

**Objetivo:** Baseline cuantitativo antes de cualquier cambio de código productivo.

### Entregables

| # | Entregable |
|---|------------|
| 1 | Script `scripts/perfil_a0_resumen.py` (timing por `bandeja_*`) |
| 2 | Informe `docs/PERFIL_A0_BASELINE.md` o sección en plan de cierre |
| 3 | EXPLAIN de queries O1/O2/V1 en staging/prod read-only |
| 4 | Tabla % tiempo por función × rol × `incluir_items` |

### Criterio GO Fase 1

- Top 3 funciones responsables de >70% del tiempo identificadas.
- Confirmación empírica de que O1/O2/V1 dominan en ADMIN/CAJA con `incluir_items=false`.

**Sin GO de Fase 0 → no iniciar Fase 1.**

---

## 11. Fase 1 — Optimización A0 ligera

**Objetivo:** Hacer `incluir_items=false` genuinamente ligero.

### Cambios previstos (backend only)

| Cambio | Descripción |
|--------|-------------|
| Fast path métricas | Rama en `construir_resumen_operativo` cuando `not incluir_items` |
| Contadores SQL | `COUNT(*)` / subqueries agregadas por bandeja — sin evaluadores |
| Skip O1/O2/V1 scans | No invocar `_iter_ot_pendientes_cobro` completo ni loop ventas |
| Skip joinedload OT | No cargar detalles si no hay ítems |
| Alertas opcionales | Evaluar skip `_resumen_inventario_alertas` en fast path (decisión Fase 0) |

### Objetivo performance prod

| Rol | `incluir_items=false` |
|-----|-------------------------|
| ADMIN / CAJA | **< 3 s** (desde ~12 s) |
| TECNICO | Mantener ~3 s |

### Tests nuevos

- Paridad `metricas.*` fast path vs bandejas completas en fixtures transaccionales.
- Regresión `test_operaciones_resumen.py` — 19+ tests existentes PASS.

### Frontend

**Sin cambios** — Dashboard sigue usando `incluir_items=false`.

---

## 12. Fase 2 — Optimización bandejas pesadas

**Objetivo:** Reducir latencia `incluir_items=true` para Recepción, Caja y Mi Taller.

### Cambios previstos

| Área | Optimización |
|------|--------------|
| O1 | Query SQL filtrada COMPLETADA + saldo; evitar `q.all()` |
| O2 | Misma estrategia; pre-filtro ventas pagadas |
| V1 | JOIN agregado pagos; eliminar N+1 `calcular_saldo_venta` |
| OT `_query_ot_base` | joinedload detalles solo si contexto requiere evaluadores |
| Citas | Evaluadores solo en ítems dentro de `limit` |

### Objetivo performance prod

| Rol | `incluir_items=true` |
|-----|----------------------|
| ADMIN / CAJA | **< 8 s** (stretch < 5 s) |
| TECNICO | Mantener < 5 s |

### Riesgo principal

Divergencia entre contadores Fase 1 y ítems Fase 2 — mitigar con tests paridad.

---

## 13. Fase 3 — Alertas turno estructuradas

**Objetivo:** Resolver ambigüedad P5.1-OBS-001 con array estructurado aditivo.

### Cambio propuesto

Extender bloque `caja`:

```json
{
  "turno_abierto": true,
  "id_turno": 1,
  "alerta_turno_largo": false,
  "alertas_turno": [
    { "codigo": "TURNO_ABIERTO", "severidad": "info", "mensaje": "..." }
  ]
}
```

### Reglas

- Campos v2 existentes **sin eliminar**.
- `meta.version_contrato = "a0-v2.1"` solo si se documenta formalmente; consumidores v2 ignoran `alertas_turno`.
- Sin cambio en evaluador financiero P4.

---

## 14. Fase 4 — Frontend mínimo

**Objetivo:** Consumir `alertas_turno[]` si presente.

| Archivo | Cambio |
|---------|--------|
| `TurnoCajaBanner.jsx` | Preferir `alertas_turno[]`; fallback a bool |
| `DashboardOperativoSection.jsx` | Idem |

**Sin cambios** en `useOperacionesResumen` salvo que Fase 1–2 requieran param opcional documentado.

---

## 15. Fase 5 — QA / smoke

| Actividad | Descripción |
|-----------|-------------|
| pytest completo | 185+ tests PASS |
| Tests paridad métricas | Nuevos en Fase 1 |
| `npm run build` | PASS |
| Gate 1 funcional | A0 fast/heavy + acciones[] |
| Gate 2 regresión | Dashboard, Recepción, Caja, Mi Taller |
| Gate 3 smoke prod | Tiempos antes/después; solo lectura |
| Documento cierre | `CIERRE_P5_3_OPTIMIZACION_A0.md` |

---

## 16. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|--------|-------|---------|------------|
| Contadores fast ≠ bandejas full | Media | Alto | Tests paridad; smoke comparativo |
| Regresión Caja P4.2 wizard | Media | Alto | No tocar evaluadores; P4.2 tests |
| Scope creep | Media | Medio | Plan acotado; fuera de alcance explícito |
| Optimización sin medición | Baja | Medio | Fase 0 bloqueante |
| Índices BD prematuros | Baja | Medio | EXPLAIN Fase 0; migración opcional separada |
| v2.1 mal consumido | Baja | Bajo | Campos aditivos; fallback bool |

---

## 17. Criterios PASS/FAIL

### PASS global P5.3

- [ ] Fase 0 completada con informe de perfil.
- [ ] Fase 1: A0 `incluir_items=false` ADMIN/CAJA **< 3 s** prod.
- [ ] Fase 2: A0 `incluir_items=true` ADMIN/CAJA **< 8 s** prod (mejora ≥ 40%).
- [ ] Paridad `metricas` vs bandejas en tests.
- [ ] 185+ pytest PASS; build frontend PASS.
- [ ] Gates 1–3 PASS.
- [ ] Sin regresión acciones[] en Caja/Mi Taller/Recepción.
- [ ] Contrato v2 intacto (v2.1 solo aditivo).

### FAIL global

- Divergencia métricas/contadores detectada en prod o tests.
- Regresión P4.x/P5.x funcional.
- Latencia sin mejora measurable post-Fase 1.
- Breaking change en contrato v2 sin migración consumidores.

---

## 18. Estrategia de rollback

| Escenario | Acción |
|-----------|--------|
| Fase 1 degrade contadores | Revert commit Fase 1; A0 vuelve a comportamiento actual |
| Fase 2 rompe Caja | Revert Fase 2; mantener Fase 1 si estable |
| v2.1 confunde frontend | Frontend ignora campos nuevos; revert Fase 3–4 |
| Prod inestable post-deploy | Railway rollback a `afc34ba` (último release estable P5.2) |

**Sin migraciones obligatorias Fase 1–2** → rollback = revert git + redeploy.

---

## 19. Gates QA

| Gate | Alcance | PASS | FAIL |
|------|---------|------|------|
| **Gate 1 — Funcional** | Fast path; bandejas items; paridad métricas; acciones[] | Tests A0/P4 + nuevos paridad PASS | Contadores wrong; acciones rotas |
| **Gate 2 — Regresión** | Dashboard, Recepción, Caja, Mi Taller, Citas, OT | 185 pytest + build OK | Cualquier FAIL módulo P3–P5 |
| **Gate 3 — Smoke prod** | Solo lectura; tiempos; permisos | A0 light < 3 s; heavy mejora ≥40%; sin 5xx | Regresión permisos; sin mejora; 5xx |

---

## 20. Checklist antes de implementación

### Documental

- [x] PRE-CHECK P5.3 completado — RECOMENDADA
- [x] Plan P5.3 documentado (este archivo)
- [ ] GO explícito negocio/técnico por fase
- [ ] Baseline perfil Fase 0 archivado

### Técnico

- [ ] Branch `feat/p5.3-a0-optimizacion` creado
- [ ] CI verde en `main` antes de fork
- [ ] Script perfil Fase 0 ejecutado en staging/prod read-only
- [ ] Tests paridad diseñados (lista casos en Fase 0)

### Operativo

- [ ] Ventana deploy acordada (Railway auto-deploy)
- [ ] Smoke prod pre-cambio documentado (tiempos baseline)
- [ ] Rollback plan comunicado

### Prohibiciones pre-implementación

- [ ] No iniciar Fase 1 sin Fase 0 GO
- [ ] No tocar evaluadores P4.0
- [ ] No breaking changes contrato v2
- [ ] No mezclar P5.2b / P5.4 / P6 en este hito

---

## Anexo A — Archivos backend probables (referencia)

| Archivo | Fases |
|---------|-------|
| `app/services/operaciones_service.py` | 1, 2, 3 |
| `app/schemas/operaciones_schema.py` | 3 |
| `app/routers/operaciones.py` | 1 (opcional param) |
| `tests/test_operaciones_resumen.py` | 1, 2 |
| `tests/test_a0_metricas_paridad.py` (nuevo) | 1 |

## Anexo B — Archivos frontend probables (referencia)

| Archivo | Fases |
|---------|-------|
| `frontend/src/components/operaciones/TurnoCajaBanner.jsx` | 4 |
| `frontend/src/components/dashboard/DashboardOperativoSection.jsx` | 4 |

## Anexo C — Roadmap post P5.3

| Ítem | Hito |
|------|------|
| Playwright E2E | P5.4 |
| Dashboard CAJA `/` | P5.2b |
| Refacciones Flujo B | P6 |
| Índices BD compuestos | Opcional post-Fase 0 |

---

*Plan P5.3 — generado tras PRE-CHECK RECOMENDADA y validación base controlada. Sin implementación ni commit de código productivo en este hito documental.*
