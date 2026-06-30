# PLAN — Dashboard V2 (Centro de Decisión ADMIN)

**Versión:** 1.0  
**Fecha:** 30 de junio de 2026  
**Estado:** 🔒 **CONGELADO** — mandato Chief Software Architect (CSA)  
**Alcance:** Dashboard ADMIN en `/` — asistente de decisión operativa  
**Baseline:** P5.1 cerrado · A0 v2 · Timezone America/Matamoros Fases 1–3 · `dashboard_agregado.py` vigente  

**Relacionado:**

- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [PLAN_P5_DASHBOARD_POR_ROL.md](./PLAN_P5_DASHBOARD_POR_ROL.md)
- [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)
- [TIMEZONE_POLICY.md](./TIMEZONE_POLICY.md)

---

## Veredicto y congelamiento

| Criterio | Decisión |
|----------|----------|
| **Dirección Dashboard V2** | ✅ **GO** — Centro de decisión, no pared de KPIs |
| **Iteraciones arquitectónicas** | 🔒 **Cerradas** — no hay iteración 5 |
| **Endpoint único** | ✅ `GET /api/dashboard` |
| **Endpoint `/api/dashboard/control`** | ❌ **Rechazado permanentemente** |
| **`DecisionEngine` / motor genérico** | ❌ **Rechazado** |
| **Servicios nuevos por nombre** | ❌ **Rechazado** — extender módulo actual |
| **Caché / versionado de contrato adicional** | ❌ **Fuera de V2** |
| **Frontend calcula prioridades** | ❌ **Prohibido** |

### Principio rector (congelado)

> **El Dashboard no muestra datos. Recomienda la siguiente acción.**

El administrador, al entrar al dashboard, debe saber en **menos de 5 segundos** qué debe hacer primero para mejorar la operación del taller.

El Dashboard es un **sistema de soporte para la toma de decisiones**, no una pantalla saturada de métricas.

---

## 1. Objetivo

### 1.1 Problema actual

El dashboard ADMIN (`frontend/src/pages/Dashboard.jsx` + `GET /api/dashboard`) hoy:

- Presenta 15–18 tarjetas KPI en grid plano.
- Ejecuta en cada mount cálculos pesados (utilidad N+1, cuentas por pagar iterativas, inventario detallado) aunque el usuario no los necesite.
- No responde la pregunta operativa: **«¿Qué hago primero?»**
- Mezcla contexto financiero con urgencias operativas sin jerarquía visual ni lógica de priorización.

### 1.2 Objetivo Dashboard V2

Transformar `/` (solo ADMIN) en un **Centro de Decisión** con:

1. **Una recomendación inteligente** — acción principal sugerida.
2. **Salud operativa** — semáforo por área (recepción, caja, taller, inventario).
3. **Prioridades agrupadas** — familias con ítems accionables.
4. **Resumen compacto** — KPIs de contexto secundario.
5. **Acciones frecuentes** — atajos estáticos.
6. **Finanzas e inventario lazy** — solo al expandir/solicitar.

### 1.3 Qué NO es Dashboard V2

| No es | Dueño / nota |
|-------|----------------|
| Nuevo endpoint `/dashboard/control` | Rechazado |
| Motor de decisiones genérico reutilizable | Rechazado (YAGNI) |
| Micro-módulo o capa arquitectónica nueva | Rechazado |
| Reemplazo de A0 / Mi Taller / Caja | P3, P4, A0 intactos |
| Cambio de landing por rol (P5.1) | CAJA → Caja, TECNICO → Mi Taller, etc. |
| Dashboard para roles distintos de ADMIN en `/` | Solo ADMIN consume V2 en `/` |

---

## 2. Reglas obligatorias (congeladas)

### 2.1 Backend = cerebro

