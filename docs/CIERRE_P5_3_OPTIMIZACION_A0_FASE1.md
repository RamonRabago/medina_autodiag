# CIERRE P5.3 FASE 1 — OPTIMIZACIÓN A0 LIGHT (FAST PATH)

**Versión:** 1.0  
**Fecha:** 18 de junio de 2026  
**Estado:** ✅ **CERRADO EN PRODUCCIÓN** — Fase 1 liberada sin rollback  
**Entorno producción:** `https://medinaautodiag.up.railway.app`  
**Contrato vigente:** A0 v2 (`meta.version_contrato = "a0-v2"`)  
**SHA desplegado (HEAD Fase 1):** `8ab6a969d8d5f6908d245d2f04e13e7ddf6c77a6` — `feat(p5.3): activar fast path A0 light incluir_items=false Commit D`  
**build_rev prod:** `8ab6a969d8d5`  
**SHA rollback anterior:** `0d155757b31e`  
**Decisión post-deploy:** **MANTENER DEPLOY**

**Referencias:**

- [PLAN_P5_3_OPTIMIZACION_A0.md](./PLAN_P5_3_OPTIMIZACION_A0.md)
- [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)
- [CIERRE_P5_1_DASHBOARD_POR_ROL.md](./CIERRE_P5_1_DASHBOARD_POR_ROL.md)
- [CIERRE_P5_2_RECEPCION_OPERATIVA.md](./CIERRE_P5_2_RECEPCION_OPERATIVA.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

## 1. Resumen ejecutivo

P5.3 Fase 1 convierte `incluir_items=false` en un **fast path genuino** para el resumen operativo A0: las métricas se calculan con contadores SQL (`_contar_*`) en lugar de ejecutar todas las bandejas con evaluadores por fila y vaciar `items[]` al final.

### Qué se optimizó

- **`GET /api/operaciones/resumen?incluir_items=false`** — dispatcher en `construir_resumen_operativo()` hacia `_construir_resumen_metricas_rapidas()`.
- **10 métricas A0** vía contadores simples (citas, OT por estado) y financieros (O1/O2/V1).
- **Dashboard ADMIN** (único consumidor frontend con `incluirItems: false`).

### Qué no se optimizó

- **`incluir_items=true`** — sigue el camino legacy `_construir_resumen_completo()` con bandejas + evaluadores.
- **Bandejas financieras legacy** (`bandeja_ot_pendientes_cobro`, `bandeja_ot_listas_entrega`, `bandeja_ventas_saldo_pendiente`) — sin cambios.
- **Evaluadores P4.0** — sin cambios.
- **Frontend** — sin cambios (P5.1 ya consumía light).
- **Schemas, routers, `acciones[]` por ítem** — sin cambios.
- **P5.3 Fase 2** (heavy path) — pendiente.

### Endpoints impactados

| Endpoint | Modo | Cambio runtime |
|----------|------|----------------|
| `GET /api/operaciones/resumen` | `incluir_items=false` | **Fast path** (contadores SQL) |
| `GET /api/operaciones/resumen` | `incluir_items=true` | **Sin cambio** (legacy) |

### Pantallas que se benefician

| Pantalla | Ruta | Parámetro A0 | Beneficio |
|----------|------|--------------|-----------|
| **Dashboard ADMIN** | `/` | `incluir_items=false`, `limit_items=1` | Carga de contadores ~72% más rápida en prod |
| Caja Operativa | `/operaciones/caja` | `incluir_items=true` | Sin cambio de latencia (Fase 2) |
| Recepción rápida | `/operaciones/recepcion` | `incluir_items=true` | Sin cambio de latencia (Fase 2) |
| Mi Taller | `/operaciones/mi-taller` | `incluir_items=true` | Sin cambio de latencia (Fase 2) |
| Wizard Caja P4.2 | (modal en Caja) | heavy vía Caja | Sin cambio |

---

## 2. Evidencia de performance (producción)

Medición: 3 runs HTTP 200, mediana, prod `https://medinaautodiag.up.railway.app`, junio 2026.  
**Antes:** `build_rev = 0d155757b31e` (pre-Commit D).  
**Después:** `build_rev = 8ab6a969d8d5` (Commit D desplegado).

| Endpoint | Rol | ANTES | DESPUÉS | Reducción |
|----------|-----|-------|---------|-----------|
| A0 light `incluir_items=false&limit_items=1` | ADMIN | **13.46 s** | **3.92 s** | **−71%** |
| A0 light | CAJA | **13.45 s** | **3.70 s** | **−72%** |
| A0 heavy `incluir_items=true&limit_items=30` | ADMIN | **17.72 s** | **16.57 s** | −6.5% (sin degradación) |
| A0 heavy | CAJA | **17.63 s** | **16.94 s** | −3.9% (sin degradación) |

**Criterios de aceptación Fase 1:**

| Criterio | Resultado |
|----------|-----------|
| A0 light ADMIN/CAJA < 4 s | ✅ 3.92 s / 3.70 s |
| A0 heavy no empeora > 10% | ✅ Mejoró ~4–7% |
| Sin errores 500 en smoke | ✅ 12/12 runs 200 post-deploy |

**Nota:** El objetivo documental original era < 3 s; se alcanzó < 4 s en prod con margen operativo aceptable (red + infra Railway).

---

## 3. Evidencia de contrato A0

Validado en API post-deploy (ADMIN y CAJA) y en suite de paridad local (244 pytest PASS pre-deploy).

### Modo light (`incluir_items=false`)

| Campo / invariante | Estado |
|--------------------|--------|
| `meta.version_contrato = "a0-v2"` | ✅ |
| `meta.incluir_items = false` | ✅ |
| `bandejas.*.items = []` | ✅ |
| `bandejas.*.total == metricas.*` | ✅ (10 métricas) |
| `acciones_globales` presentes | ✅ |
| `caja` presente | ✅ |
| `alertas_operativas` presentes | ✅ |

### Modo heavy (`incluir_items=true`)

| Campo / invariante | Estado |
|--------------------|--------|
| `meta.incluir_items = true` | ✅ |
| Bandejas con `items[]` serializados | ✅ (30 ítems ADMIN/CAJA en smoke) |
| `acciones[]` en ítems financieros O1/O2/V1 | ✅ 8/8 con acciones (smoke prod) |
| Evaluadores P4.0 sin cambio | ✅ |

**Harness de paridad:** `tests/test_a0_metricas_paridad.py` — `test_paridad_fast_path_vs_legacy` PASS para ADMIN, CAJA, TECNICO, EMPLEADO.

---

## 4. Evidencia UI smoke (producción post-deploy)

Login ADMIN prod (`rrabago@medinaautodiag.com`). **PASS** en las cuatro pantallas operativas:

| Pantalla | Validación |
|----------|------------|
| **Dashboard ADMIN** | Contadores operativos visibles (3/4/8/1/6/4/2/2); carga perceptiblemente más rápida |
| **Caja Operativa** | O1(4), O2(2), V1(2); botones P4.2 «Continuar proceso» / «Acciones individuales» |
| **Recepción rápida** | Citas asistencia(3), convertibles(4); acciones Sí/No asistió, Completar recepción |
| **Mi Taller** | Pendientes(8), En proceso(1) con Finalizar, Completadas(6) |
| Errores console críticos | No observados en flujo probado |

---

## 5. Alcance técnico real

### Commits incluidos en el deploy

| Commit | Descripción |
|--------|-------------|
| `a195a2f` | **Commit A** — Harness paridad métricas A0 (`tests/a0_metricas_paridad.py`) |
| `df5f3e4` | **Commit B** — Contadores SQL simples (`_contar_citas_*`, `_contar_ot_*`) |
| `30d1a78` | **Commit C** — Contadores financieros O1/O2/V1 + subqueries |
| `8ab6a96` | **Commit D** — Fast path + dispatcher `construir_resumen_operativo` |

*También desplegado en el mismo push:* `10d130d` — docs P6 multi-sucursal (documentación, sin código funcional P6).*

### Archivos principales modificados (Fase 1)

| Archivo | Rol |
|---------|-----|
| `app/services/operaciones_service.py` | `_construir_resumen_metricas_rapidas`, `_construir_resumen_completo`, dispatcher |
| `tests/a0_metricas_paridad.py` | Harness legacy vs fast path |
| `tests/test_a0_metricas_paridad.py` | Gate paridad por rol |
| `tests/test_a0_contadores_simples.py` | Tests contadores B |
| `tests/test_a0_contadores_financieros.py` | Tests contadores C |

### Comportamiento runtime (post Fase 1)

```text
construir_resumen_operativo(incluir_items=false) → _construir_resumen_metricas_rapidas()  [FAST]
construir_resumen_operativo(incluir_items=true)  → _construir_resumen_completo()           [LEGACY]
```

- **P4.2 wizard** sigue alimentándose del heavy path vía Caja Operativa (`incluir_items=true`).
- **P5.3 Fase 2** — optimización `incluir_items=true` para Caja, Recepción, Mi Taller — **pendiente**.

### Validación local pre-deploy

| Check | Resultado |
|-------|-----------|
| `pytest` completo | 244 passed |
| `npm run build` | PASS |
| `python -c "from app.main import app"` | OK |
| Suite P5.3 relevante | 62 passed (paridad + contadores + resumen) |

---

## 6. Riesgos restantes

| ID | Riesgo | Severidad | Mitigación / siguiente paso |
|----|--------|-----------|------------------------------|
| **P5.3-OBS-001** | Heavy path sigue ~17 s en ADMIN/CAJA | Alta (operativa) | P5.3 Fase 2 |
| **P5.3-OBS-002** | Caja, Recepción y Mi Taller dependen de `incluir_items=true` | Alta | Fase 2 |
| **P5.3-OBS-003** | Light ~3.7–3.9 s (no sub-1 s) | Baja | Aceptable; Fase 0 script perfil opcional |
| **P5.3-OBS-004** | Commit E (`A0_FAST_METRICS` + `perfil_a0_resumen.py`) no implementado | Baja | Opcional; rollback por SHA Railway disponible |
| **P5.3-OBS-005** | Push incluyó docs P6 en mismo deploy | Baja | Sin impacto funcional |

---

## 7. Recomendación final

### Veredicto Fase 1

**P5.3 Fase 1 — PASS.** Cerrada en producción con decisión **MANTENER DEPLOY**.

### Secuencia recomendada (no iniciar sin PRE-CHECK y autorización)

1. **P5.3 Fase 2** — Optimización heavy path (`incluir_items=true`): O1/O2/V1, Caja, Recepción, Mi Taller. Objetivo prod < 8 s (stretch < 5 s).
2. **UX-1** — Sprint UX operativa (después de Fase 2 o en paralelo controlado según prioridad).
3. **P6.0** o **UX-2** — Según prioridad operativa del taller tras medir impacto de Fase 2.

### Fuera de alcance (explícito)

- ❌ P5.3 Fase 2 — no iniciada
- ❌ UX-1 — no iniciado
- ❌ Commit E — no implementado (opcional)

---

## Anexo — Dispatcher (referencia)

```python
# app/services/operaciones_service.py (Commit D)
def construir_resumen_operativo(..., incluir_items: bool = True):
    if not incluir_items:
        return _construir_resumen_metricas_rapidas(...)
    return _construir_resumen_completo(..., incluir_items=True)
```

---

*Documento de cierre — solo metodología/docs. Sin cambios funcionales adicionales respecto al deploy `8ab6a96`.*
