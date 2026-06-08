# Lógica del Módulo de Citas

**Versión:** 2.0  
**Fecha de actualización:** 8 de junio de 2026  
**Estado:** Alineado con Corrección de Estados V2 (Fases 1–2 implementadas)

**Documentos relacionados:**

- [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md) — Arquitectura oficial de transiciones, historial y roles
- [PLAN_CITA_A_OT_V2.md](./PLAN_CITA_A_OT_V2.md) — Conversión cita → OT y elegibilidad por estado
- [QA_CITAS_FASE2_PRODUCCION.md](./QA_CITAS_FASE2_PRODUCCION.md) — Checklist de validación en producción

---

## 1. Flujo actual

### 1.1 Ciclo de vida de una cita

```
CREAR → CONFIRMADA → SI_ASISTIO  ⇄  correcciones (con motivo)
                  ↘ NO_ASISTIO   ⇄  correcciones (con motivo)
                  ↘ CANCELADA    →  CONFIRMADA (reactivar, ADMIN/CAJA)
```

- **CONFIRMADA**: Estado inicial al crear (el cliente ya confirmó al agendar).
- **SI_ASISTIO**: El cliente asistió y se atendió (puede vincularse a Orden de trabajo).
- **NO_ASISTIO**: El cliente no se presentó.
- **CANCELADA**: El cliente avisó que no podrá; se requiere motivo de cancelación.

Las flechas de **corrección** no borran el historial: cada cambio queda en `cita_estado_historial`. El primer cierre desde `CONFIRMADA` se conserva en `estado_origen_cierre` aunque el estado actual cambie después.

La matriz completa de transiciones y reglas por rol están en [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md).

### 1.2 Datos de una cita

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| id_cliente | Sí | Cliente de la cita |
| id_vehiculo | No | Vehículo (debe pertenecer al cliente) |
| fecha_hora | Sí | Fecha y hora de la cita |
| tipo | Sí | REVISION, MANTENIMIENTO, REPARACION, DIAGNOSTICO, OTRO |
| estado | Sí | CONFIRMADA, SI_ASISTIO, NO_ASISTIO, CANCELADA (solo vía PATCH `/estado`) |
| motivo | No | Motivo breve (ej. "Revisión de frenos") |
| motivo_cancelacion | Condicional | Obligatorio al cancelar (`estado = CANCELADA`) |
| notas | No | Notas adicionales |
| id_orden | No | Orden de trabajo vinculada (al convertir cita → OT) |
| estado_origen_cierre | No | Primer cierre al salir de CONFIRMADA; **inmutable** tras asignarse |

### 1.3 Flujo en la interfaz

1. **Listado**: Tabla con filtros (cliente, estado, fecha desde/hasta). Flags ligeros: `estado_editable`, `tiene_ot`, `bloqueo_financiero`.
2. **Nueva cita**: Modal con formulario → `POST /api/citas/`.
3. **Ver detalle**: Modal con datos enriquecidos desde `GET /api/citas/{id}` (incluye `estado_meta`). **No usar el listado** para decidir correcciones.
4. **Editar datos**: Modal de edición → `PUT /api/citas/{id}` (**sin** campo `estado`; el backend rechaza PUT con `estado`).
5. **Cambiar estado**: Siempre `PATCH /api/citas/{id}/estado` (ver §1.4).
6. **Eliminar**: Desde detalle o listado (requiere confirmación) → `DELETE /api/citas/{id}`.

**Acciones en detalle según estado** (sin OT vinculada):

| Estado | Botones principales |
|--------|---------------------|
| CONFIRMADA | Sí asistió · No asistió · Cancelar cita |
| SI_ASISTIO | Convertir a OT · Corregir estado |
| NO_ASISTIO | Corregir estado (destinos según `estado_meta`) |
| CANCELADA | Reactivar / Corregir estado (si `estado_meta.estado_editable`) |

**Con OT vinculada:** Ver OT; Corregir estado solo si el backend devuelve `transiciones_permitidas` (típicamente ADMIN).

### 1.4 Transiciones de estado — `PATCH /api/citas/{id}/estado`