| # | Regla |
|---|-------|
| 1 | Toda la inteligencia vive en backend |
| 2 | Frontend únicamente renderiza JSON |
| 3 | Frontend **no** calcula prioridades |
| 4 | Frontend **no** calcula severidades |
| 5 | Frontend **no** ordena por importancia |
| 6 | Frontend **no** interpreta reglas de negocio |
| 7 | Frontend **no** decide qué acción mostrar primero |
| 8 | Toda recomendación viene ya calculada desde backend |
| 9 | No crear endpoints innecesarios |
| 10 | No fragmentar el dominio Dashboard |

### 2.2 Mandato CSA — simplicidad

- **Menos capas siempre es mejor.**
- **Menos servicios siempre es mejor.**
- **Menos contratos siempre es mejor.**
- Cada clase o archivo nuevo debe justificar por qué no puede integrarse al existente.
- Si el beneficio no supera claramente el costo → mantener arquitectura actual.

### 2.3 Implementación backend (congelada)

| Decisión | Valor |
|----------|-------|
| Extender módulo actual | ✅ `app/routers/dashboard_agregado.py` |
| Separación opcional por legibilidad | ✅ `app/routers/dashboard_operativa.py` — **solo si el archivo crece demasiado** |
| Motivo de separación | Legibilidad, **no** patrón arquitectónico |
| Servicios nuevos (`*DashboardService`, `*Engine`) | ❌ No crear |
| Pesos y umbrales | ✅ `app/config/dashboard_prioridades.py` o constants en el mismo módulo |
| Reutilizar extractores A0 | ✅ Donde existan en `operaciones_service` — sin duplicar reglas |

---

## 3. API — endpoint único

### 3.1 Recurso

```
GET /api/dashboard
```

**Un solo endpoint.** No se crean rutas adicionales bajo `/dashboard`.

### 3.2 Query parameters

| Parámetro | Tipo | Default | Reglas |
|-----------|------|---------|--------|
| `secciones` | enum[] (CSV o repetible) | `operativa` | Valores permitidos: `operativa`, `finanzas`, `inventario` |
| `periodo` | enum | `mes` | Obligatorio cuando `finanzas` ∈ `secciones`. Valores: `mes`, `mes_pasado`, `ano`, `acumulado` |

### 3.3 Enum `secciones` (estricto)

| Valor | Comportamiento |
|-------|----------------|
| `operativa` | Bloque decisión: recomendación, salud, prioridades, resumen, acciones. **Default en mount.** |
| `finanzas` | Bloque financiero lazy (extrae lógica pesada actual de `dashboard_agregado`) |
| `inventario` | Bloque inventario detallado lazy |

**Valor desconocido** → HTTP **422** con mensaje claro.

**Ejemplos válidos:**

```
GET /api/dashboard
GET /api/dashboard?secciones=operativa
GET /api/dashboard?secciones=operativa,finanzas&periodo=mes
GET /api/dashboard?secciones=finanzas&periodo=mes
GET /api/dashboard?secciones=inventario
```

### 3.4 Guardas de performance (obligatorias)

| Condición | Prohibido ejecutar |
|-----------|-------------------|
| `finanzas` ∉ `secciones` | Loop utilidad N+1 por venta |
| `finanzas` ∉ `secciones` | CPP pesado (órdenes compra + cuentas manuales iterativas) |
| `finanzas` ∉ `secciones` | Agregados financieros de periodo (`total_facturado`, `utilidad_neta`, gastos periodo) |
| `inventario` ∉ `secciones` | `InventarioService.calcular_valor_inventario` y conteos detallados de stock |
| `inventario` ∉ `secciones` | Órdenes de compra alertas detalladas |

La sección `operativa` debe poder responder en **< 500 ms** en condiciones normales de producción (objetivo técnico; validar en smoke post-deploy).

### 3.5 `/api/operaciones/resumen` (sin cambio de rol)

- Permanece como fuente del acordeón **Operación** colapsable (UX-1A).
- Se consume con `incluir_items=false` en dashboard (modo ligero A0).
- **No compite** con la recomendación inteligente del hero.
- **No** se fusiona con `/api/dashboard`.

