# Postmortem — OT 47 finalizada accidentalmente en smoke UX-1B.3 (producción)

**Fecha del documento:** 22 de junio de 2026  
**Versión:** 1.0  
**Estado:** **CERRADO** — corrección aplicada y validada  
**Entorno:** `https://medinaautodiag.up.railway.app`  
**Alcance documental:** incidencia operativa aislada; **no modifica** documentación de UX-1B ni implica cambios funcionales.

**Referencias relacionadas (solo lectura):**

| Documento | Relación |
|-----------|----------|
| [DEPLOY_RAILWAY.md](./DEPLOY_RAILWAY.md) | Flag `VITE_A0_SLICES_MI_TALLER` y despliegue Railway |
| [CIERRE_P3_1_MI_TALLER.md](./CIERRE_P3_1_MI_TALLER.md) | Contexto operativo de Mi Taller y mutaciones `iniciar`/`finalizar` |

---

## 1. Resumen ejecutivo

### Qué ocurrió

Durante el smoke post-deploy **UX-1B.3** (activación de slices Mi Taller con `VITE_A0_SLICES_MI_TALLER=true`), el paso **S3** ejecutó la acción **`finalizar_ot`** sobre una **orden de trabajo real** del taller — **OT 47** (`OT-20260613-0001`, cliente Manuel Mata) — en lugar de limitarse a un fixture QA identificable.

La OT pasó de `EN_PROCESO` a `COMPLETADA` sin que el trabajo estuviera terminado operativamente.

### Fecha / hora

| Evento | Timestamp (registro sistema) |
|--------|------------------------------|
| Finalización accidental | **2026-06-22 14:51:36** (`fecha_finalizacion` / auditoría `FINALIZAR`) |
| Detección y análisis | 2026-06-22 (misma sesión de smoke / validación) |
| Reversión vía API | 2026-06-22 |
| Higiene BD puntual | 2026-06-22 |
| Cierre incidencia | 2026-06-22 |

### Alcance

- **Afectado:** una OT real (id 47), cliente real, vehículo en taller.
- **No afectado:** feature UX-1B.3 (smoke técnico S1–S7 **PASS**), flag de slices, resto de OTs, ventas, pagos, entrega, inventario, auditoría histórica.
- **Usuarios involucrados:** técnico smoke `dsifuentes@medinaautodiag.com` (id 2); corrección con rol ADMIN.

### Severidad

| Dimensión | Nivel | Notas |
|-----------|-------|-------|
| **Operativa** | Media | OT real fuera de bandeja correcta hasta corrección |
| **Financiera** | Ninguna | Sin venta ni cobro |
| **Datos / integridad** | Baja | Reversible; sin pérdida de historial |
| **Cliente final** | Baja* | Sin entrega ni cobro; OT restaurada a flujo activo |

\* Riesgo reputacional/operativo si el taller hubiera actuado sobre estado incorrecto; mitigado al revertir el mismo día.

---

## 2. Línea de tiempo

| # | Momento | Detalle |
|---|---------|---------|
| 1 | **Contexto previo** | OT 47 creada **2026-06-13** (recepción rápida). Iniciada **2026-06-13 13:39** → `EN_PROCESO`. ~9 días en reparación (revisión suspensión, ruido lado izquierdo delantero). |
| 2 | **Deploy UX-1B.3** | `railway variable set VITE_A0_SLICES_MI_TALLER=true` + redeploy. Smoke S1–S7 planificado con flag ON. |
| 3 | **Inicio smoke UX-1B.3** | Validación Mi Taller en modo slices (`incluir_items=false`, bandejas `ot_pendientes` / `ot_en_proceso`). |
| 4 | **Finalización accidental OT 47** | Smoke **S3** (`finalizar_ot`) sobre OT visible en bandeja del técnico — **OT real** en lugar de fixture QA. Auditoría: `FINALIZAR` **2026-06-22 14:51:37**. |
| 5 | **Detección** | Identificación de OT afectada: id **47**, `OT-20260613-0001`, Manuel Mata, Chevrolet Equinox 2013. Confirmación: `id_venta` null, sin entrega. Fixture QA correcto del smoke: **OT 56** (`OT-20260622-0001`). |
| 6 | **Análisis y autorización** | Decisión: **no rollback del flag**; corregir solo datos de OT 47. UX-1B.3 permanece **PASS**. |
| 7 | **Reversión (Paso 1)** | `PUT /api/ordenes-trabajo/47` con `estado: EN_PROCESO` + observación técnica de corrección. HTTP 200. |
| 8 | **Validación post-reversión** | GET OT 47 → `EN_PROCESO`. Bandejas: OT en `ot_en_proceso`, ausente de `ot_completadas`. Sin venta/entrega/inventario. |
| 9 | **Higiene BD (Paso 2)** | `UPDATE` puntual: `fecha_finalizacion = NULL`, `id_usuario_finalizacion = NULL` (condiciones de seguridad cumplidas). **1 fila** afectada. |
| 10 | **Validación final API** | GET OT 47: `EN_PROCESO`, `fecha_finalizacion` null, observaciones intactas. |
| 11 | **Cierre** | Incidencia OT 47 declarada cerrada. Prevención obligatoria documentada para smokes futuros. |