Endpoint dedicado para **todas** las transiciones de estado. Implementado en Fase 1 backend; consumido por Fase 2 frontend.

**Request:**

```json
{
  "estado_nuevo": "SI_ASISTIO",
  "motivo_codigo": "ERROR_CAPTURA",
  "motivo_detalle": "Opcional; obligatorio ≥10 chars si motivo_codigo = OTRO",
  "motivo_cancelacion": "Obligatorio si estado_nuevo = CANCELADA"
}
```

**Response:** incluye `estado`, `estado_origen_cierre`, `ultimo_evento`, `estado_meta`.

**Marcación inicial** (`CONFIRMADA` → cierre):

- No requiere `motivo_codigo`.
- Cancelación requiere `motivo_cancelacion`.
- Botones directos en detalle: Sí asistió / No asistió / Cancelar cita.

**Corrección** (desde cualquier estado ya cerrado):

- Requiere `motivo_codigo` (catálogo en backend).
- Si `motivo_codigo = OTRO`, `motivo_detalle` mínimo 10 caracteres.
- UI: componente `ModalCorregirEstadoCita` — select de destino desde `estado_meta.transiciones_permitidas`, select de motivo, confirmación antes de enviar, advertencia si hay OT vinculada.

El frontend **no duplica** la matriz de transiciones; consume `estado_meta` del detalle enriquecido.

### 1.5 `estado_meta`

Objeto calculado por backend según rol, ventana 24h y presencia de OT. Disponible en `GET /api/citas/{id}` y en la respuesta del PATCH.

| Campo | Uso en UI |
|-------|-----------|
| `transiciones_permitidas` | Opciones del modal de corrección |
| `requiere_motivo` | Indica si alguna transición disponible es corrección |
| `estado_editable` | Mostrar u ocultar botón Corregir / Reactivar |
| `ventana_activa` | Si la cita está dentro de las 24h post `fecha_hora` |
| `tiene_ot` | Advertencia y restricción de corrección |
| `bloqueo_financiero` | Reservado Fase 4 (siempre `false` hoy) |

### 1.6 `cita_estado_historial`

Log append-only de cada transición. Tabla creada en migración `b8c9d0e1f2a3`.

| Origen | Cuándo se registra |
|--------|-------------------|
| `CREACION` | Alta de cita en CONFIRMADA |
| `MANUAL` | PATCH `/estado` por usuario |
| `CONVERTIR_OT` | Conversión cita → OT |
| `RECEPCION_RAPIDA` | Vinculación vía recepción rápida (si aplica) |

Las correcciones (no marcación inicial) generan además auditoría `CITA_ESTADO_CORREGIDO`.

**KPI operativo:** `citas.estado` (snapshot actual).  
**KPI calidad / auditoría:** `cita_estado_historial` + `estado_origen_cierre`. Ver [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md) §12.

### 1.7 `estado_origen_cierre`

- Se asigna **una sola vez** en la primera transición `CONFIRMADA` → estado cerrado (incluye conversión a OT que pasa a `SI_ASISTIO`).
- **No cambia** en correcciones posteriores.
- Permite saber cómo se cerró la cita originalmente aunque el estado actual haya sido corregido.

### 1.8 Roles y ventana de 24 horas

**Ventana:** desde `fecha_hora` de la cita hasta +24 horas (`ventana_correccion_activa`).

| Acción | ADMIN | CAJA / EMPLEADO | TECNICO |
|--------|-------|-----------------|---------|
| Marcación inicial (CONFIRMADA → cierre) | ✅ | ✅ | ✅ |
| Corrección dentro de 24h (sin OT) | ✅ | ✅ | ❌ |
| Corrección fuera de 24h (sin OT) | ✅ | ❌ | ❌ |
| Reactivar CANCELADA → CONFIRMADA | ✅ | ✅ | ❌ |
| Corrección con OT vinculada | ✅ | ❌ | ❌ |

Detalle completo: [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md) §4–5.

### 1.9 Integración con Cita → OT

