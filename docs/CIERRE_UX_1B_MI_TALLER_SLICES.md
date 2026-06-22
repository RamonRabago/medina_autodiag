# Cierre UX-1B — Mi Taller lazy slices (A0 v2.1)

**Versión:** 1.0  
**Fecha:** 22 de junio de 2026  
**Estado:** ✅ **CERRADO EN PRODUCCIÓN** — validado técnicamente y operativamente  
**Entorno:** `https://medinaautodiag.up.railway.app`

**Referencias:**

- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)
- [DEPLOY_RAILWAY.md](./DEPLOY_RAILWAY.md) — §5.1 flag `VITE_A0_SLICES_MI_TALLER`
- [CIERRE_P3_1_MI_TALLER.md](./CIERRE_P3_1_MI_TALLER.md)
- [postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md](./postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md)

---

## Resumen ejecutivo

UX-1B introduce **carga diferida por bandejas (slices)** en Mi Taller sobre la Capa Operativa Central A0 v2.1, reduciendo requests pesados (`incluir_items=true`) a un modelo **capa0 + hidratación selectiva** (`incluir_items=false` + `bandejas=ot_*`).

El hito quedó **desplegado, activado con flag ON y validado** en producción. Dashboard, Caja y Recepción permanecen en modo legacy (sin `bandejas=`).

| Campo | Valor |
|-------|-------|
| **build_rev funcional prod** | `43c8078dd897` (UX-1B.2) |
| **Flag Railway** | `VITE_A0_SLICES_MI_TALLER=true` |
| **Smoke UX-1B.3** | **PASS** (S1–S7) |
| **Rollback** | Variable `false` o eliminar + redeploy (~5–10 min) |
| **Alembic UX-1B** | Sin migración — solo frontend/backend/deploy |

---

## Alcance UX-1B

| Sub-hito | Commit | Descripción | Prod |
|----------|--------|-------------|------|
| **UX-1A** | `6f3de1b` | Accordion Dashboard / Mi Taller (DisclosurePanel) | ✅ Base previa |
| **UX-1B.0** | `ab05b72` | Backend: params slice `grupo`, `bandejas`, A0 v2.1 | ✅ |
| **UX-1B.1** | `94990df` | Frontend: lazy slices Mi Taller (`useOperacionesSlices`) | ✅ |
| **UX-1B.2** | `43c8078` | Pipeline Docker: `ARG/ENV VITE_A0_SLICES_MI_TALLER` (default OFF) | ✅ |
| **UX-1B.3** | — (activación) | Flag ON + smoke post-deploy | ✅ PASS |

**Archivos clave (referencia):**

- `app/services/operaciones_service.py` — slice A0 v2.1, bandejas `ot_*`
- `app/routers/operaciones.py` — query params `grupo`, `bandejas`, `incluir_items`
- `frontend/src/hooks/useOperacionesSlices.js` — capa0, slices, invalidación
- `frontend/src/pages/operaciones/MiTaller.jsx` — rama flag ON/OFF
- `frontend/src/utils/operacionesGrupos.js` — defaults accordion, keys API bandejas
- `Dockerfile` — bake-time flag Vite

---

## Estado final en producción

### Comportamiento Mi Taller (flag ON)

| Aspecto | Esperado | Validado |
|---------|----------|----------|
| Mount inicial | 1× `incluir_items=false` + bandejas capa0 | ✅ Smoke S1–S2 |
| Expandir bandeja | `bandejas=ot_pendientes` / `ot_en_proceso` / `ot_completadas` | ✅ Smoke S3–S5 |
| Requests legacy | **0×** `incluir_items=true` en flujo normal | ✅ Smoke S6 |
| Mutaciones OT | Delegadas a endpoints existentes (`iniciar`, `finalizar`, etc.) | ✅ Smoke S7 |

### Otros módulos operativos

Sin cambio: Dashboard, Caja Operativa y Recepción siguen usando resumen legacy (`incluir_items=true`, sin `bandejas=`).

### Flag y rollback

| Acción | Procedimiento |
|--------|---------------|
| **Estado actual** | `VITE_A0_SLICES_MI_TALLER=true` en Railway Variables |
| **Rollback a legacy** | Variable `false` o eliminar + **redeploy completo** |
| **Nota** | Flag es **build-time** — cambiar variable sin redeploy no tiene efecto |

Documentación operativa: [DEPLOY_RAILWAY.md §5.1](./DEPLOY_RAILWAY.md).

---

## Smoke UX-1B.3 — resultado

