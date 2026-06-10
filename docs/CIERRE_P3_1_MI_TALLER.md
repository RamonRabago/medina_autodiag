# Cierre P3.1 — Mi Taller

**Versión:** 1.0  
**Fecha:** 10 de junio de 2026  
**Estado:** ✅ **CERRADO EN PRODUCCIÓN** — validado operativamente  
**Entorno:** `https://medinaautodiag.up.railway.app`

**Referencias:**

- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)
- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)

---

## Resumen ejecutivo

P3.1 Mi Taller fue desplegado y validado en producción con flujo operativo real de punta a punta. El técnico ejecutó **iniciar** y **finalizar** exclusivamente desde `/operaciones/mi-taller`, sin usar botones del módulo legacy de Órdenes de Trabajo para el trabajo operativo.

| Campo | Valor |
|-------|-------|
| **Commit desplegado** | `658a3a2` — feat: add mi taller operative view |
| **Deployment Railway** | `9dee9714-5aaf-4d43-b3d2-e5b4770407a3` |
| **build_rev prod** | `658a3a2c103f` |
| **Alembic** | No aplicó (sin migración en P3.1) |

---

## Objetivo de validación

Confirmar flujo operativo real:

```
Recepción → OT → Técnico → Iniciar → En proceso → Finalizar → Completadas
```

Sin utilizar el módulo legacy de Órdenes de Trabajo para **ejecutar** el trabajo (iniciar/finalizar). La preparación de la OT (servicios, técnico) puede hacerse fuera de Mi Taller — coherente con el diseño P3.1.

---

## Caso probado en producción

| Campo | Valor |
|-------|-------|
| **OT** | OT-20260610-0001 (id 46) |
| **Cliente** | Angel Aaron Rabago Garcia |
| **Vehículo** | Chevrolet Cobalt 2007 |
| **Técnico** | Demetrio Sifuentes Díaz |
| **Servicio** | Escaneo computarizado |

---

## Flujo validado — evidencia de bandejas

Usuario: **TECNICO** en `/operaciones/mi-taller`.

| Momento | Pendientes | En proceso | Completadas |
|---------|------------|------------|-------------|
| **Estado inicial** | 1 | 0 | 4 |
| **Tras Iniciar** | 0 | 1 | 4 |
| **Tras Finalizar** | 0 | 0 | 5 |

Transición de estado en BD:

```
PENDIENTE → EN_PROCESO → COMPLETADA
```

Refetch automático tras mutación — **sin F5 manual**.

---

## Componentes arquitectónicos validados

### A0 — Capa Operativa Central

| Bandeja | Resultado |
|---------|-----------|
| `ot_pendientes` | Refleja OT asignadas al técnico |
| `ot_en_proceso` | Actualiza al iniciar |
| `ot_completadas` | Incrementa al finalizar; solo lectura |

### ot_acciones_service

- UI consume `acciones[]` del evaluador.
- No se detectó desalineación **A0 `permitida=true` + API rechaza** durante el caso probado.
- Botones gobernados por `permitida`; no por `estado`/`rol` local en frontend.

### React Query

- Mutaciones `iniciar_ot` / `finalizar_ot` invalidan resumen y actualizan bandejas automáticamente.

### Filtro por técnico

- Demetrio solo visualiza OT con `tecnico_id` propio en bandejas A0.

### Completadas

- Tarjetas en solo lectura.
- Sin acciones operativas (`acciones = []` en A0).

---

## Smoke post-deploy (automático + manual)

| Check | Resultado |
|-------|-----------|
| `GET /health` | 200 |
| A0 ADMIN / TECNICO / CAJA | 200; bandeja `ot_completadas` presente |
| Mi Taller ADMIN / TECNICO | Carga OK; 3 bandejas visibles |
| CAJA menú Mi Taller | No visible; redirect en acceso directo |
| Regresión Citas V2 | OK |
| Regresión Recepción rápida | OK |
| Regresión alta rápida cliente CAJA | OK |

---

## Alcance validado vs excluido

### Validado ✅

- Bandejas A0 (`ot_pendientes`, `ot_en_proceso`, `ot_completadas`)
- Acciones OT inline (`iniciar_ot`, `finalizar_ot`)
- Inicio y finalización de trabajo desde Mi Taller
- Refetch automático
- Restricción por técnico
- Completadas solo lectura
- Menú por rol (TECNICO, ADMIN)

### Excluido (fuera de P3.1) — sin regresión reportada

- Pausar / reanudar refacción
- Cronómetros y métricas de productividad
- Asignación de técnico desde Mi Taller
- Bandeja sin asignar
- Cobros, entrega, cancelar, autorizar en Mi Taller
- P4 Caja Operativa
- P5 Dashboard por rol