Documento de referencia: [PLAN_CITA_A_OT_V2.md](./PLAN_CITA_A_OT_V2.md).

| Estado | ¿Convertir a OT? |
|--------|------------------|
| CONFIRMADA | ✅ |
| SI_ASISTIO | ✅ |
| NO_ASISTIO | ❌ (`409 ESTADO_NO_CONVERTIBLE`) |
| CANCELADA | ❌ |

Al convertir (`POST /api/citas/{id}/convertir-orden`):

1. Se crea OT y se asigna `cita.id_orden`.
2. La cita pasa a `SI_ASISTIO` si no lo estaba.
3. Se registra evento en `cita_estado_historial` con origen `CONVERTIR_OT`.
4. Puede fijarse `estado_origen_cierre` si es el primer cierre desde CONFIRMADA.

En UI: **Convertir a OT** solo en CONFIRMADA/SI_ASISTIO sin OT; **Ver OT** cuando `id_orden` está poblado.

---

## 2. Optimizaciones recomendadas

> **Nota (Jun 2026):** Vinculación con OT, transiciones gobernadas, historial y modal de corrección ya están implementados (P2 + Corrección V2). Las filas obsoletas se marcan como ✅ o ⏳.

### 2.1 UX (prioridad alta)

| Mejora | Descripción | Estado |
|--------|-------------|--------|
| **Botón Eliminar en la tabla** | Añadir "Eliminar" en la columna Acciones para borrar sin abrir el modal. | Parcial (existe en listado) |
| **Ordenar por fecha ascendente por defecto** | Mostrar primero las citas más próximas. | ⏳ Pendiente |
| **Vista calendario opcional** | Calendario semanal/mensual para planificación visual. | ⏳ Pendiente |

### 2.2 Lógica de negocio

| Mejora | Descripción | Estado |
|--------|-------------|--------|
| **Validar solapamiento** | Evitar citas a la misma hora para el mismo cliente/vehículo. | ⏳ Pendiente |
| **Vinculación con Orden** | Convertir cita a OT y actualizar `id_orden` + estado. | ✅ [PLAN_CITA_A_OT_V2.md](./PLAN_CITA_A_OT_V2.md) |
| **Corrección gobernada de estados** | PATCH dedicado, historial, roles, ventana 24h. | ✅ [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md) |
| **Recordatorios** | Notificaciones antes de la cita (email/SMS). | ⏳ Futuro |

### 2.3 Backend

| Mejora | Descripción | Estado |
|--------|-------------|--------|
| **Usar catálogos API** | Tipos/estados desde `GET /citas/catalogos/*`. | ✅ Parcial en frontend |
| **Optimizar count** | Paginación eficiente con muchas citas. | ⏳ Pendiente |
| **Reportes operativo vs calidad** | KPI dual desde estado vs historial. | ⏳ Fase 3 |
| **Bloqueo financiero con OT** | Bloquear PATCH si OT tiene venta/pagos. | ⏳ Fase 4 |

### 2.4 Simplificaciones

| Mejora | Descripción | Estado |
|--------|-------------|--------|
| **Ocultar botones según estado** | Acciones derivadas de `estado_meta` y reglas OT. | ✅ Fase 2 |
| **Confirmación antes de Eliminar** | `confirm()` en eliminación. | ✅ Implementado |

---

## 3. Resumen de prioridades

1. **Completado (2026):** Corrección de estados V2, Cita → OT P2, UI con PATCH y modal de corrección.
2. **Corto plazo:** QA producción post-deploy — [QA_CITAS_FASE2_PRODUCCION.md](./QA_CITAS_FASE2_PRODUCCION.md).
3. **Mediano plazo:** Reportes Fase 3; ordenar listado por próximas citas; validar solapamiento.
4. **Largo plazo:** Bloqueo financiero y desvinculación OT (Fase 4).

---

## Control de versiones del documento

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | (original) | Flujo base PUT estado, optimizaciones pendientes |
| 2.0 | 2026-06-08 | PATCH `/estado`, historial, `estado_origen_cierre`, `estado_meta`, modal corrección, OT, roles 24h, referencias V2 |