| Criterio | Resultado |
|----------|-----------|
| S1–S7 técnico | **PASS** |
| Usuario smoke | TÉCNICO `dsifuentes@medinaautodiag.com` |
| Fixture QA posterior | OT 56 (`OT-20260622-0001`) — cliente `Qa-Op*` |
| Rollback flag post-smoke | **No aplicado** — flag permanece ON por decisión operativa |

---

## Incidencia OT 47 (no bloqueante para cierre UX-1B)

Durante smoke S3 se finalizó accidentalmente **OT real** 47 (`OT-20260613-0001`, Manuel Mata) en lugar de fixture QA.

| Aspecto | Estado |
|---------|--------|
| **Impacto** | Operativo únicamente |
| **Financiero / inventario** | Sin impacto (sin venta, pago, entrega, repuestos) |
| **Corrección** | Reversión API → `EN_PROCESO` + higiene BD `fecha_finalizacion` / `id_usuario_finalizacion` |
| **Estado OT 47** | Activa en `EN_PROCESO`, coherente |
| **Postmortem** | [postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md](./postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md) |
| **Commit postmortem** | `1a5034a` — en `origin/main` |

La incidencia **no invalida** el PASS técnico de UX-1B.3; expone deuda de **proceso QA**, no de feature.

---

## Riesgos residuales (no bloqueantes)

| ID | Riesgo | Severidad | Notas |
|----|--------|-----------|-------|
| UX-TOAST-001 | Sin toast en `iniciar_ot` / `finalizar_ot` desde `AccionesOtRenderer` | Baja | UX feedback |
| UX-REFETCH-DUP | Posible refetch duplicado capa0 post-mutación | Baja | Performance menor |
| UX-ISSUE-002 | Accordion puede quedar expandido vacío tras mutación | Baja | UX edge case |
| QA-PROC-001 | Smokes con mutaciones pueden afectar OTs reales en prod | **Media (proceso)** | Ver backlog preventivo |
| DOC-001 | Sin plan formal QA Guardrails commiteado aún | Baja | Backlog pendiente |

Ninguno impide operación diaria de Mi Taller con slices ON.

---

## Pendientes preventivos — backlog QA Guardrails

**No implementados en este cierre.** Registro como backlog para sprint futuro:

| Prioridad | Acción |
|-----------|--------|
| **P0** | Mutaciones smoke prod **solo** sobre fixtures QA identificables |
| **P0** | Lista blanca de OTs QA en scripts; abort si id/número no coincide |
| **P0** | Verificación previa de cliente (`Qa-Op*`) y OT antes de `iniciar`/`finalizar` |
| **P1** | Fixture QA dedicado por smoke (crear al inicio, documentar id) |
| **P1** | Parametrizar `OT_QA_ID` / `OT_QA_NUMERO` en scripts |
| **P2** | Entorno staging con BD separada para smokes destructivos |
| **P2** | Marcado visual OTs QA en UI (evaluar en feature futuro) |

Detalle operativo en postmortem OT 47 §7.

---

## Criterios de cierre cumplidos

- [x] UX-1B.0 backend slices desplegado (`ab05b72`)
- [x] UX-1B.1 frontend lazy slices desplegado (`94990df`)
- [x] UX-1B.2 pipeline Docker/Vite desplegado (`43c8078`)
- [x] UX-1B.3 flag ON activo y smoke PASS
- [x] Rollback documentado y probado conceptualmente
- [x] Incidencia OT 47 corregida y documentada
- [x] Sin deuda funcional bloqueante en Mi Taller slices

---

## Commits de referencia (cadena UX-1B)

```
6f3de1b feat(ux): compact dashboard and mi taller with disclosure panels   ← UX-1A
ab05b72 feat(operaciones): A0 v2.1 slice params grupo and bandejas         ← UX-1B.0
94990df feat(ux): lazy load mi taller bandejas with A0 slices              ← UX-1B.1
43c8078 chore(deploy): wire VITE_A0_SLICES_MI_TALLER into Docker build     ← UX-1B.2
1a5034a docs(postmortem): document OT47 production smoke incident          ← post-incidente (docs)
```

---

## Próximos pasos recomendados (fuera de UX-1B)

1. Push autorizado del presente documento de cierre (commit separado, cuando se apruebe).
2. Implementar backlog QA Guardrails P0 antes del próximo smoke con mutaciones en prod.
3. Evaluar issues UX menores (TOAST, REFETCH, accordion) en backlog UX post-1B.
4. No abrir P5.2+ sin PRE-CHECK arquitectónico y plan aprobado.

---

*Hito UX-1B cerrado. Mi Taller en producción opera con lazy slices A0 v2.1 y flag ON.*
