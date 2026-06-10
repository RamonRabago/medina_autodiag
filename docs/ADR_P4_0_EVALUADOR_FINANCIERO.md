# ADR-P4.0 — Evaluador Financiero y Contrato A0 v2

**Estado:** ✅ **APROBADO**  
**Fecha:** Junio 2026  
**Decisor:** Arquitectura / Negocio  
**Relacionado:** [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md) · [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md) · [PLAN_A0_CAPA_OPERATIVA_CENTRAL.md](./PLAN_A0_CAPA_OPERATIVA_CENTRAL.md)

---

## Contexto

Tras el cierre de P3.1 Mi Taller y la auditoría arquitectónica de tercer nivel, se identificó que P4.0 no puede implementarse como ajuste funcional aislado. Existen inconsistencias entre `GET /api/operaciones/resumen` (A0) y las mutaciones reales (`POST /api/pagos/`, ventas desde OT), duplicidad de bandejas financieras y `registrar_pago` fuera del evaluador central.

Este ADR es la **fuente normativa** para la implementación de P4.0.

---

## Decisión

Aprobar P4.0 como **extensión obligatoria de la Capa Operativa Central (A0)** con:

1. Contrato **A0 v2** (`meta.version_contrato = "a0-v2"`).
2. Nuevo módulo **`acciones_operativas_service`** como fachada del evaluador financiero-operativo.
3. Política **`acciones_globales`** sin mutaciones financieras permitidas.
4. **Deduplicación** como regla de dominio en `OperacionesService`.
5. **P4.1 UI bloqueada** hasta P4.0 implementado y validado.

---

## 1. Contrato A0 v2

### 1.1 Obligatoriedad

**A0 v2 es obligatorio para P4.0.** Mantener `a0-v1` con las nuevas reglas introduce deuda documental y operativa.

| Cambio v2 | Impacto |
|-----------|---------|
| Deduplicación `ventas_saldo_pendiente` vs `ot_pendientes_cobro` | Semántica de bandeja distinta |
| `registrar_pago` evaluado (turno, saldo, venta) | `permitida` distinta por ítem |
| `acciones_globales.registrar_pago` nunca `permitida=true` | Corrección de contrato |

### 1.2 Versión

```text
meta.version_contrato = "a0-v2"
```

Cambios normativos incluidos en v2:

- `deduplicacion_bandejas_financieras`
- `evaluador_registrar_pago`
- `acciones_globales_alineadas`

### 1.3 Estructura `acciones[]` (por ítem)

Unidad: acción evaluada sobre **una entidad concreta** en una bandeja.

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `accion` | Sí | Código estable del catálogo |
| `permitida` | Sí | Si la mutación delegada debe aceptarse |
| `motivo_bloqueo` | Si `permitida=false` | Texto para UI |
| `codigo_bloqueo` | Si `permitida=false` | Código estable (`TURNO_CERRADO`, etc.) |
| `contexto` | Opcional v2 | Metadatos informativos (`id_venta`, `saldo_pendiente`, …) |

**Invariante R-A1:** Toda acción mutante en superficies operativas se renderiza **solo** desde `acciones[]` del ítem.

**Invariante R-A2:** `permitida=true` implica que el POST delegado no fallará por reglas que el evaluador conoce (turno, saldo, rol, estado de entidad).

### 1.4 Estructura `acciones_globales[]`

**Propósito v2:** capacidades de **sesión/navegación**, no botones de mutación financiera.

| Campo | Uso v2 |
|-------|--------|
| `alcance` | `"global"` \| `"item_only"` (documentación / contrato) |

**Decisión normativa (punto 3 y 4 del mandato):**

- `acciones_globales` **no debe** exponer `registrar_pago` con `permitida=true`.
- `registrar_pago` es **`item_only`**: requiere contexto de entidad (`orden_trabajo` o `venta`).

Representación en global:

```json
{
  "accion": "registrar_pago",
  "permitida": false,
  "motivo_bloqueo": "Disponible en ítems de bandeja Por cobrar o Ventas con saldo",
  "codigo_bloqueo": "REQUIERE_CONTEXTO_ENTIDAD",
  "alcance": "item_only"
}
```