---

## 4. Contrato JSON (congelado)

### 4.1 Forma general de respuesta

```json
{
  "meta": {
    "zona": "America/Matamoros",
    "generado_en": "<ISO8601 UTC con Z>",
    "secciones_calculadas": ["operativa"]
  },

  "operativa": { ... } | null,
  "finanzas": { ... } | null,
  "inventario": { ... } | null
}
```

- Keys `operativa`, `finanzas`, `inventario` **siempre presentes**.
- Valor `null` cuando la sección no fue solicitada.
- Sin versionado adicional de contrato en V2 (deploy acoplado frontend + backend).

### 4.2 Bloque `operativa`

Calculado cuando `operativa` ∈ `secciones` (default).

#### 4.2.1 `recomendacion_inteligente` (siempre presente en operativa)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `titulo` | string | Frase accionable para el ADMIN |
| `accion_label` | string | Texto del botón CTA |
| `to` | string | Ruta frontend (`/operaciones/caja`, etc.) |
| `severidad` | enum | `critica`, `alta`, `media`, `baja`, `estable` |
| `grupo` | string? | Familia origen (`cobros`, `entregas`, …) |
| `decision_score` | number | Score interno para ordenamiento — **API sí, UI no** (ocultar en render) |
| `explicacion` | string[] | 1–3 razones legibles («lleva 5 h», «$X pendiente», …) |
| `referencia` | object? | `{ tipo, id }` opcional para trazabilidad |

**Regla de oro:** exactamente **una** recomendación principal. Si no hay urgencias → `severidad: estable` con mensaje de operación normal.

#### 4.2.2 `salud_operativa`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `global` | enum | `verde`, `amarillo`, `rojo` |
| `mensaje` | string | Resumen en una línea |
| `areas` | object | `recepcion`, `caja`, `taller`, `inventario` — cada una: `{ estado, mensaje }` |

#### 4.2.3 `prioridades_agrupadas`

Array ordenado por importancia (orden calculado en backend).

Cada grupo:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `grupo` | string | `cobros`, `entregas`, `citas`, `autorizaciones`, `inventario`, `caja` |
| `label` | string | Etiqueta humana |
| `severidad_grupo` | enum | `critica`, `alta`, `media`, `baja` |
| `total` | number | Total ítems en la familia |
| `items` | array | Máximo **3** ítems visibles |
| `ver_todas` | object? | `{ to, label }` si `total > 3` |

Cada ítem en `items`:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | Identificador compuesto o único |
| `titulo` | string | Línea principal |
| `subtitulo` | string? | Contexto (cliente, monto, tiempo) |
| `severidad` | enum | Severidad del ítem |
| `decision_score` | number | Para orden interno — ocultar en UI |
| `to` | string | Deep link o ruta de acción |
| `referencia` | object? | `{ tipo, id }` |

**Regla:** grupos con `total: 0` **no se incluyen** en el array.

**Orden fijo de familias (desempate):** cobros → entregas → autorizaciones → citas → inventario → caja.

#### 4.2.4 `resumen`

KPIs compactos de contexto (secundarios visualmente):

| Campo | Descripción |
|-------|-------------|
| `caja` | Estado turno / alerta resumida |
| `cobrado_hoy` | Total cobrado día taller |
| `ventas_hoy` | Ventas del día |
| `ot_activas` | OT en curso |
| `citas_proximas_24h` | Conteo citas próximas 24 h |
| `por_cobrar` | Monto pendiente resumido |

#### 4.2.5 `acciones_frecuentes`

Lista estática servida desde config backend (no calculada por motor):

```json
[
  { "id": "recepcion", "label": "Recepción rápida", "to": "/operaciones/recepcion", "orden": 1 },
  { "id": "caja", "label": "Caja operativa", "to": "/operaciones/caja", "orden": 2 }
]
```

### 4.3 Bloque `finanzas` (lazy)

