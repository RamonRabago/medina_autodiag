# PRE-CHECK ARQUITECTÓNICO — P5.3 Fase 2 (A0 heavy path)

**Versión:** 1.0  
**Fecha:** 22 de junio de 2026  
**Estado:** 📋 **PENDIENTE APROBACIÓN EXPLÍCITA** — no implementar hasta GO  
**Hito:** P5.3 Fase 2 — Optimización bandejas pesadas (`incluir_items=true`)  
**Baseline funcional:** P5.3 Fase 1 cerrada (`8ab6a96`) · UX-1B ON · A0 v2 + v2.1 slices  
**Plan maestro:** [PLAN_P5_3_OPTIMIZACION_A0.md](./PLAN_P5_3_OPTIMIZACION_A0.md) §12

**Relacionado:**

- [CIERRE_P5_3_OPTIMIZACION_A0_FASE1.md](./CIERRE_P5_3_OPTIMIZACION_A0_FASE1.md)
- [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md)
- [PLAN_QA_GUARDRAILS.md](./PLAN_QA_GUARDRAILS.md)

---

## PRE-CHECK ARQUITECTÓNICO — Reporte

### Componentes reutilizados

| Área | Reutilizar | Descartar |
|------|------------|-----------|
| Contadores SQL F1 | `_contar_*`, `_subquery_*`, `_query_ids_ordenes_o1` | Reescribir A0 desde cero |
| Tests paridad | `tests/test_a0_metricas_paridad.py`, `test_a0_contadores_financieros.py` | Tests nuevos duplicados |
| Evaluadores P4 | `_acciones_ot_item`, `_acciones_ot_pendientes_cobro`, `acciones_operativas_service` | Mover reglas al frontend |
| Slice A0 v2.1 | `_construir_resumen_slice`, `_hidratar_bandeja` | Romper contrato slice |

### Endpoints reutilizados

- `GET /api/operaciones/resumen` — mismo contrato JSON A0 v2
- Mutaciones — **sin cambios** (delegadas a routers existentes)

### Riesgos detectados

| Riesgo | Severidad |
|--------|-----------|
| Divergencia `total` vs ítems en O1/O2/V1 | Alta |
| Regresión wizard P4.2 (acciones[] incorrectas) | Alta |
| Divergencia slice v2.1 vs heavy optimizado | Media |
| Scope creep (Fase 3 alertas turno) | Media |

### Cumplimiento Metodología V2 / Arquitectura Operativa V2

- ✅ Backend-first; A0 solo lectura preservado
- ✅ No reabre P1–P5.1 / UX-1B cerrados
- ✅ Incremental sobre Fase 1
- ⚠️ Requiere QA Guardrails antes de smoke mutante prod
- ⛔ **NO-GO implementación** hasta aprobación explícita de este documento

---

## 1. Objetivo Fase 2

Reducir latencia de `GET /api/operaciones/resumen?incluir_items=true` para **CAJA**, **Recepción** y consumidores heavy, eliminando scans completos y N+1 en bandejas financieras O1/O2/V1 y optimizando carga OT/citas **sin cambiar semántica de evaluadores**.

### Objetivos de performance (prod)

| Rol | Baseline | Meta Fase 2 |
|-----|----------|-------------|
| ADMIN / CAJA | ~14–16 s | **< 8 s** (stretch < 5 s) |
| TECNICO | ~3 s | Mantener **< 5 s** |
| EMPLEADO | ~12–15 s (citas heavy) | **< 8 s** |

---

## 2. Funciones en `operaciones_service.py` — alcance de cambio

**Archivo único autorizado:** `app/services/operaciones_service.py`  
**Archivos relacionados solo tests:** `tests/test_a0_*`, `tests/test_operaciones_resumen.py`

### 2.1 Funciones que SE TOCARÁN (Fase 2)

| Función | Línea ref. | Cambio previsto |
|---------|------------|-----------------|
| `_iter_ot_pendientes_cobro` | ~731 | Reemplazar `q.all()` por query filtrada / subquery saldos; preservar yield semantics |
| `_ids_ordenes_ot_pendientes_cobro` | ~751 | Alinear con iterador optimizado (paridad frozenset) |
| `bandeja_ot_pendientes_cobro` | ~767 | Usar iterador optimizado; evaluadores solo en `[:limit]` |
| `bandeja_ot_listas_entrega` | ~785 | Evitar `ordenes = q.all()`; pre-filtro SQL venta pagada |
| `bandeja_ventas_saldo_pendiente` | ~817 | JOIN agregado pagos; eliminar loop N+1 `calcular_saldo_venta` |
| `_query_ot_base` | ~628 | joinedload condicional (detalles solo si evaluadores requieren) |
| `bandeja_ot_pendientes` | ~641 | Aplicar query base optimizada |
| `bandeja_ot_en_proceso` | ~671 | Idem |
| `bandeja_ot_completadas` | ~700 | Idem (ADMIN lectura) |
| `bandeja_citas_pendientes_asistencia` | ~557 | Evaluadores solo en ítems dentro de `limit` |
| `bandeja_citas_convertibles` | ~593 | Idem |
| `_construir_resumen_completo` | ~1013 | Orquestación: invocar bandejas optimizadas (sin cambiar shape respuesta) |
| `calcular_saldo_venta` | ~164 | Posible helper batch para V1/O2 — **sin cambiar firma pública** |