---

# Backlog arquitectónico — hallazgos

## Hallazgos UX (Mi Taller)

### P3-UX-001 — Motivo de bloqueo más visible

| Campo | Valor |
|-------|-------|
| **Situación** | OT con `codigo_bloqueo = SIN_ITEMS` muestran botón gris; motivo solo en hover |
| **Ejemplo** | *"La orden debe tener al menos un servicio o repuesto antes de continuar."* |
| **Propuesta** | Mensaje visible, badge contextual o alerta inline |
| **Prioridad** | Media |

### P3-UX-002 — Affordance de botones bloqueados

| Campo | Valor |
|-------|-------|
| **Situación** | Existe tooltip pero no es evidente que el botón contiene explicación |
| **Propuesta** | Cursor help, ícono información, indicador visual |
| **Prioridad** | Baja |

### P3-UX-003 — Consistencia estado vs etiqueta operativa

| Campo | Valor |
|-------|-------|
| **Situación** | Tarjeta muestra *Estado: Pendiente recepción* mientras badge muestra `PENDIENTE` |
| **Propuesta** | Revisar alineación entre `estado`, `estado_operativo`, `etiqueta_estado` |
| **Prioridad** | Media |

### P3-UX-004 — Contexto temporal operativo

| Campo | Valor |
|-------|-------|
| **Situación** | Tarjetas muestran fecha de ingreso; en proceso sería útil fecha de inicio o tiempo transcurrido |
| **Propuesta** | *"Iniciada hace 15 min"* o *"En proceso desde 10:32 AM"* |
| **Prioridad** | Baja |

### P3-UX-005 — Limpiar fecha promesa (modal Editar OT)

| Campo | Valor |
|-------|-------|
| **Situación** | En el modal **Editar OT** (`OrdenesTrabajo.jsx`), una vez capturada una fecha promesa no existe botón para limpiar el campo, ícono X ni acción rápida para volver a `NULL`. El usuario debe borrar manualmente el valor del control `datetime-local` o cerrar y reabrir el modal. |
| **Impacto** | Bajo — genera fricción durante edición rápida de OT en mostrador |
| **Propuesta** | Junto al campo `datetime-local`: botón **Limpiar** o ícono **X** que establezca `fecha_promesa = null` en el formulario y envíe `null` en el PUT al guardar |
| **Prioridad** | Baja |
| **Bloquea P3.1 / Mi Taller** | No |
| **Nota** | Hallazgo detectado durante preparación de OT de prueba; aplica al módulo OT legacy, no a Mi Taller |

### P3-UX-006 — Modos semánticos ADMIN vs TECNICO en Mi Taller

| Campo | Valor |
|-------|-------|
| **Situación** | La misma ruta `/operaciones/mi-taller` cambia semántica según rol: **ADMIN** muestra *"Supervisión operativa de órdenes de trabajo"*; **TECNICO** muestra *"Tus trabajos pendientes, en proceso y completados recientes"*. Comportamiento correcto, pero no está documentado como modos explícitos. |
| **Recomendación P3.2** | Documentar y evolucionar dos modos: **Modo Supervisor (ADMIN)** — vista global, nombre de técnico en tarjetas; **Modo Operativo (TECNICO)** — solo OT propias, acciones inline. Futuras features (métricas, asignación) deben declarar en qué modo aplican. |
| **Prioridad** | Documentación / diseño (no bug) |
| **Referencia código** | `frontend/src/pages/operaciones/MiTaller.jsx` — `showTecnico`, subtítulo por `user.rol` |

---

## Hallazgos funcionales (módulo OT legacy)

### OT-FECHAS-V1 — Bug de timezone en fechas OT

| Campo | Valor |
|-------|-------|
| **Tipo** | Deuda técnica / bug timezone |
| **Detectado en** | Edición OT-20260610-0001 (preparación para Mi Taller) |
| **Causa** | `fecha_ingreso` usa `datetime.now()` (UTC en Railway); otros módulos usan `ahora_local()` |
| **Validación** | `fecha_promesa < fecha_ingreso` compara datetimes naive en bases distintas |
| **Ejemplo prod** | `fecha_ingreso = 2026-06-10 13:17:22`; payload `2026-06-10T09:50` → rechazo incorrecto desde perspectiva del usuario |
| **Ubicación** | `app/routers/ordenes_trabajo/crud.py` líneas 214–218, 635–639 |
| **Bloquea P3.1** | **No** — workaround: dejar `fecha_promesa` vacía |
| **Prioridad fix** | Media (afecta recepción/edición OT, no Mi Taller) |

### OT-UX-001 — Limpiar fecha promesa

Alias funcional de **P3-UX-005** (mismo hallazgo, numeración legacy OT). Ver detalle en P3-UX-005.