Presente solo si `finanzas` ∈ `secciones`. Extrae la lógica financiera actual de `dashboard_agregado.py`:

| Campo | Origen actual |
|-------|---------------|
| `periodo` | Query param |
| `total_ventas_periodo` | Agregado ventas |
| `total_facturado` | Agregado pagos |
| `total_gastos` | `query_gastos` |
| `utilidad_neta` | Cálculo N+1 actual (solo aquí) |
| `cuentas_por_pagar` | CPP OC + manuales |
| `devoluciones_mes` | `query_devoluciones` |

### 4.4 Bloque `inventario` (lazy)

Presente solo si `inventario` ∈ `secciones`:

| Campo | Origen actual |
|-------|---------------|
| `valor_inventario` | `InventarioService.calcular_valor_inventario` |
| `productos_activos` | Conteo |
| `stock_bajo` | Conteo |
| `sin_stock` | Conteo |
| `total_alertas` | Alertas activas |
| `ordenes_compra_alertas` | OC sin recibir / vencidas |

---

## 5. Lógica de decisión (backend)

### 5.1 Ubicación

Toda la lógica vive en el módulo dashboard extendido:

```
app/routers/dashboard_agregado.py      ← router + orquestación secciones
app/routers/dashboard_operativa.py     ← opcional, solo legibilidad
app/config/dashboard_prioridades.py    ← pesos, umbrales, acciones_frecuentes
```

**No** se crean:

- `DashboardService`
- `PrioridadesDashboardService`
- `RecomendacionInteligenteService`
- `SaludOperativaService`
- `DecisionEngine` / `MotorDecisionOperativa` como paquete independiente

### 5.2 Flujo interno (una pasada)

```
1. Extraer candidatos por familia (queries acotadas)
2. Calcular decision_score por candidato
3. Ordenar y agrupar → prioridades_agrupadas
4. Seleccionar top-1 → recomendacion_inteligente
5. Derivar salud_operativa desde métricas por área
6. Armar resumen compacto (queries ligeras SUM/COUNT)
7. Adjuntar acciones_frecuentes desde config
```

### 5.3 Fórmula `decision_score` (congelada conceptualmente)

```
decision_score = peso_base(tipo) × factor_antiguedad × factor_proximidad × factor_impacto
```

| Factor | Regla |
|--------|-------|
| `peso_base` | Por familia — definido en config |
| `factor_antiguedad` | Más antigüedad → mayor score (5 h > 10 min) |
| `factor_proximidad` | Citas próximas, entregas hoy |
| `factor_impacto` | Monto pendiente, OT bloqueada, stock crítico |

**Pesos y umbrales:** únicamente en `app/config/dashboard_prioridades.py`. El router/funciones importan constants; no hardcodear en lógica dispersa.

### 5.4 Fuentes de candidatos (reutilizar, no duplicar)

| Familia | Fuente preferida |
|---------|------------------|
| Cobros | Ventas/OT por cobrar, alertas caja |
| Entregas | OT listas para entrega |
| Autorizaciones | OT esperando autorización cliente |
| Citas | Citas confirmadas próximas (`fecha_hora` local naive — TIMEZONE_POLICY) |
| Inventario | Alertas stock, sin stock |
| Caja | Turno abierto largo, alertas `CajaAlerta` |

Donde `operaciones_service` ya expone datos equivalentes para A0, **reutilizar funciones internas** — no reimplementar reglas de estado OT.

### 5.5 Timezone

Todas las comparaciones de antigüedad y rangos «hoy» usan utilidades de `app/utils/fechas.py`:

- `hoy_taller()`, `ahora_local()`, `condiciones_rango_taller()`
- Citas: `fecha_hora` local naive
- OT: `fecha_ingreso` con política TZ-1 documentada en [TIMEZONE_POLICY.md](./TIMEZONE_POLICY.md)

---

## 6. Frontend (render puro)

### 6.1 Consumidor

