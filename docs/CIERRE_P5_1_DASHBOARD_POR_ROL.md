# CIERRE P5.1 — DASHBOARD POR ROL

**Versión:** 1.0  
**Fecha:** 16 de junio de 2026  
**Estado:** ✅ **CERRADO EN PRODUCCIÓN** — liberado sin rollback  
**Entorno producción:** `https://medinaautodiag.up.railway.app`  
**Contrato vigente:** A0 v2 (`meta.version_contrato = "a0-v2"`)  
**SHA `main` al cierre:** `1bb7f9d815795209db29222126776a4e68059701` — `feat(p5.1): landing por rol y dashboard operativo admin`

**Referencias:**

- [PLAN_P5_DASHBOARD_POR_ROL.md](./PLAN_P5_DASHBOARD_POR_ROL.md)
- [CIERRE_P42_FLUJO_GUIADO_CAJA.md](./CIERRE_P42_FLUJO_GUIADO_CAJA.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)

---

## Resumen ejecutivo

P5.1 cierra el hito **Dashboard por Rol** como MVP frontend-only: cada rol operativo aterriza en su superficie de trabajo diaria tras el login, y el rol **ADMIN** conserva `/` como dashboard gerencial enriquecido con una sección operativa ligera alimentada por A0 v2.

| Capacidad | Resultado |
|-----------|-----------|
| **Landing por rol** | Post-login redirige según rol (ADMIN permanece en `/`; CAJA, TECNICO y EMPLEADO van a operaciones) |
| **Guard de navegación** | Si CAJA, TECNICO o EMPLEADO visitan `/` manualmente, se redirigen a su landing sin ver KPIs financieros |
| **Dashboard operativo ADMIN** | Sección «Operaciones» con alertas, turno caja, CTAs y contadores A0 — sin duplicar bandejas O1/O2/V1 |
| **Integración A0 ligera** | Query independiente con `incluir_items=false` y `limit_items=1`; KPIs financieros siguen en `GET /api/dashboard` |

El release quedó desplegado sobre `1bb7f9d`, CI Run **#318** verde, Railway auto-deploy success, `build_rev` validado y smoke UI en producción **PASS** (con observaciones documentadas).

**Principios preservados:**

- Sin cambios en backend, A0, endpoints ni Alembic.
- Contadores y enlaces en dashboard ADMIN; detalle operativo permanece en `/operaciones/*`.
- Caja Operativa, Mi Taller y Recepción Rápida sin regresión funcional detectada.

---

## Alcance implementado

### Landing por rol

Centralizado en `getLandingPorRol()` (`frontend/src/utils/rolesOperaciones.js`). Invocado desde `Login.jsx` (post-login) y `Dashboard.jsx` (guard en `/`).

| Rol | Landing post-login | Redirect si visita `/` |
|-----|-------------------|------------------------|
| ADMIN | `/` | — (permanece) |
| CAJA | `/operaciones/caja` | → `/operaciones/caja` |
| TECNICO | `/operaciones/mi-taller` | → `/operaciones/mi-taller` |
| EMPLEADO | `/operaciones/recepcion` | → `/operaciones/recepcion` |
| Rol desconocido | `/` | — |

### Guard de Dashboard

En `Dashboard.jsx`, tras resolver el rol del usuario autenticado, si `getLandingPorRol(rol) !== '/'` se renderiza `<Navigate to={landing} replace />` antes de mostrar contenido gerencial.

Efecto:

- **CAJA / TECNICO / EMPLEADO** no acceden al dashboard financiero desde `/` ni desde el enlace lateral «Dashboard».
- **ADMIN** permanece en `/` y ve el dashboard completo (financiero + operativo).
- No hay loop de redirects: la landing de cada rol operativo es distinta de `/`.

### Dashboard Operativo ADMIN

Componente `DashboardOperativoSection.jsx`, visible solo cuando `rol === 'ADMIN'`, compuesto por:

| Bloque | Fuente | Descripción |
|--------|--------|-------------|
| **Alertas operativas** | `alertas_operativas[]` (A0) | Banners por severidad (`AlertasOperativasBanner`) |
| **Banner turno caja** | `caja` (A0) | Reutiliza patrón `TurnoCajaBanner` |
| **CTAs operativos** | Rutas existentes | Enlaces a Recepción, Caja operativa, Mi taller, Citas |
| **KPIs A0** | `metricas` (A0) | 10 contadores con destino (Anexo A del plan): citas, OT, O1/O2/V1, refacciones |
| **KPIs financieros** | `GET /api/dashboard` | Grid existente sin cambios (ventas, utilidad, inventario, etc.) |

**Prohibición cumplida:** no se copiaron `BandejaOtSection`, `AccionesCajaRenderer` ni modales P4 al dashboard.

### Optimización A0

Hook `useOperacionesResumen` extendido con opciones `incluirItems` y `enabled`. En dashboard ADMIN:

```http
GET /api/operaciones/resumen?limit_items=1&incluir_items=false
```

| Beneficio | Detalle |
|-----------|---------|
| Métricas sin bandejas completas | Solo contadores en `metricas`; bandejas con `items` vacíos |
| Menor payload | ~1 KB vs respuesta A0 completa con ítems |
| Dashboard más ligero | Query A0 independiente de `/api/dashboard`; `enabled: esAdmin` evita fetch innecesario en redirect |

Mi Taller y Caja Operativa siguen usando `useOperacionesResumen(30, { incluirItems: true })` sin cambio de comportamiento.

---

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `frontend/src/utils/rolesOperaciones.js` | `getLandingPorRol()` + mapa `LANDING_POR_ROL` |
| `frontend/src/pages/Login.jsx` | Redirect post-login según rol |
| `frontend/src/pages/Dashboard.jsx` | Guard `/` + sección operativa ADMIN |
| `frontend/src/hooks/useOperacionesResumen.js` | Params `incluirItems`, `enabled`; query key extendida |
| `frontend/src/components/dashboard/KPIWidget.jsx` | **Nuevo** — tarjeta contador + link opcional |
| `frontend/src/components/dashboard/AlertasOperativasBanner.jsx` | **Nuevo** — lista `alertas_operativas[]` |
| `frontend/src/components/dashboard/DashboardOperativoSection.jsx` | **Nuevo** — sección operativa ADMIN |

**Sin modificar:** backend, A0, Caja Operativa, Mi Taller, Recepción Rápida (salvo consumo de hook con defaults compatibles).

---

## Validaciones técnicas

### Build

| Comando | Resultado |
|---------|-----------|
| `cd frontend && npm run build` | **PASS** |

### Pytest

| Comando | Resultado |
|---------|-----------|
| `pytest tests/test_operaciones_resumen.py -v` | **19 passed** |
| `pytest tests/ -q` | **185 passed** |
| `ruff check app tests` | **PASS** |
| `black --check app tests` | **PASS** |
| `python -c "from app.main import app; print('OK')"` | **PASS** |

### CI

| Campo | Valor |
|-------|-------|
| Run | **#318** |
| Evento | push `main` |
| SHA | `1bb7f9d815795209db29222126776a4e68059701` |
| Resultado | **SUCCESS** |

### Deploy

| Campo | Valor |
|-------|-------|
| Plataforma | Railway (auto-deploy on push) |
| Deploy manual | No ejecutado |
| Resultado | **PASS** |
| `GET /health` | 200 — `{"status":"healthy","database":"connected"}` |

### build_rev

| Campo | Valor |
|-------|-------|
| `GET /api/config` → `build_rev` | `1bb7f9d81579` |
| SHA esperado | `1bb7f9d815795209db29222126776a4e68059701` |

---

## Smoke UI Producción

Ejecutado en `https://medinaautodiag.up.railway.app` tras deploy de `1bb7f9d`.

### Landing por rol

| Rol | Resultado | Notas |
|-----|-----------|-------|
| ADMIN | **PASS** | Permanece en `/` |
| CAJA | **PASS** | Aterriza en `/operaciones/caja` |
| TECNICO | **PASS** | Aterriza en `/operaciones/mi-taller` |
| EMPLEADO | **NO VALIDADO** | Sin usuario con rol EMPLEADO en BD prod (5 usuarios: 3 ADMIN, 1 CAJA, 1 TECNICO) |

### Guard de `/`