---

## 3. Impacto

### Operativo

- OT 47 apareció temporalmente en bandeja **`ot_completadas`** con estado `COMPLETADA`.
- Tras corrección: vuelve a **`ot_en_proceso`** para técnico asignado (id 2).
- Flujo taller (iniciar → reparar → finalizar → cobrar → entregar) **no avanzó** más allá del cierre erróneo.

### Financiero

- **Sin impacto.** `id_venta` null antes, durante y después de la corrección.
- Sin pagos, saldos pendientes ni movimientos de caja asociados.

### Inventario

- **Sin impacto.** OT 47 con **0 repuestos**; `finalizar_ot` no consumió stock.

### Cliente

- **Manuel Mata** / Chevrolet Equinox 2013.
- Vehículo **no entregado** (`fecha_entrega` null).
- OT **restaurada** a estado activo coherente con trabajo en curso.
- Observación técnica registrada para trazabilidad interna (sin borrar auditoría previa).

---

## 4. Causa raíz

### Uso de OT real durante smoke con mutaciones

El smoke UX-1B.3 incluía mutaciones reales en producción (`iniciar_ot`, `finalizar_ot`) desde Mi Taller. La primera OT elegible en bandeja del técnico smoke era una **OT real en `EN_PROCESO`** (OT 47), no un fixture QA previamente aislado.

### Ausencia de validación explícita de fixture QA

- No existía **lista blanca** de OTs permitidas para mutación en scripts/smoke manual.
- No había **guardrail** que rechace finalizar OTs cuyo cliente no cumpla convención QA (p. ej. prefijo `Qa-Op*`).
- El fixture QA (**OT 56**) se creó/usó **después** de detectar el error sobre OT 47.

### Factores contribuyentes

| Factor | Descripción |
|--------|-------------|
| Entorno prod compartido | Datos reales y QA conviven en la misma BD |
| Smoke manual | Selección visual de OT sin verificación previa de id/número/cliente |
| Usuario técnico real | Cuenta smoke con OTs reales asignadas en bandeja |

---

## 5. Corrección aplicada

### 5.1 Reversión API (Paso 1 — autorizado)

```http
PUT /api/ordenes-trabajo/47
Authorization: Bearer <ADMIN>
Content-Type: application/json

{
  "estado": "EN_PROCESO",
  "observaciones_tecnico": "[Corrección 2026-06-22] Revertido de COMPLETADA por finalización accidental en smoke UX-1B.3. Trabajo sigue en curso."
}
```

**Resultado:** HTTP 200, estado `EN_PROCESO`. Auditoría `ACTUALIZAR` registrada. Entrada `FINALIZAR` previa **conservada**.

**Pre-checks ejecutados antes del PUT:**

- `id = 47`, `numero_orden = OT-20260613-0001`
- `estado = COMPLETADA`
- `id_venta` null (API)
- `fecha_entrega` null

### 5.2 Limpieza BD puntual (Paso 2 — autorizado)

**Nota técnica:** `id_venta` no es columna física en `ordenes_trabajo`; la condición de seguridad se aplicó con subconsulta equivalente (`NOT EXISTS` venta activa en `ventas.id_orden`).

```sql
-- SELECT antes: fecha_finalizacion = 2026-06-22 14:51:36, id_usuario_finalizacion = 2

UPDATE ordenes_trabajo
SET fecha_finalizacion = NULL,
    id_usuario_finalizacion = NULL
WHERE id = 47
  AND numero_orden = 'OT-20260613-0001'
  AND estado = 'EN_PROCESO'
  AND fecha_entrega IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM ventas v
    WHERE v.id_orden = ordenes_trabajo.id AND v.estado != 'CANCELADA'
  );

-- SELECT después: fecha_finalizacion = NULL, id_usuario_finalizacion = NULL
-- Filas afectadas: 1
```