Solo **ADMIN** en ruta `/` (`Dashboard.jsx`). P5.1 intacto: otros roles redirigen vía `getLandingPorRol`.

### 6.2 Mount inicial

```
GET /api/dashboard
```

Equivalente a `?secciones=operativa`. Renderizar en este orden visual:

1. **Recomendación inteligente** (hero — primer elemento pintado)
2. **Salud operativa** (4 áreas)
3. **Prioridades agrupadas** (acordeones o tarjetas por familia)
4. **Resumen** (KPIs compactos — visualmente subordinados)
5. **Acciones frecuentes**

### 6.3 Secciones lazy (colapsables)

| Sección UI | Request al expandir |
|------------|---------------------|
| Operación (A0) | `GET /api/operaciones/resumen?incluir_items=false` — sin cambio UX-1A |
| Finanzas | `GET /api/dashboard?secciones=finanzas&periodo={mes}` |
| Inventario | `GET /api/dashboard?secciones=inventario` |

### 6.4 Prohibiciones frontend

| Prohibido | Motivo |
|-----------|--------|
| Ordenar `prioridades_agrupadas` o `items` | Backend ya ordena |
| Recalcular `decision_score` | Backend |
| Elegir recomendación entre candidatos | Backend |
| Mapear severidad desde conteos locales | Backend |
| Mostrar `decision_score` al usuario | Ruido cognitivo — solo debug futuro opcional |

### 6.5 Objetivo UX — 5 segundos

| Segundo | Lo que ve el ADMIN |
|---------|-------------------|
| 0–1 | Skeleton hero recomendación |
| 1–3 | Recomendación con CTA visible |
| 3–5 | Salud + primer grupo de prioridades |

Si mount operativa > 3 s en prod → investigar queries, no compensar en frontend.

---

## 7. Compatibilidad

| Sistema | Impacto V2 |
|---------|------------|
| **P5.1** landing por rol | Sin cambio |
| **UX-1A** acordeón operativo | Sección colapsable lazy — A0 intacto |
| **UX-1B** Mi Taller | Sin cambio (otra ruta) |
| **A0 v2** | Lectura reutilizada; contrato A0 no se modifica |
| **Timezone Matamoros** | Extractores operativa usan `fechas.py` |
| **Producción Railway** | Deploy acoplado backend + frontend ADMIN |
| **Roles CAJA / TECNICO / EMPLEADO** | No consumen Dashboard V2 |

### 7.1 Migración desde respuesta plana actual

El shape plano actual de `GET /api/dashboard` (campos `clientes`, `ordenes`, `inventario`, etc. en raíz) **se reemplaza** por el shape anidado V2.

- Único consumidor: `Dashboard.jsx` (ADMIN).
- No se mantiene shim `legacy` en V2 — deploy simultáneo.

---

## 8. Testing (mínimo obligatorio)

### 8.1 Backend — unitarios

| Test | Assert |
|------|--------|
| Scoring antigüedad | Item 5 h score > item 10 min (misma familia) |
| Una recomendación | Siempre exactamente 1 `recomendacion_inteligente` |
| Agrupación | Máx 3 items; `ver_todas` si total > 3 |
| Grupos vacíos | No aparecen en array |
| Orden familias | cobros antes que caja en empate |
| Salud derivada | Área roja si hay candidato crítico en esa área |
| TZ citas | Cita naive 08:00 no desplazada en proximidad |
| Secciones 422 | Valor desconocido rechazado |
| Guarda finanzas | Sin `finanzas` → no ejecuta loop utilidad (mock/spy) |
| Guarda inventario | Sin `inventario` → no llama `calcular_valor_inventario` |

### 8.2 Smoke ADMIN (post-deploy)

- Login ADMIN → recomendación visible < 5 s
- CTA navega a ruta válida
- Expandir Finanzas carga bloque lazy
- CAJA sigue aterrizando en `/operaciones/caja`

---

## 9. Fuera de alcance V2

