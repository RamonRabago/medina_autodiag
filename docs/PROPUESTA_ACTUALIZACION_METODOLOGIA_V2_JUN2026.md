# Propuesta DOCS-ONLY — Actualización METODOLOGIA_DESARROLLO_V2.md

**Versión:** 1.0  
**Fecha:** 22 de junio de 2026  
**Estado:** 📋 **PROPUESTA** — pendiente revisión y commit docs separado  
**Archivo objetivo:** [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)  
**Tipo:** Solo documentación — **sin cambios funcionales**

**Motivo:** La memoria de proyecto en METODOLOGIA está desactualizada respecto a hitos cerrados en prod (P5.2 F1, P5.3 F1, UX-1A/1B) y no incluye regla post-incidente OT47.

---

## 1. Resumen de cambios propuestos

| Sección | Acción |
|---------|--------|
| § Memoria de proyecto | Ampliar tabla hitos cerrados |
| § Reglas gobernanza | Actualizar regla P5.2+; añadir smokes prod |
| § Roadmap oficial | Nota de extensiones P5.x y UX cerradas |
| Control versiones | Entrada v1.2.2 |

---

## 2. Cambio A — Tabla «Memoria de proyecto» (§ línea ~162)

### Texto actual

```markdown
| Dashboard por rol (P5.1) | ✅ Cerrado |
| Dashboard resumen CAJA / extensiones P5 (P5.2+) | 🔲 **No abierto** — requiere plan y autorización |
```

### Texto propuesto (reemplazo filas P5.1 en adelante)

```markdown
| Dashboard por rol (P5.1) | ✅ Cerrado |
| Recepción operativa enriquecida (P5.2 F1) | ✅ Cerrado |
| Optimización A0 light (P5.3 F1) | ✅ Cerrado |
| Accordion operativo Dashboard / Mi Taller (UX-1A) | ✅ Cerrado |
| Mi Taller lazy slices A0 v2.1 (UX-1B) | ✅ Cerrado — flag prod ON |
| Timezone taller Matamoros (TZ-1) | ✅ Cerrado |
| Optimización A0 heavy (P5.3 F2) | 🔲 Plan + PRE-CHECK — no implementado |
| Cotización PDF cliente (P5.4) | 🔲 Plan aprobado — no implementado |
| P5.2 F2 / P5.3 F3+ / P6 / P6.0 | 🔲 Requiere plan y autorización explícita |
```

---

## 3. Cambio B — Regla gobernanza «P5.2+ no abiertos» (§ línea ~156)

### Texto actual

```markdown
| **P5.2+ no abiertos** | No iniciar fases futuras sin PRE-CHECK y autorización explícita |
```

### Texto propuesto

```markdown
| **Fases no cerradas (P5.3 F2+)** | No iniciar sin PRE-CHECK aprobado y autorización explícita — ver `docs/PRE_CHECK_*.md` |
| **Fases cerradas P1–UX-1B** | Congeladas salvo bug demostrado con reproducción y evidencia |
| **Smokes prod con mutaciones** | **Solo fixtures QA** (`Qa-Op*`) — ver [PLAN_QA_GUARDRAILS.md](./PLAN_QA_GUARDRAILS.md) |
```

---

## 4. Cambio C — Nueva subsección «Smokes en producción» (insertar tras Reglas gobernanza)

```markdown
### Smokes en producción (obligatorio desde jun 2026)

Tras incidencia OT47 ([postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md](./postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md)):

| Tipo smoke | Regla |
|------------|-------|
| **Solo lectura** (GET health, resumen, config) | Permitido con credenciales autorizadas |
| **Con mutaciones** (iniciar/finalizar OT, POST cliente, etc.) | **Solo** entidades fixture QA — prefijo cliente `Qa-Op*` + id en lista blanca del script |
| **Prohibido** | Mutar OTs, citas o ventas de clientes reales del taller |
| **Gate** | Implementar [PLAN_QA_GUARDRAILS.md](./PLAN_QA_GUARDRAILS.md) antes del próximo smoke mutante |

**UX-1B flag prod:** `VITE_A0_SLICES_MI_TALLER=true` — documentado en [CIERRE_UX_1B_MI_TALLER_SLICES.md](./CIERRE_UX_1B_MI_TALLER_SLICES.md). Rollback: [DEPLOY_RAILWAY.md](./DEPLOY_RAILWAY.md) §5.1.
```

---

## 5. Cambio D — Roadmap oficial (§ línea ~501) — nota al pie

### Añadir después de la tabla roadmap

```markdown
**Extensiones cerradas en prod (jun 2026):** P5.2 F1, P5.3 F1, UX-1A, UX-1B (Mi Taller slices ON).  
**Documentos de cierre:** `docs/CIERRE_P5_*.md`, `docs/CIERRE_UX_1B_MI_TALLER_SLICES.md`.

**Prioridad operativa inmediata (proceso):** QA Guardrails P0 → P5.3 F2 (PRE-CHECK aprobado).
```

---

## 6. Cambio E — Documentos relacionados (§ ecosistema V2)

### Añadir filas a la tabla

```markdown
| [PLAN_QA_GUARDRAILS.md](./PLAN_QA_GUARDRAILS.md) | Smokes prod — fixtures QA obligatorios |
| [PRE_CHECK_P5_3_FASE2.md](./PRE_CHECK_P5_3_FASE2.md) | PRE-CHECK P5.3 Fase 2 (pendiente GO) |
| [CIERRE_UX_1B_MI_TALLER_SLICES.md](./CIERRE_UX_1B_MI_TALLER_SLICES.md) | Cierre UX-1B slices ON |
| [postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md](./postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md) | Incidencia smoke prod jun 2026 |
```

---

## 7. Cambio F — Control de versiones (final del documento)

```markdown
| 1.2.2 | Jun 2026 | Memoria P5.2 F1, P5.3 F1, UX-1A/1B, TZ-1; regla smokes prod QA; referencias guardrails y PRE-CHECK P5.3 F2 |

**Próxima revisión:** tras cierre P5.3 F2 o apertura P5.4.
```

---

## 8. Qué NO cambia en esta propuesta

- Los 10 principios de desarrollo
- PRE-CHECK checklist genérico
- Directiva no abandonar flujo operativo
- Roadmap P1–P6 orden prioritario
- Reglas Alembic, permisos backend, design system

---

## 9. Commit sugerido (cuando se apruebe)

```
docs(metodologia): sync closed milestones and prod smoke guardrails
```

**Archivos staged explícitamente:**

- `docs/METODOLOGIA_DESARROLLO_V2.md`

**Opcional mismo commit o separado:**

- `docs/PLAN_QA_GUARDRAILS.md`
- `docs/PRE_CHECK_P5_3_FASE2.md`

**No usar** `git add .`

---

## 10. Aprobación requerida

- [ ] Usuario aprueba texto propuesto §2–7
- [ ] Aplicar cambios a METODOLOGIA
- [ ] Commit docs-only separado de implementación guardrails/scripts

---

*Propuesta docs-only — no modifica `METODOLOGIA_DESARROLLO_V2.md` hasta aprobación.*