**Invariante I-G1:** No existe construcción manual de acciones financieras por rol en `OperacionesService`.

**Invariante I-G2:** Global e ítem invocan la **misma función** evaluadora; la diferencia es política de `alcance`.

**Invariante I-G3:** Tests contractuales: acciones `item_only` nunca `permitida=true` en global.

### 1.5 Compatibilidad hacia atrás

| Consumidor | Impacto |
|------------|---------|
| **Mi Taller P3.1** | Sin cambio funcional de bandejas técnicas; recibe `a0-v2` en meta |
| **Caja Operativa P4.1** | Depende de v2 |
| **Legacy** (`/ventas`, `/ordenes-trabajo`) | Sin impacto (no consumen A0) |

No mantener dos code paths v1/v2 en backend.

---

## 2. Evaluador operativo — `acciones_operativas_service`

### 2.1 Decisión (punto 5 del mandato)

Crear **`app/services/acciones_operativas_service.py`** como fachada pública del evaluador financiero-operativo para A0.

**No** implementar `registrar_pago` como lógica final dentro de `ot_acciones_service` (dominio OT ≠ entidad Venta).

### 2.2 Responsabilidades

| Módulo | Responsabilidad |
|--------|-----------------|
| **`acciones_operativas_service`** | `evaluar_registrar_pago`, `evaluar_crear_venta_desde_ot`, `evaluar_entregar_vehiculo`; fachada para A0 |
| **`ot_acciones_service`** | Acciones OT puras: `iniciar_ot`, `finalizar_ot`, autorización, cancelación, etc. |
| **`OperacionesService`** | Bandejas, deduplicación, publicación JSON; delega evaluación a operativas |

### 2.3 Compatibilidad

`ot_acciones_service.evaluar_crear_venta_desde_ot` (y similares) pueden delegar a `acciones_operativas_service` para no romper `asegurar_accion_ot_permitida()` en mutaciones existentes.

### 2.4 Evolución futura

Opción de renombrar fachada a `evaluador_operativo_service` en P5/P4.3 sin cambiar reglas de negocio.

---

## 3. Deduplicación — regla de dominio

### 3.1 Decisión (punto 6 del mandato)

La deduplicación es **regla de dominio**, ejecutada en **`OperacionesService`**, **no** filtro visual en frontend.

### 3.2 Invariante D1 — Partición exclusiva

| Clase | Condición | Bandeja A0 |
|-------|-----------|------------|
| **O1 — OT por cobrar** | OT `COMPLETADA` ∧ (¬venta_activa ∨ saldo > ε) | `ot_pendientes_cobro` |
| **O2 — OT lista entrega** | OT `COMPLETADA` ∧ venta_activa ∧ saldo ≤ ε | `ot_listas_entrega` |
| **V1 — Venta mostrador** | venta_activa ∧ saldo > ε ∧ `id_orden` IS NULL | `ventas_saldo_pendiente` |

**Exclusión:** venta con `id_orden` vinculada a OT en O1/O2 **nunca** aparece en V1.

**Definición `venta_activa`:** `estado != CANCELADA`.

### 3.3 Consumidores

| Capa | Rol |
|------|-----|
| `OperacionesService` | Ejecuta clasificador |
| A0 JSON | Expone bandejas particionadas |
| Caja Operativa P4.1 | Consume sin reclasificar |
| Frontend | **Prohibido** deduplicar |

---

## 4. Venta CANCELADA vinculada a OT

### 4.1 Decisión (punto 7 del mandato)

Venta **CANCELADA** vinculada a OT se trata como **venta no activa** (equivalente a sin venta).

| Efecto | Comportamiento |
|--------|----------------|
| Bandeja | OT en **O1** (`ot_pendientes_cobro`) |
| Acciones | `crear_venta_desde_ot` permitida si evaluador OK; `registrar_pago` bloqueada (`VENTA_INEXISTENTE` o sin venta) |
| Cancelación | Responsabilidad de `/ventas` (legacy/admin); P4.0 no auto-repara |

