# Cierre de release — P4.1 Caja Operativa + CI-BASELINE

**Versión:** 1.0  
**Fecha:** 11 de junio de 2026  
**Estado:** ✅ **CONGELADO** — punto de partida para futuras fases  
**Entorno producción:** `https://medinaautodiag.up.railway.app`  
**Contrato vigente:** A0 v2 (`meta.version_contrato = "a0-v2"`)  
**SHA `main` al cierre:** `5e828a9` — `ci: prepare database schema before tests`

**Referencias:**

- [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md)
- [CHECKLIST_P4_0_STAGING.md](./CHECKLIST_P4_0_STAGING.md)
- [CHECKLIST_P4_1_CAJA_OPERATIVA.md](./CHECKLIST_P4_1_CAJA_OPERATIVA.md)
- [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [CIERRE_P3_1_MI_TALLER.md](./CIERRE_P3_1_MI_TALLER.md)

---

## 1. Resumen ejecutivo

Medina AutoDiag V2 alcanza un hito de **cierre operativo de mostrador** con P4.1 Caja Operativa UI desplegada en producción, apoyada en el evaluador financiero P4.0 y el contrato **A0 v2**. La caja operativa unifica en `/operaciones/caja` los tres pasos críticos del cierre financiero del Flujo A: **crear venta desde OT**, **registrar pago** y **entregar vehículo**, sin duplicar reglas de negocio en frontend.

En paralelo, **CI-BASELINE** restableció la calidad del pipeline: lint Ruff/Black en verde, tests de integración alineados y bootstrap de esquema MySQL en GitHub Actions. El workflow CI completo quedó **verde** en Run **#311**.

| Hito | Estado al cierre |
|------|------------------|
| P4.0 Evaluador Financiero / A0 v2 | ✅ Cerrado (Railway validado) |
| P4.1 Caja Operativa UI (Fases 0–4B) | ✅ Cerrado y desplegado |
| CI-BASELINE (Ruff + tests + schema CI) | ✅ Cerrado |
| GitHub Actions | ✅ Verde (Run #311) |
| Railway auto-deploy | ✅ Success |
| Playwright E2E Caja | 🔲 Fuera de alcance de este release |

**Principio arquitectónico preservado:**

```text
Backend == A0 == acciones[] == UI
```

---

## 2. Alcance implementado

### 2.1 P4.0 — Backend (prerrequisito, cerrado previamente)

| Componente | Ubicación | Función |
|------------|-----------|---------|
| Contrato A0 v2 | `app/services/operaciones_service.py` | `VERSION_CONTRATO = "a0-v2"` |
| Evaluador financiero | `app/services/acciones_operativas_service.py` | `evaluar_registrar_pago`, `evaluar_crear_venta_desde_ot`, `evaluar_entregar_vehiculo` |
| Deduplicación bandejas | `OperacionesService` | Excluye ventas OT duplicadas en `ventas_saldo_pendiente` |
| `acciones_globales` | A0 v2 | Acciones financieras `item_only`; nunca `permitida=true` en global |

Commits de referencia P4.0: `41531ae`, `86afda7` (ver [CHECKLIST_P4_0_STAGING.md](./CHECKLIST_P4_0_STAGING.md)).

### 2.2 P4.1 — Caja Operativa UI

| Fase | Alcance | Entregables principales |
|------|---------|---------------------------|
| **0** | PRE-CHECK documental | Checklist P4.1, actualización ARQUITECTURA y PLAN |
| **1** | Esqueleto + routing | `CajaOperativa.jsx`, `TurnoCajaBanner.jsx`, `BandejaVentaSection.jsx`, ruta `/operaciones/caja`, roles ADMIN/CAJA |
| **2** | Acciones desde A0 | `AccionesCajaRenderer.jsx`, `accionesCaja.js` |
| **3** | Crear venta desde OT | `FlujoCrearVentaOtModal.jsx`, `accionesCajaApi.js` |
| **4A** | Registrar pago | `FlujoRegistrarPagoModal.jsx` |
| **4B** | Entregar vehículo | `FlujoEntregarVehiculoModal.jsx` |

**Bandejas renderizadas (solo lectura + acciones):**

| UI | Bandeja A0 | Clave payload |
|----|------------|---------------|
| Por cobrar (OT) | O1 | `bandejas.ot_pendientes_cobro` |
| Listas para entrega | O2 | `bandejas.ot_listas_entrega` |
| Ventas con saldo (mostrador) | V1 | `bandejas.ventas_saldo_pendiente` |

**Restricciones respetadas en P4.1:**

- Sin cambios de contrato A0 en backend durante fases UI.
- Mutaciones **delegadas** a endpoints existentes.
- UI no evalúa permisos por rol/estado local; solo renderiza `acciones[]`.

### 2.3 CI-BASELINE

| Commit | Mensaje | Alcance |
|--------|---------|---------|
| `447e929` | `chore(ci): fix ruff baseline` | Ruff/Black en `app/` y `tests/`; `pyproject.toml` |
| `e277fb9` | `test(ci): align legacy tests with current rules` | 4 tests legacy alineados con reglas actuales |
| `5e828a9` | `ci: prepare database schema before tests` | Bootstrap `create_all` + `alembic stamp head` en job test |

---

## 3. Flujo operativo final

Superficie: **`/operaciones/caja`** — roles **ADMIN** y **CAJA** (Modo Mostrador).

Fuente de lectura única: **`GET /api/operaciones/resumen?incluir_items=true`**.

```mermaid
flowchart LR
  subgraph O1["O1 — ot_pendientes_cobro"]
    A0O1[A0: crear_venta_desde_ot / registrar_pago]
    POSTV[POST /ventas/desde-orden/{id}]
    POSTP[POST /pagos/]
  end
  subgraph O2["O2 — ot_listas_entrega"]
    A0O2[A0: entregar_vehiculo]
    POSTE[POST /ordenes-trabajo/{id}/entregar]
  end
  A0[GET /operaciones/resumen] --> O1
  A0 --> O2
  A0O1 -->|permitida| POSTV
  A0O1 -->|permitida| POSTP
  A0O2 -->|permitida| POSTE
  POSTV --> REFETCH[Refetch A0]
  POSTP --> REFETCH
  POSTE --> REFETCH
```

### 3.1 O1 — Crear venta desde OT

| Campo | Valor |
|-------|-------|
| **Bandeja** | `ot_pendientes_cobro` (O1) |
| **Condición A0** | OT `COMPLETADA` sin venta activa o con saldo pendiente |
| **Acción A0** | `crear_venta_desde_ot` con `permitida=true` |
| **Mutación** | `POST /api/ventas/desde-orden/{ordenId}?requiere_factura={bool}` |
| **UI** | `FlujoCrearVentaOtModal` — confirmación `requiere_factura` |
| **Post-condición** | Refetch A0; ítem migra según saldo (sigue en O1 o avanza hacia O2) |
| **Test golden path** | `tests/test_p41_fase3_golden_crear_venta_ot.py` |
| **Commit** | `0369c6d`, `37a7de6` |

### 3.2 O1 — Registrar pago

| Campo | Valor |
|-------|-------|
| **Bandejas** | O1 (`ot_pendientes_cobro`) y V1 (`ventas_saldo_pendiente`) |
| **Condición A0** | Venta activa, saldo > 0, turno abierto del usuario, monto válido |
| **Acción A0** | `registrar_pago` con `permitida=true` |
| **Mutación** | `POST /api/pagos/` `{ id_venta, metodo, monto, referencia? }` |
| **UI** | `FlujoRegistrarPagoModal` |
| **Bloqueos típicos** | `TURNO_CERRADO`, saldo excedido, venta inexistente |
| **Tests** | `tests/test_p41_fase4a_registrar_pago.py`, `tests/test_p40_contrato_a0_pagos.py` |
| **Commit** | `241756a` |

### 3.3 O2 — Entregar vehículo

| Campo | Valor |
|-------|-------|
| **Bandeja** | `ot_listas_entrega` (O2) |
| **Condición A0** | OT `COMPLETADA`, venta saldada, sin saldo pendiente |
| **Acción A0** | `entregar_vehiculo` con `permitida=true` |
| **Mutación** | `POST /api/ordenes-trabajo/{id}/entregar` |
| **UI** | `FlujoEntregarVehiculoModal` |
| **Roles** | ADMIN, CAJA — TECNICO rechazado |
| **Tests** | `tests/test_p41_fase4b_entregar_vehiculo.py` |
| **Commit** | `ad2e0fb` |

### 3.4 Turno de caja

El banner `TurnoCajaBanner` refleja `data.caja.turno_abierto` desde A0. Sin turno abierto, `registrar_pago` queda bloqueado en evaluador y UI. Apertura/cierre de turno permanece en módulo **`/caja`** (sin duplicar lógica en Caja Operativa).

---

## 4. Contrato A0 v2 vigente

**Versión:** `meta.version_contrato = "a0-v2"`  
**Endpoint:** `GET /api/operaciones/resumen`

### 4.1 Cambios normativos v2 (respecto a v1)

| Regla | Descripción |
|-------|-------------|
| `deduplicacion_bandejas_financieras` | Ventas vinculadas a OT en O1 no aparecen duplicadas en V1 |
| `evaluador_registrar_pago` | Turno, saldo, venta activa evaluados antes de `permitida=true` |
| `acciones_globales_alineadas` | `registrar_pago`, `crear_venta_desde_ot`, `entregar_vehiculo` son `item_only` |

### 4.2 Estructura `acciones[]` (por ítem)

| Campo | Obligatorio | Uso |
|-------|-------------|-----|
| `accion` | Sí | Código estable del catálogo |
| `permitida` | Sí | Si la mutación delegada debe aceptarse |
| `motivo_bloqueo` | Si `permitida=false` | Texto para UI |
| `codigo_bloqueo` | Si `permitida=false` | Código estable (`TURNO_CERRADO`, etc.) |
| `contexto` | Opcional | Metadatos (`id_venta`, `saldo_pendiente`, …) |

### 4.3 Invariantes contractuales (R-A1, R-A2, I-G1–I-G3)

- Toda acción mutante en superficies operativas se renderiza **solo** desde `acciones[]`.
- `permitida=true` implica que el POST delegado no fallará por reglas que el evaluador conoce.
- No existe `registrar_pago` con `permitida=true` en `acciones_globales`.

Fuente normativa: [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md).

---

## 5. Validaciones realizadas

### 5.1 Tests de integración (local)

| Suite | Resultado | Notas |
|-------|-----------|-------|
| `pytest tests/` | **172 passed** | Tras CI-BASELINE en `e277fb9` y `5e828a9` |
| P4.1 Fase 3 | Golden path crear venta | `test_p41_fase3_golden_crear_venta_ot.py` |
| P4.1 Fase 4A | Pagos parcial/total/sin turno | `test_p41_fase4a_registrar_pago.py` |
| P4.1 Fase 4B | Entrega happy path + bloqueos | `test_p41_fase4b_entregar_vehiculo.py` |
| P4.0 contrato A0 | Coherencia pagos ↔ A0 | `test_p40_contrato_a0_pagos.py` |

Reproducción entorno CI (MySQL 8.0 vacío + bootstrap):

| Escenario | Resultado |
|-----------|-----------|
| Sin schema | 72 failed — `Table 'usuarios' doesn't exist` |
| `create_all` + `alembic stamp head` | 172 passed |

### 5.2 Build frontend

| Check | Resultado |
|-------|-----------|
| `npm run build` | ✅ OK (local y CI job `build-frontend`) |
| Bundle `CajaOperativa-*.js` | Contiene acciones P4.1 (smoke post-deploy) |

### 5.3 Smoke producción (solo lectura)

Validación post-deploy Railway sin mutaciones en prod:

| Check | Resultado |
|-------|-----------|
| `GET /health` | healthy |
| `GET /api/operaciones/resumen` | `version_contrato=a0-v2` |
| Bandejas O1, O2, V1 | Presentes en payload |
| Bundle frontend P4.1 | Acciones caja en JS desplegado |

### 5.4 GitHub Actions

| Run | SHA | lint | build-frontend | test | Workflow |
|-----|-----|------|----------------|------|----------|
| **#310** | `e277fb9` | ✅ | ✅ | ❌ | BD vacía sin schema |
| **#311** | `5e828a9` | ✅ | ✅ | ✅ | **Success** |

URL Run #311: https://github.com/RamonRabago/medina_autodiag/actions/runs/27356736060

---

## 6. Riesgos residuales

| # | Riesgo | Severidad | Mitigación / nota |
|---|--------|-----------|-------------------|
| R1 | **OT-FECHAS-V1** no desplegado como hotfix dedicado | Media | Plan P4 lo marca dependencia crítica prod; P4.1 ya está en prod — monitorear edición de `fecha_promesa` |
| R2 | CI usa `create_all` + `stamp head`, prod usa `alembic upgrade head` | Media | Divergencia posible a largo plazo; considerar migración baseline real o `upgrade head` en CI cuando exista esquema from-scratch |
| R3 | Turno de caja **por usuario** (`id_usuario` del turno) | Media | Solo quien abrió turno puede cobrar; decisión de negocio — documentada en análisis ventas |
| R4 | Sin Playwright E2E de Caja Operativa | Media | Cobertura API/integration sí; flujos UI no automatizados en browser |
| R5 | Documentos CHECKLIST/ARQUITECTURA parcialmente desactualizados vs estado real P4.1 | Baja | Este cierre congela estado; actualizar referencias cruzadas en siguiente sprint doc |
| R6 | Baseline Alembic `3d82bfb3252b` es no-op | Baja | BD nueva requiere bootstrap explícito (CI ya lo hace; Railway usa preDeploy) |

---

## 7. Pendientes fuera de alcance

Explicitamente **no incluidos** en este release:

| Ítem | Tipo | Referencia |
|------|------|------------|
| **P4.2 — Flujo guiado** | UX modales ampliados | [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md) § P4.2 |
| **P4.3 — Bloqueo financiero** | Hito avanzado | Plan P4 § P4.3 |
| **HOTFIX OT-FECHAS-V1** | Hotfix fechas promesa OT | Plan P4, [CIERRE_P3_1_MI_TALLER.md](./CIERRE_P3_1_MI_TALLER.md) |
| **P5 — Dashboard por rol** | Orquestación | [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md) |
| **P6 — Refacción automática (Flujo B)** | Bandeja refacciones | Arquitectura V2 |
| **Playwright E2E** | Automatización browser | Metodología V2 — diferido |
| **Mutaciones desde módulos legacy** | Refactor UX legacy | Fuera de P4.1 MVP |

---

## 8. Decisiones arquitectónicas aprobadas

| # | Decisión | Fuente |
|---|----------|--------|
| D1 | P4.0 como extensión obligatoria de A0, no ajuste aislado | ADR P4.0 |
| D2 | Contrato **A0 v2** obligatorio (`a0-v2`); no mantener v1 en paralelo | ADR P4.0 §1.1 |
| D3 | Evaluador financiero centralizado en `acciones_operativas_service` | ADR P4.0 |
| D4 | Acciones financieras **`item_only`** en `acciones_globales` | ADR P4.0 §1.4 |
| D5 | Deduplicación O1/V1 como regla de dominio en backend | ADR P4.0 §4 |
| D6 | P4.1 UI consume **exclusivamente** A0; mutaciones delegadas | CHECKLIST P4.1 |
| D7 | Modo Mostrador: ADMIN y CAJA comparten misma UI en `/operaciones/caja` | PLAN P4 |
| D8 | Sin Alembic en P4.0/P4.1 feature (solo CI bootstrap) | PLAN P4 § restricciones |
| D9 | CI test job: `create_all` + `alembic stamp head` en BD vacía | Run #310→#311, commit `5e828a9` |
| D10 | Railway: migraciones vía `preDeployCommand` (`alembic upgrade head`) | `railway.toml` |

---

## 9. Estado actual de producción

| Campo | Valor |
|-------|-------|
| **URL** | https://medinaautodiag.up.railway.app |
| **Rama** | `main` |
| **SHA desplegado (cierre)** | `5e828a9` |
| **Contrato A0** | `a0-v2` |
| **Superficie Caja Operativa** | `/operaciones/caja` — ADMIN, CAJA |
| **Deploy** | Railway auto-deploy on push — Success |
| **Migraciones prod** | `alembic upgrade head` en preDeploy |

### Commits publicados en este release (referencia)

| SHA | Mensaje |
|-----|---------|
| `0369c6d` | feat(p4.1): add create-sale-from-OT flow in caja operativa |
| `37a7de6` | test(p4.1): golden path crear venta desde OT |
| `241756a` | feat(p4.1): registrar pago desde caja operativa |
| `ad2e0fb` | feat(p4.1): entregar vehiculo desde caja operativa |
| `447e929` | chore(ci): fix ruff baseline |
| `e277fb9` | test(ci): align legacy tests with current rules |
| `5e828a9` | ci: prepare database schema before tests |

### Mapa de superficies operativas V2 (estado al cierre)

| Ruta | Hito | Estado |
|------|------|--------|
| `/operaciones/recepcion` | Recepción rápida | ✅ Prod |
| `/operaciones/mi-taller` | P3.1 Mi Taller | ✅ Prod |
| `/operaciones/caja` | P4.1 Caja Operativa | ✅ Prod |
| `/operaciones/refacciones` | Flujo B | 🔲 Pendiente P6 |

---

## 10. Recomendaciones para la siguiente fase

### Prioridad sugerida

1. **HOTFIX OT-FECHAS-V1** — Cerrar deuda de `fecha_promesa` detectada en golden path P3.1; reduce riesgo operativo en recepción/OT antes de ampliar P4.2.
2. **Actualización documental** — Alinear `CHECKLIST_P4_1_CAJA_OPERATIVA.md` y §3.3 de `ARQUITECTURA_OPERATIVA_V2.md` con estado real (Fases 2–4B completadas).
3. **P4.2 Flujo guiado** — Modales enriquecidos sin nuevas reglas de negocio; reutilizar `accionesCajaApi.js`.
4. **Playwright smoke Caja** — Automatizar golden path O1→O2 en staging antes de P4.3.
5. **CI hardening (opcional)** — Evaluar `alembic upgrade head` from-scratch cuando exista migración baseline que cree esquema completo; hoy `create_all` es suficiente y está documentado en baseline Alembic.

### Criterios de arranque para P4.2 / P5

- Mantener invariante **A0 `permitida=true` → POST aceptado** en toda nueva acción.
- Todo cambio de bandeja o evaluador → bump de contrato o extensión documentada.
- PRE-CHECK arquitectónico antes de tocar `OperacionesService` o evaluadores.
- CI verde obligatorio antes de push a `main`.

### Qué no hacer en la siguiente iteración

- No reintroducir lógica de permisos en frontend.
- No duplicar bandejas financieras fuera de A0.
- No mezclar hitos (P5 dashboard ≠ P4.2 UX) en un solo PR.

---

## Control de versiones del documento

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-06-11 | Cierre release P4.1 + CI-BASELINE; congelación estado V2 |

---

**Veredicto de cierre:** ✅ **RELEASE P4.1 + CI-BASELINE CONGELADO** — apto como baseline para HOTFIX OT-FECHAS-V1, P4.2 o P5 según prioridad de negocio.