**Helpers SQL existentes F1 a reutilizar/extender:**

- `_subquery_venta_activa_por_orden_agg`
- `_subquery_saldos_venta`
- `_query_ids_ordenes_o1`
- `_contar_ot_pendientes_cobro`, `_contar_ot_listas_entrega`, `_contar_ventas_saldo_pendiente`

### 2.2 Funciones que NO SE TOCARÁN

| Función / área | Motivo |
|----------------|--------|
| `_construir_resumen_metricas_rapidas` | Fase 1 cerrada — fast path |
| `construir_resumen_operativo` dispatcher | Solo wiring mínimo si unavoidable |
| `validar_params_slice`, `_construir_resumen_slice`, `_hidratar_bandeja` | UX-1B / A0 v2.1 — congelado salvo bug |
| `_acciones_ot_item`, `_acciones_ot_pendientes_cobro`, `_acciones_cita_item` | Evaluadores P4.0 — reglas negocio |
| `acciones_globales_por_rol` | Contrato acciones globales |
| `alertas_operativas`, `_resumen_inventario_alertas`, `_info_caja` | Fuera alcance F2 |
| `app/routers/operaciones.py` | Sin cambio API |
| **Frontend completo** | Prohibido en F2 |
| **Alembic / migraciones** | Prohibido salvo índices en fase separada autorizada |
| **P4.2 modales / Caja UI** | Solo regresión |

### 2.3 Bandejas A0 heavy optimizadas

| Bandeja | Key | Rol principal | Prioridad optimización |
|---------|-----|---------------|------------------------|
| Pendientes cobro | `ot_pendientes_cobro` (O1) | CAJA, ADMIN | **Crítica** |
| Listas entrega | `ot_listas_entrega` (O2) | CAJA, ADMIN | **Crítica** |
| Ventas saldo | `ventas_saldo_pendiente` (V1) | CAJA, ADMIN | **Crítica** |
| OT pendientes | `ot_pendientes` | Todos | Media |
| OT en proceso | `ot_en_proceso` | TECNICO, ADMIN | Media |
| OT completadas | `ot_completadas` | TECNICO, ADMIN | Baja |
| Citas asistencia | `citas_pendientes_asistencia` | Recepción | Media |
| Citas convertibles | `citas_convertibles` | Recepción | Media |

**Consumidores frontend (sin cambio en F2):**

| Pantalla | Query |
|----------|-------|
| Caja Operativa | `incluir_items=true`, limit 30 |
| Recepción Rápida | `incluir_items=true`, limit 30 |
| Mi Taller (legacy path) | heavy si flag OFF; slices si UX-1B ON |
| Wizard P4.2 | Resumen vía Caja |

---

## 3. Riesgos de divergencia A0 v2 / v2.1

| Escenario | Mitigación |
|-----------|------------|
| `metricas.total` ≠ `bandejas.*.total` tras F2 | Tests paridad existentes + nuevos casos borde |
| O1/V1 deduplicación rota | `test_u5_v1_no_duplica_venta_ot_en_o1`, `test_slice_v1_dedup_*` |
| Slice `bandejas=ot_*` ≠ heavy item fields | `test_paridad_slice_bandeja_individual_vs_heavy` |
| `acciones[]` distintas post-optimización | `test_p42_flujo_guiado_caja.py`, `test_acciones_operativas_service.py` |
| `meta.version_contrato` | Permanece `"a0-v2"` — sin breaking changes |

**Regla:** optimizar **cuándo** y **cómo** se cargan datos; **no** qué decide el evaluador.

---

## 4. Tests de paridad requeridos (GO gate)

### 4.1 Existentes — deben seguir PASS

| Archivo | Cobertura |
|---------|-----------|
| `tests/test_a0_metricas_paridad.py` | Fast vs legacy; bandejas total vs metricas light |
| `tests/test_a0_contadores_financieros.py` | O1/O2/V1 fixtures U3–U6 |
| `tests/test_a0_contadores_simples.py` | Citas + OT contadores |
| `tests/test_a0_slices_v21.py` | Slice vs heavy paridad |
| `tests/test_operaciones_resumen.py` | Contrato API |
| `tests/test_p42_flujo_guiado_caja.py` | Regresión Caja wizard |
| `tests/test_acciones_operativas_service.py` | Evaluador financiero |

### 4.2 Nuevos / extendidos (Fase 2)

| Test | Objetivo |
|------|----------|
| Paridad O1 ítems: legacy iter vs optimizado | Mismo `total`, mismos ids en limit |
| Paridad O2 ítems | Lista entrega equivalente |
| Paridad V1 ítems + dedup O1 | Sin duplicados cross-bandeja |
| Performance harness (opcional) | Timing relativo local — no CI blocker |
| `acciones[]` byte-stable en fixture golden | Mismo permitida/motivo pre/post |