**Ejecución:** `railway run` contra BD producción (Aiven). Sin cambios en observaciones, auditoría, ventas ni flag.

### 5.3 Validaciones posteriores

| Validación | Resultado |
|------------|-----------|
| `GET /ordenes-trabajo/47` | `EN_PROCESO`, `fecha_finalizacion` null, `id_venta` null |
| Bandeja `ot_en_proceso` (técnico / ADMIN) | OT 47 **presente** |
| Bandeja `ot_completadas` | OT 47 **ausente** |
| Ventas / pagos / entrega / inventario | Sin cambios |

---

## 6. Lecciones aprendidas

1. **Smokes con mutaciones en producción son de alto riesgo** cuando conviven datos reales y de prueba en la misma instancia.
2. **La bandeja operativa no distingue OT real vs QA** — cualquier OT visible es candidata a clic accidental o smoke mal dirigido.
3. **El endpoint `finalizar_ot` no valida** si la OT pertenece a un cliente/convención QA; la protección debe estar en el proceso de prueba, no en el negocio.
4. **La reversión parcial vía API** (`estado` sin limpiar `fecha_finalizacion`) deja inconsistencia visible; conviene planificar higiene de campos huérfanos cuando el schema de update no los expone.
5. **UX-1B.3 puede ser PASS técnicamente** aunque ocurra una incidencia de datos; separar criterio de feature vs criterio de operación segura en prod.

---

## 7. Acciones preventivas

### Obligatorias (inmediatas — proceso)

| # | Acción | Responsable |
|---|--------|-------------|
| P1 | **Solo fixtures QA** en smokes con mutaciones en prod | QA / quien ejecute smoke |
| P2 | **Lista blanca de OTs QA** — abortar si `id` / `numero_orden` no está en lista | Scripts y checklist manual |
| P3 | **Verificación previa** de cliente (`Qa-Op*`, etc.) y número OT antes de `iniciar` / `finalizar` | Operador smoke |
| P4 | **Prohibido mutar OTs reales** para pruebas post-deploy | Política de equipo |

### Recomendadas (mediano plazo — sin implementar en este postmortem)

| # | Acción | Notas |
|---|--------|-------|
| R1 | **Entorno staging** con BD separada para smokes destructivos | Reduce riesgo en prod |
| R2 | **Scripts smoke con assert pre-mutación** | Validar cliente/OT antes de POST |
| R3 | **Marcado visual OTs QA** en UI (badge) o campo `es_fixture_qa` | Facilita distinguir en bandeja |
| R4 | **Filtrar OTs reales** en scripts automatizados (`cliente NOT LIKE 'Qa-%'`) | Guardrail en código — requiere plan aparte |

---

## 8. Estado final

| Ítem | Estado |
|------|--------|
| **OT 47** | Restaurada — `EN_PROCESO`, fechas de finalización limpias, observación de corrección registrada |
| **Cliente / vehículo** | Manuel Mata / Chevrolet Equinox 2013 — sin entrega, sin cobro |
| **UX-1B.3** | **Aprobado (PASS)** — smoke S1–S7 técnico OK con slices ON |
| **Flag producción** | `VITE_A0_SLICES_MI_TALLER=true` — **permanece activo** (sin rollback) |
| **Incidencia OT 47** | **CERRADA** |

---

## Anexo — Datos de referencia OT 47

| Campo | Valor final |
|-------|-------------|
| id | 47 |
| numero_orden | OT-20260613-0001 |
| estado | EN_PROCESO |
| cliente | Manuel Mata |
| vehículo | Chevrolet Equinox 2013 |
| tecnico_id | 2 |
| total | $200 (revisión suspensión) |
| id_venta | null |
| fecha_entrega | null |
| fecha_finalizacion | null (post-higiene) |

**Fixture QA de referencia para smokes futuros:** OT 56 — `OT-20260622-0001` (cliente `Qa-Op100 Cliente Walkin 06161715`).

---

*Documento generado como registro post-incidente. No sustituye planes de feature UX-1B ni autoriza cambios de código por sí solo.*