| Item | Motivo |
|------|--------|
| Caché in-memory | Optimización prematura |
| `meta.version_contrato` dashboard | Deploy acoplado suficiente |
| Panel «¿Por qué?» expandible | V2.2 |
| Deep links con query params | V2.2 |
| Notificaciones push desde mismo motor | Backlog |
| Dashboard V2 para CAJA en `/` | P5.1 — CAJA va a operación |
| Modificar contrato A0 | P5.3 dominio separado |

---

## 10. Checklist de decisiones congeladas

- [x] Un solo endpoint: `GET /api/dashboard`
- [x] Sin `/api/dashboard/control`
- [x] `secciones` enum estricto: `operativa`, `finanzas`, `inventario`
- [x] Default `operativa`; desconocido → 422
- [x] Lazy real: sin finanzas → sin utilidad N+1 ni CPP pesado
- [x] Lazy real: sin inventario → sin inventario detallado
- [x] Backend cerebro; frontend render puro
- [x] Sin servicios nuevos innecesarios
- [x] Sin `DecisionEngine` genérico
- [x] Sin caché en V2
- [x] Sin versionado de contrato adicional
- [x] Extender `dashboard_agregado.py`; `dashboard_operativa.py` solo por legibilidad
- [x] Pesos en `app/config/dashboard_prioridades.py`
- [x] Contrato: `recomendacion_inteligente`, `salud_operativa`, `prioridades_agrupadas`, `resumen`, `acciones_frecuentes`
- [x] Finanzas e inventario lazy en bloques separados
- [x] Una sola recomendación principal (regla de oro)
- [x] `decision_score` en API, oculto en UI
- [x] A0 en acordeón Operación — no compite con hero
- [x] P5.1, UX-1A, timezone intactos
- [x] Objetivo UX: < 5 segundos para saber qué hacer

---

## 11. Plan de implementación (orden obligatorio)

| # | Fase | Entregable | Notas |
|---|------|------------|-------|
| 1 | Documentación | Este plan (`PLAN_DASHBOARD_V2.md`) | ✅ Congelado |
| 2 | Config | `app/config/dashboard_prioridades.py` | Pesos, umbrales, acciones_frecuentes |
| 3 | Lógica operativa | Funciones en dashboard (agregado u operativa) | Candidatos → score → recomendación → salud → grupos |
| 4 | Tests unitarios | `tests/test_dashboard_v2_*.py` | Antes de tocar frontend |
| 5 | Endpoint | Extender `GET /api/dashboard` con `secciones` + guardas | Shape V2 anidado |
| 6 | Smoke ADMIN | Script o verificación manual staging/prod | < 5 s a recomendación |
| 7 | Frontend render | `Dashboard.jsx` + componentes en `components/dashboard/` | Hero → salud → prioridades → resumen |
| 8 | Lazy sections | Acordeones Finanzas / Inventario / Operación | Requests bajo demanda |
| 9 | Validación prod | 48 h monitoreo ADMIN | Sin regresión P5.1 ni TZ |

**Regla:** no invertir pasos 3–5 con 7. El frontend no compensa lógica faltante en cliente.

---

## 12. Criterios de cierre V2

| Criterio | Métrica |
|----------|---------|
| Recomendación visible | ADMIN ve CTA en < 5 s post-login |
| Render puro | Cero lógica de scoring/orden en `Dashboard.jsx` |
| Lazy efectivo | Mount default no ejecuta utilidad N+1 |
| Tests | Suite unitaria dashboard V2 verde |
| Regresión P5.1 | CAJA/TECNICO/EMPLEADO landing correcto |
| Regresión TZ | Citas y OT en smoke timezone |
| Build | `npm run build` OK |
| Backend | `python -c "from app.main import app"` OK |

---

*Documento congelado bajo mandato CSA. Cualquier desviación (nuevo endpoint, servicio, motor genérico, caché) requiere PRE-CHECK arquitectónico explícito y autorización del usuario.*