**Comando mínimo pre-deploy:**

```powershell
.\venv\Scripts\Activate.ps1
python -c "from app.main import app; print('OK')"
pytest tests/test_a0_metricas_paridad.py tests/test_a0_contadores_financieros.py tests/test_a0_slices_v21.py tests/test_operaciones_resumen.py tests/test_p42_flujo_guiado_caja.py -q
```

---

## 5. Plan de commits incremental (propuesto)

| Commit | Contenido | Riesgo |
|--------|-----------|--------|
| **F2-A** | O1: `_iter_ot_pendientes_cobro` + tests paridad | Medio |
| **F2-B** | O2: `bandeja_ot_listas_entrega` + tests | Medio |
| **F2-C** | V1: `bandeja_ventas_saldo_pendiente` + tests | Medio |
| **F2-D** | OT `_query_ot_base` joinedload condicional | Medio-bajo |
| **F2-E** | Citas limit-aware evaluadores | Bajo |
| **Docs** | `CIERRE_P5_3_FASE2.md` o sección en plan | — |

**Un commit por área** — facilita bisect y rollback.

---

## 6. Plan de rollback

| Nivel | Acción | Tiempo |
|-------|--------|--------|
| **L1** | Revert commit F2-x en `main` + redeploy Railway | ~10 min |
| **L2** | Revert rango F2-A..E completo | ~10 min |
| **L3** | Flag no existe para F2 — rollback = git revert únicamente | — |

**Sin migraciones** → rollback limpio sin Alembic down.

**Validación post-rollback:** latencia vuelve a baseline; tests PASS; smoke read-only prod.

---

## 7. Smoke plan — solo lectura (prod)

**Prohibido** mutaciones OT en smoke F2 salvo [PLAN_QA_GUARDRAILS.md](./PLAN_QA_GUARDRAILS.md) implementado.

### 7.1 Pre-deploy (local/staging)

- pytest suite §4
- `npm run build` — sin cambios frontend, debe PASS igual

### 7.2 Post-deploy prod (read-only)

| # | Check | Rol | Criterio |
|---|-------|-----|----------|
| S1 | `GET /health` | — | healthy + DB connected |
| S2 | `GET /api/config` | — | `build_rev` nuevo |
| S3 | `GET /operaciones/resumen?incluir_items=false` | ADMIN | < 3 s; metricas presentes |
| S4 | `GET /operaciones/resumen?incluir_items=true&limit_items=30` | CAJA | **< 8 s**; bandejas O1/O2/V1 shape OK |
| S5 | Idem | EMPLEADO | citas bandejas presentes |
| S6 | `incluir_items=true` | TECNICO | < 5 s; ot_* OK |
| S7 | Spot check `acciones[]` | CAJA | 1 ítem O1: campos permitida/motivo presentes |
| S8 | Mi Taller slices ON | TECNICO | `incluir_items=false` + bandejas — sin regresión UX-1B |

**Medición:** registrar tiempos antes/después en tabla (no commitear credenciales).

---

## 8. Criterios GO / NO-GO

### GO — implementación Fase 2

- [ ] Este PRE-CHECK **aprobado explícitamente** por usuario
- [ ] QA Guardrails P0 **implementado** (mínimo `smoke_p31` protegido)
- [ ] Baseline tiempos prod documentados (S4 CAJA antes)
- [ ] Plan commits F2-A..E aceptado
- [ ] Confirmación: **sin cambios frontend/BD/Alembic**

### NO-GO — detener

- [ ] Cualquier cambio a evaluadores P4.0 “por conveniencia”
- [ ] Paridad tests fallando en O1/O2/V1
- [ ] Propuesta de migración índices sin ADR separado
- [ ] Mezcla Fase 2 + Fase 3 alertas turno en mismo commit
- [ ] Smoke mutante prod sin guardrails

---

## 9. Fuera de alcance Fase 2

- P5.3 Fase 3 (`caja.alertas_turno[]`)
- P5.3 Fase 4 frontend alertas
- Extender UX-1B slices a Caja/Recepción
- P5.4 PDF cotización
- P6 / P6.0
- Cache Redis
- Índices BD (fase opcional separada con EXPLAIN)

---

## 10. Veredicto PRE-CHECK

| Campo | Valor |
|-------|-------|
| **Arquitectura** | ✅ Alineada V2 — extensión incremental F1 |
| **Reutilización** | ✅ Contadores y tests existentes |
| **Riesgo** | ⚠️ Medio-alto en O1/O2/V1 — mitigable con paridad |
| **Implementación** | ⛔ **BLOQUEADA** hasta GO explícito |
| **Prerequisito P0** | QA Guardrails antes de smoke mutante |

---

**Siguiente paso tras aprobación:** implementar commit **F2-A** (O1) únicamente, validar tests, reportar diff antes de F2-B.

*Documento PRE-CHECK — no autoriza código por sí solo.*