| Rol | Resultado |
|-----|-----------|
| CAJA → `/` | **PASS** → redirect `/operaciones/caja` |
| TECNICO → `/` | **PASS** → redirect `/operaciones/mi-taller` |
| ADMIN → `/` | **PASS** → permanece |
| EMPLEADO → `/` | **NO VALIDADO** |

### Dashboard ADMIN

| Elemento | Resultado |
|----------|-----------|
| Sección «Operaciones» | **PASS** |
| Alertas operativas (2 banners observados) | **PASS** |
| Banner turno caja | **PASS** |
| CTAs operativos (4 enlaces) | **PASS** |
| KPIs operativos A0 (10 contadores) | **PASS** |
| KPIs financieros legacy | **PASS** (sin regresión) |

### Network Validation

| Check | Resultado |
|-------|-----------|
| Request observado | `GET /api/operaciones/resumen?limit_items=1&incluir_items=false` |
| `meta.incluir_items` | `false` — **PASS** |
| `meta.version_contrato` | `a0-v2` — **PASS** |
| `metricas` | 10 claves presentes — **PASS** |
| `alertas_operativas` | presente (2 alertas) — **PASS** |
| `caja` | presente — **PASS** |
| `bandejas.*.items` | longitud 0 en todas — **PASS** |

### Regresiones

| Pantalla | Resultado | Evidencia |
|----------|-----------|-----------|
| Caja Operativa | **PASS** | Bandejas O1 (3), O2 (2), V1 (2); CTA «Continuar proceso» |
| Mi Taller | **PASS** | Bandejas Pendientes / En proceso / Completadas con OT |
| Recepción Rápida | **PASS** | Formulario de ingreso visible |

---

## Hallazgos

### P5.1-OBS-001

**Posible diferencia de estado de turno entre Dashboard ADMIN y Caja Operativa.**

| Campo | Detalle |
|-------|---------|
| Síntoma | Dashboard ADMIN (A0) mostró «Turno de caja abierto» (Turno #1); Caja Operativa con usuario CAJA mostró «No hay turno de caja abierto» |
| Clasificación | Observación operativa |
| Impacto P5.1 | No bloqueante |
| Acción | No corregido en P5.1; revisar contexto de turno por usuario/sesión en operación |

### P5.1-OBS-002

**Rol EMPLEADO no validado en producción.**

| Campo | Detalle |
|-------|---------|
| Causa | Ausencia de usuarios con rol EMPLEADO en BD prod |
| Alcance no probado | Landing post-login y guard `/` para EMPLEADO |
| Clasificación | Pendiente de smoke futuro |
| Impacto P5.1 | No bloqueante (código alineado con plan §5.5) |
| Mitigación acordada | Rollback parcial documentado en plan: `EMPLEADO: '/'` si falla en prod; crear usuario EMPLEADO y re-smoke |

---

## Resultado Final

| Campo | Valor |
|-------|-------|
| **Estado** | **PASS** |
| **Veredicto** | P5.1 queda **cerrado y liberado** |
| **Rollback** | No aplicado |

---

## Baseline

| Campo | Valor |
|-------|-------|
| **SHA** | `1bb7f9d815795209db29222126776a4e68059701` |
| **Release estable** | P5.1 Dashboard por Rol |
| **Contrato** | A0 v2 |
| **Commit feature** | `feat(p5.1): landing por rol y dashboard operativo admin` |
| **Commit plan (previo)** | `ab5fa88` — `docs: add P5.1 dashboard por rol plan` |

---

## Próximos pasos

**No incluidos en este release.** P5.1 se considera cerrado.

| Ítem | Fase | Notas |
|------|------|-------|
| Smoke EMPLEADO en prod | Operativo | Tras crear usuario EMPLEADO |
| Dashboard resumen CAJA en `/` | P5.2 | Backlog; no autorizado |
| Extensión A0 / métricas adicionales | P5.3 | Backlog |
| Playwright login + dashboard ADMIN | P5.4 | Backlog |
| Sync docs maestros / `CIERRE_P5_DASHBOARD.md` | P5.5 | Backlog |

---

*Documento de cierre P5.1 — generado tras smoke UI producción PASS. Sin cambios de código en este hito documental.*
