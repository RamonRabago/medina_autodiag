# CHECKLIST P4.1 — Caja Operativa MVP

**Versión del documento:** 1.0  
**Fecha:** Junio 2026  
**Commit P4.0 de referencia:** `86afda7` — cierre evaluador financiero · `2c9b8df` — smoke A0 v2  
**Contrato A0:** `meta.version_contrato = "a0-v2"`  
**Estado:** 🟡 **Fase 0 + Fase 1 autorizadas** — Fases 2–5 bloqueadas  
**Relacionado:** [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md) · [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md) · [CHECKLIST_P4_0_STAGING.md](./CHECKLIST_P4_0_STAGING.md) · [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

## 1. Objetivo

Implementar la **superficie operativa de mostrador** `/operaciones/caja` (Modo Mostrador) consumiendo **exclusivamente** `GET /api/operaciones/resumen` (A0 v2), sin duplicar reglas de negocio en frontend.

Este checklist es la **fuente operativa** para declarar el veredicto por fase:

> **P4.1 VALIDADO EN STAGING** (futuro — requiere Fases 2–5 completas)

---

## 2. Pre-requisitos (gate P4.1)

| Requisito | Estado | Verificación |
|-----------|--------|--------------|
| P4.0 cerrado | ✅ | [CHECKLIST_P4_0_STAGING.md](./CHECKLIST_P4_0_STAGING.md) — Railway validado |
| Contrato A0 v2 | ✅ | `meta.version_contrato=a0-v2`; globals financieros `item_only` |
| Autorización explícita UI | ✅ | GO arquitectónico P4.1 — Fase 0 + Fase 1 |
| OT-FECHAS-V1 en prod | 🔲 | Dependencia **prod** P4.1 — no bloquea staging/dev |
| Backend sin cambios Fase 0–1 | ✅ | Solo frontend + docs |

---

## 3. Alcance por fase

| Fase | Alcance | Mutaciones | Estado |
|------|---------|------------|--------|
| **0 — PRE-CHECK documental** | Checklist, actualizar ARQUITECTURA y PLAN | No | 🟡 En curso |
| **1 — Esqueleto UI + routing** | Ruta, menú, roles, bandejas solo lectura, banner turno | No | 🟡 Autorizada |
| **2 — Acciones caja** | `AccionesCajaRenderer`; botones desde `acciones[]` | Sí (delegadas) | ❌ Bloqueada |
| **3 — Flujo crear venta OT** | Confirmación `requiere_factura` → POST venta | Sí | ❌ Bloqueada |
| **4 — Flujo pago + entrega** | Registrar pago, entregar vehículo | Sí | ❌ Bloqueada |
| **5 — Validación staging** | Smoke §6 PLAN, regresión Mi Taller / Recepción / Citas | — | ❌ Bloqueada |

**Prohibido en Fase 0–1:** tocar backend, Alembic, `pagos.py`, `VentasService`, comisiones.

---

## 4. Especificación UI (normativa)

| Campo | Valor |
|-------|-------|
| **Ruta** | `/operaciones/caja` |
| **Roles** | ADMIN, CAJA — **misma UI** (Modo Mostrador) |
| **Sin acceso** | TECNICO, EMPLEADO y demás roles |
| **API lectura** | `GET /api/operaciones/resumen?incluir_items=true&limit_items=N` |
| **API mutación** | Ninguna en Fase 1 — delegadas en Fases 2–4 |

### Bandejas renderizadas (solo estas tres)

| # | Sección UI | Bandeja A0 | Clave payload |
|---|------------|------------|---------------|
| 1 | Por cobrar (OT) | OT completadas sin cobro total | `bandejas.ot_pendientes_cobro` |
| 2 | Listas para entrega | OT cobradas pendientes entrega | `bandejas.ot_listas_entrega` |
| 3 | Ventas con saldo (mostrador) | Ventas sin OT en flujo cobro | `bandejas.ventas_saldo_pendiente` |

**No renderizar** bandejas técnicas (`ot_pendientes`, `ot_en_proceso`, etc.) — permanecen en Mi Taller.

### Componentes

| Componente | Fase | Función |
|------------|------|---------|
| `CajaOperativa.jsx` | 1 | Pantalla principal |
| `TurnoCajaBanner.jsx` | 1 | `data.caja.turno_abierto`; enlace `/caja` si cerrado |
| `BandejaOtSection` | 1 | Reutilizado P3.1 — `soloLectura={true}` en Fase 1 |
| `BandejaVentaSection` | 1 | Skeleton lectura ventas A0 |
| `AccionesCajaRenderer` | 2+ | Botones gobernados por `acciones[]` |

---

## 5. Fase 0 — PRE-CHECK documental

### 5.1 Entregables

- [x] Crear `docs/CHECKLIST_P4_1_CAJA_OPERATIVA.md`
- [x] Actualizar `docs/ARQUITECTURA_OPERATIVA_V2.md` — P4.0 cerrado; P4.1 desbloqueado (Fase 0+1)
- [x] Actualizar `docs/PLAN_P4_CAJA_OPERATIVA.md` — quitar bloqueo UI; referenciar commits P4.0

### 5.2 Checklist PRE-CHECK arquitectónico

| Ítem | Verificación |
|------|--------------|
| Fuente única A0 | ✅ Solo `GET /operaciones/resumen` |
| Backend autoridad | ✅ Frontend no decide permisos |
| Reutilización | ✅ `BandejaOtSection`, `OtOperativaCard`, `useOperacionesResumen` |
| Sin deduplicación frontend | ✅ Regla dominio en A0 v2 |
| Regresión | ✅ Mi Taller, Recepción, Citas V2 sin cambios en Fase 0–1 |
| TECNICO sin ruta | ✅ Guard + menú filtrado por rol |

---

## 6. Fase 1 — Esqueleto UI + routing

### 6.1 Entregables código

- [x] `frontend/src/utils/rolesOperaciones.js` — `ROLES_CAJA_OPERATIVA`, `puedeCajaOperativa`
- [x] `frontend/src/App.jsx` — lazy route `/operaciones/caja`
- [x] `frontend/src/components/Layout.jsx` — entrada menú Operaciones
- [x] `frontend/src/pages/operaciones/CajaOperativa.jsx`
- [x] `frontend/src/components/operaciones/TurnoCajaBanner.jsx`
- [x] `frontend/src/components/operaciones/BandejaVentaSection.jsx`

### 6.2 Validación Fase 1

| Check | Comando / criterio |
|-------|-------------------|
| Build frontend | `cd frontend && npm run build` → exit 0 ✅ (7.13s) |
| Ruta protegida | TECNICO → redirect `/` |
| Menú | ADMIN y CAJA ven "Caja operativa"; TECNICO no |
| Bandejas | Tres secciones; `soloLectura` en OT; sin botones mutación |
| Banner turno | Muestra estado `caja.turno_abierto` |
| Sin mutaciones | Ningún POST/PUT desde pantalla |

---

## 7. Fase 2–5 (bloqueadas)

No iniciar sin autorización explícita. Ver [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md) § P4.1–P4.2 y smoke §6.

---

## 8. Criterios GO producción P4.1 (futuro)

| Criterio | Requerido |
|----------|-----------|
| OT-FECHAS-V1 en prod | Sí |
| P4.0 + smoke A0 v2 | Sí |
| Fases 2–5 completas | Sí |
| Cero escenarios `acciones[].permitida=true` → POST 400 | Sí |
| Regresión Mi Taller / Recepción / Citas | Sí |

---

## 9. Control de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-06-08 | Fase 0 documental; gate Fase 1 autorizada |