---

## Observaciones operativas en producción

Durante la validación se confirmaron OT reales pendientes con:

- `codigo_bloqueo = SIN_ITEMS` — recepciones rápidas sin servicios/repuestos agregados

**Métricas futuras recomendadas** (candidatas P5 / extensión A0):

| Métrica | Uso |
|---------|-----|
| OT pendientes sin ítems | Supervisión recepción |
| OT pendientes sin técnico | Asignación (D1) |
| OT pendientes sin autorización | Flujo cotización |
| OT bloqueadas por stock | Inventario / compras |

---

# Estado oficial del hito

| Campo | Valor |
|-------|-------|
| **Hito** | P3.1 Mi Taller |
| **Estado** | ✅ CERRADO EN PRODUCCIÓN |
| **Resultado** | VALIDADO OPERATIVAMENTE |
| **Fecha cierre** | 2026-06-10 |

---

# Siguiente decisión arquitectónica

**No iniciar desarrollo automáticamente.** Requiere aprobación explícita del negocio.

## Opción A — P3.2 Mi Taller

| Aspecto | Detalle |
|---------|---------|
| **Enfoque** | Profundizar experiencia del técnico |
| **Entregables típicos** | P3-UX-001..006, modos Supervisor/Operativo, pausar refacción, métricas productividad, asignación técnico, `LineasOrdenEditor` |
| **Consume A0** | Sí — mismas bandejas |
| **Impacto operativo inmediato** | Medio-alto para **técnicos** |
| **Riesgo** | Scope creep si se mezcla con D1 (asignación obligatoria) |
| **Dependencias** | P3.1 cerrado ✅ |

## Opción B — P4 Caja Operativa

| Aspecto | Detalle |
|---------|---------|
| **Enfoque** | Cierre financiero y entrega desde Operaciones |
| **Entregables típicos** | `/operaciones/caja`, `FlujoCobroModal`, `FlujoEntregaModal`, bandejas `ot_pendientes_cobro`, `ot_listas_entrega` |
| **Consume A0** | Sí — bandejas financieras ya existen en A0 |
| **Impacto operativo inmediato** | Alto para **CAJA / mostrador** — cierra ciclo recepción → trabajo → cobro → entrega |
| **Riesgo** | Integración contable, turno de caja, permisos |
| **Dependencias** | A0 + evaluador acciones ✅; Mi Taller opcional pero deseable |

## Matriz comparativa

| Criterio | P3.2 Mi Taller | P4 Caja Operativa |
|----------|----------------|-------------------|
| Usuario principal | TECNICO | CAJA / ADMIN |
| Cierra ciclo de valor completo | Parcial (solo taller) | **Sí** (cobro + entrega) |
| Aprovecha A0 existente | Bandejas OT | **Bandejas financieras** |
| Deuda detectada en validación | UX Mi Taller | OT-FECHAS-V1 afecta edición previa a cobro |
| Urgencia operativa típica | Mejora continua | **Flujo de ingresos** |
| Complejidad estimada | Media | Media-alta |

## Recomendación (impacto operativo) — acordada post-cierre P3.1

**Secuencia de roadmap aprobada:**

1. **Hotfix OT-FECHAS-V1** — urgente operativa: genera tickets diarios en edición OT (timezone); scope acotado, sin Alembic
2. **P4 Caja Operativa** — cierra ciclo recepción → trabajo → cobro → entrega; A0 ya expone bandejas financieras
3. **P3.2 Mi Taller** — UX (P3-UX-001..006), modos Supervisor/Operativo, funciones técnicas avanzadas
4. **P5 Dashboard por rol** — métricas OT sin ítems, bloqueos SIN_ITEMS, etc.

**Razonamiento:**

1. **P3.1 está operativo y validado** — no requiere más trabajo para producción diaria del técnico.
2. **OT-FECHAS-V1** afecta mostrador/recepción al editar OT; puede confundir usuarios **cada día** aunque no bloquee Mi Taller.
3. **P4** materializa el siguiente eslabón del ciclo de valor (cobro + entrega) con backend ya listo en A0.
4. **P3.2** es mejora incremental; quick wins (P3-UX-001 motivo bloqueo visible) pueden hacerse en paralelo sin bloquear P4.

**Nota:** P4 sigue siendo el hito funcional mayor tras el hotfix de fechas; el hotfix no sustituye P4, lo **desbloquea operativamente** en mostrador.

---

## Control de versiones del documento

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-06-10 | Cierre validación producción P3.1; backlog UX/funcional; análisis P3.2 vs P4 |
| 1.1 | 2026-06-10 | P3-UX-005, P3-UX-006; roadmap OT-FECHAS-V1 → P4 → P3.2 → P5 |