---

## 5. Alcance excluido de P4.0

### 5.1 Decisión (punto 8 del mandato)

P4.0 **no modifica**:

| Área | Motivo |
|------|--------|
| **Comisiones** | Reutilizar flujos existentes al liquidar venta |
| **`VentasService` core** | Mutaciones delegadas sin cambio de lógica contable |
| **`pagos.py` core** | Validación de turno permanece en POST; evaluador refleja reglas |
| **Alembic** | Sin cambios de esquema |

---

## 6. Bloqueo P4.1 UI

### 6.1 Decisión (punto 9 del mandato)

**P4.1 UI no puede iniciar** hasta que P4.0 quede:

1. Implementado según este ADR.
2. Validado con tests contractuales (deduplicación, turno, global nunca verde para pago, regresión Mi Taller).

Orden obligatorio: **P4.0 → validación → P4.1**.

---

## 7. Reglas `evaluar_registrar_pago`

| Condición | Resultado |
|-----------|-----------|
| Rol ∉ {ADMIN, CAJA} | `permitida=false`, `ROL_NO_PERMITIDO` |
| Sin turno ABIERTO del usuario | `permitida=false`, `TURNO_CERRADO` |
| Venta no existe | `permitida=false`, `VENTA_INEXISTENTE` |
| Venta CANCELADA | `permitida=false`, `VENTA_CANCELADA` |
| Saldo ≤ ε | `permitida=false`, `SALDO_CERO` |
| Pago excedería total | Coherente con `evaluar_pago_contra_total` |
| Todas OK | `permitida=true` |

**Criterio de aceptación P4.0:**

> No existe escenario reproducible donde A0 devuelva `registrar_pago.permitida=true` y `POST /api/pagos/` responda 400 por turno cerrado o saldo inválido.

---

## 8. Escenarios límite (referencia)

| Escenario | Comportamiento | Dueño regla |
|-----------|----------------|-------------|
| OT COMPLETADA + venta CANCELADA | O1; recrear venta | ADR §4 + operativas |
| OT COMPLETADA + pago parcial | O1; `registrar_pago` si turno OK | Clasificador + operativas |
| OT COMPLETADA + saldo cero | O2; `entregar_vehiculo` | Clasificador + operativas |
| OT ENTREGADA + saldo pendiente | Inconsistencia histórica; fuera bandejas O1/O2 | Legacy/reparación manual |
| Pago concurrente dos cajeros | Segundo POST rechazado si excede | `pagos.py` |
| Venta mostrador sin OT | V1 | Clasificador dominio |

---

## 9. Entregables P4.0 (implementación futura)

Cuando se autorice código:

1. `acciones_operativas_service.py`
2. Refactor `OperacionesService` (clasificador + deduplicación)
3. Política `acciones_globales` v2
4. `meta.version_contrato = "a0-v2"`
5. Schema `AccionOperativaOut`: `codigo_bloqueo`, `contexto` opcional
6. Tests contractuales listados en [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md) § P4.0

---

## 10. Consecuencias

### Positivas

- Cierra brecha `Backend == A0 == acciones[] == UI` para dominio financiero-operativo.
- P4.1 puede construirse sobre contrato confiable.
- P5 evita doble conteo en bandejas.

### Negativas / costo

- Bump de contrato requiere actualizar tests A0.
- Nuevo módulo evaluador (disciplina de imports para evitar circularidad).
- `PLAN_A0` original queda parcialmente superado por v2 (referencia histórica).

---

## 11. Control de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-06-10 | ADR aprobado — A0 v2, acciones_operativas_service, globales, deduplicación, exclusiones P4.0, bloqueo P4.1 |

---

## Aprobación

| Rol | Estado | Fecha |
|-----|--------|-------|
| Arquitectura / Negocio | ✅ Aprobado | 2026-06-10 |
| Implementación P4.0 | 🔲 Pendiente PRE-CHECK de código |
