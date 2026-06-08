# Plan Cita → OT V2 — Análisis y diseño

**Versión:** 2.1  
**Fecha:** Junio 2026  
**Estado:** **P2 implementado** ✅  
**Prioridad roadmap:** P2 — cerrado  
**Relacionado:** [PLAN_RECEPCION_RAPIDA_V2.md](./PLAN_RECEPCION_RAPIDA_V2.md) · [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md) · [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

## Resumen ejecutivo

Hoy **Citas** y **Órdenes de trabajo** capturan los mismos datos de forma independiente: cliente, vehículo y motivo. Cuando el cliente llega al taller, recepción vuelve a tipear todo en OT (wizard o recepción rápida).

**Objetivo P2:** usar **Recepción Rápida** como único punto de captura al convertir una cita en OT, precargando datos desde la cita y vinculando `cita.id_orden` ↔ `orden.id`.

**Hallazgo crítico:** el campo `citas.id_orden` **existe en BD** pero **ningún endpoint lo escribe** hoy. La conversión no está implementada en backend ni frontend.

**Recomendación:** flujo UI `Cita → /operaciones/recepcion?cita_id=X` (precarga) + al crear OT actualizar cita (`id_orden`, `estado=SI_ASISTIO`). Alternativa atómica: `POST /api/citas/{id}/convertir-orden`.

**Complejidad estimada:** Media-baja (3–5 días: 1.5 backend, 2 frontend, 0.5 QA).

---

## Fase 1 — Modelo y datos actuales

### 1.1 Modelo `Cita` (`app/models/cita.py`)

| Campo | Tipo | Obligatorio | Uso en conversión |
|-------|------|-------------|-------------------|
| `id_cita` | PK | Sí | Trazabilidad, query param P2 |
| `id_cliente` | FK clientes | Sí | → `RecepcionRapidaCreate.cliente_id` |
| `id_vehiculo` | FK vehiculos | No | → `vehiculo_id` (validar pertenencia) |
| `fecha_hora` | DateTime | Sí | Contexto UI; no va a OT directamente |
| `tipo` | Enum TipoCita | Sí | Opcional en notas OT / prioridad inferida |
| `estado` | Enum EstadoCita | Sí | Tras conversión → `SI_ASISTIO` |
| `motivo` | String(300) | No | → campo `motivo` recepción (≥10 chars) |
| `notas` | Text | No | Concatenar a motivo si corto |
| `motivo_cancelacion` | Text | No | No aplica en conversión |
| **`id_orden`** | FK ordenes_trabajo | No | **Vínculo cita ↔ OT (nunca se escribe hoy)** |
| `creado_en` | DateTime | Auto | Auditoría |

**Estados cita:** `CONFIRMADA`, `SI_ASISTIO`, `NO_ASISTIO`, `CANCELADA`  
**Tipos:** `REVISION`, `MANTENIMIENTO`, `REPARACION`, `DIAGNOSTICO`, `OTRO`

### 1.2 Relación con OT

```text
Cita.id_orden  →  ordenes_trabajo.id  (nullable, FK)
OrdenTrabajo   ←  backref "citas"     (1:N teórico; operación espera 1:1)
```

- Eliminar cita con `id_orden` → **400** (`citas.py` DELETE).
- Detalle cita expone `orden_vinculada` si existe (`GET /citas/{id}`).
- **No hay** `PUT` que asigne `id_orden` ni endpoint de conversión.

### 1.3 Schema API (`app/schemas/cita.py`)

- `CitaOut.id_orden` expuesto en respuestas enriquecidas.
- `CitaUpdate` **no incluye** `id_orden` (conversión requiere endpoint dedicado o ampliar schema con reglas estrictas).

---

## Fase 2 — Endpoints Citas actuales

| Método | Ruta | Roles | Relevante P2 |
|--------|------|-------|--------------|
| GET | `/api/citas/` | ADMIN, EMPLEADO, TECNICO, CAJA | Listado; filtro estado CONFIRMADA |
| GET | `/api/citas/{id}` | Idem | **Precarga recepción** (cliente, vehículo, motivo, id_orden) |
| GET | `/api/citas/dashboard/proximas` | Idem | Panel dashboard / futuro CitasHoy |
| GET | `/api/citas/alertas` | Idem | Citas vencidas sin seguimiento |
| POST | `/api/citas/` | Idem | Crear cita (sin OT) |
| PUT | `/api/citas/{id}` | Idem | Cambiar estado (SI_ASISTIO manual hoy, sin OT) |
| DELETE | `/api/citas/{id}` | Idem | Bloqueado si `id_orden` |

**Gap P2:** falta `POST /api/citas/{id}/convertir-orden` o lógica post-`recepcion-rapida` que actualice la cita.

---

## Fase 3 — Recepción rápida (base P1)

### 3.1 Contrato ya preparado

**Frontend** (`RecepcionRapidaForm`):

```javascript
initialValues={{
  cliente_id, cliente, vehiculo_id,
  motivo,   // desde cita.motivo + notas
  cita_id,
}}
```

**URL:** `/operaciones/recepcion?cita_id={id}` (hook en `RecepcionRapida.jsx`; precarga de cita **pendiente**).

**Backend** (`POST /api/ordenes-trabajo/recepcion-rapida`):

- Acepta `cita_id` opcional en body.
- **No persiste** FK en OT (no hay `cita_id` en modelo OT).
- Registra `cita_id_pendiente` en auditoría solamente.

### 3.2 Flujo objetivo P2

```mermaid
sequenceDiagram
  participant U as Recepcionista
  participant C as Citas / Dashboard
  participant R as /operaciones/recepcion
  participant API as Backend

  C->>R: navigate ?cita_id=42
  R->>API: GET /citas/42
  API-->>R: cliente, vehículo, motivo, id_orden
  alt Ya tiene id_orden
    R->>U: Redirect /ordenes-trabajo/{id}
  else Sin OT
    R->>R: Precarga formulario
    U->>R: Confirmar / ajustar
    R->>API: POST /recepcion-rapida + cita_id
    API->>API: Crear OT PENDIENTE
    API->>API: PUT cita id_orden + SI_ASISTIO
    R->>U: Redirect detalle OT
  end
```

---

## Fase 4 — Datos reutilizables y mapeo

| Origen (Cita) | Destino (Recepción / OT) | Regla |
|---------------|--------------------------|-------|
| `id_cliente` | `cliente_id` | Obligatorio |
| `id_vehiculo` | `vehiculo_id` | Obligatorio para recepción; si null → forzar alta/selección |
| `motivo` | `motivo` (UI) | Si &lt; 10 chars, enriquecer con `notas` o texto tipo cita |
| `notas` | parte de `motivo` | `trim(motivo + " — " + notas)` si hace falta longitud |
| `tipo` | (opcional) | Mostrar en UI; no mapear a BD OT en P2 |
| `fecha_hora` | (informativo) | Banner "Cita programada: …" |
| `id_cita` | `cita_id` en POST | Trazabilidad + update cita post-crear |

| Post-crear OT | Actualizar Cita |
|---------------|-----------------|
| `orden.id` | `cita.id_orden = orden.id` |
| — | `cita.estado = SI_ASISTIO` |

**Motivo duplicado eliminado:** una sola captura en recepción; cita solo se lee.

---

## Fase 5 — Duplicación actual (problema)

### 5.1 Frontend Citas (`Citas.jsx`)

| Elemento | Estado | Problema |
|----------|--------|----------|
| Autocomplete cliente | Manual (500 clientes) | Duplica lógica vs `ClienteAutocompleteConAltaRapida` |
| Modal vehículo | Inline duplicado | No usa `ModalVehiculoRapido` |
| Motivo / notas | Campos propios | Re-captura en OT |
| Conversión OT | Solo muestra `orden_vinculada` | Sin botón "Recibir en taller" |
| Marcar asistencia | PUT estado | No crea OT |

### 5.2 Flujo operativo hoy

1. Crear cita (cliente, vehículo, motivo).
2. Cliente llega → marcar `SI_ASISTIO` (opcional).
3. Ir a OT nueva o recepción → **re-ingresar** cliente, vehículo, motivo.

**Meta P2:** paso 3 → un clic desde cita a recepción precargada.

---

## Fase 6 — Opciones de implementación (decisión pendiente)

### Opción A — Orquestación frontend (recomendada fase 1)

1. `GET /citas/{id}` → precargar `RecepcionRapidaForm`.
2. `POST /recepcion-rapida` con `cita_id`.
3. Nuevo **`PATCH /api/citas/{id}/vincular-orden`** `{ id_orden }` con validaciones:
   - Rol recepción (ADMIN, CAJA, EMPLEADO).
   - Cita en `CONFIRMADA` o vencida CONFIRMADA.
   - `id_orden` vacío.
   - OT mismo cliente (y vehículo si ambos tienen FK).

**Pros:** reutiliza endpoint P1; cambios acotados.  
**Contras:** dos requests; riesgo de OT huérfana si falla paso 3.

### Opción B — Endpoint atómico (recomendada producción)

`POST /api/citas/{id}/convertir-orden`

Body opcional: `{ motivo?, prioridad?, tecnico_id?, kilometraje? }` — override de precarga.

Transacción:

1. Validar cita elegible.
2. Crear OT vía lógica compartida con `crear_recepcion_rapida`.
3. `cita.id_orden = ot.id`, `cita.estado = SI_ASISTIO`.
4. Auditoría `CITA_CONVERTIDA_OT`.

**Pros:** consistencia, idempotencia posible.  
**Contras:** más backend; UI puede seguir usando formulario de confirmación antes del POST.

### Opción C — Solo query param sin vínculo BD

No recomendado: deja `id_orden` null y pierde trazabilidad.

---

## Fase 7 — Reglas de negocio propuestas

| Regla | Descripción |
|-------|-------------|
| Elegibilidad | Cita `CONFIRMADA` o `SI_ASISTIO` (incl. vencida CONFIRMADA) y `id_orden IS NULL` |
| Ya convertida | Si `id_orden` → redirect detalle OT, no duplicar |
| Cancelada | No convertir; HTTP 400 |
| **NO_ASISTIO** | **No convertir; HTTP 409 `ESTADO_NO_CONVERTIBLE`. Conservar estado para reportes no-show** |
| Vehículo obligatorio | Si cita sin vehículo → recepción exige selección/alta antes de POST |
| Motivo mínimo 10 | Combinar motivo+notas+tipo en precarga |
| Roles conversión | Mismos que recepción: ADMIN, CAJA, EMPLEADO |
| TECNICO | Puede ver cita; conversión vía recepción prohibida (403) |

---

## Fase 8 — Puntos de entrada UI (P2)

| Origen | Acción |
|--------|--------|
| `Citas.jsx` — fila / detalle | Botón "Recibir en taller" → `/operaciones/recepcion?cita_id=` |
| `Dashboard.jsx` — citas próximas | Mismo enlace por cita |
| Walk-in sin cita | `/operaciones/recepcion` sin param (sin cambio) |

**No eliminar** módulo Citas; solo dejar de duplicar captura hacia OT.

---

## Fase 9 — Pruebas planificadas (P2)

| # | Escenario |
|---|-----------|
| 1 | Cita CONFIRMADA con cliente+vehículo+motivo → OT + vínculo |
| 2 | Cita sin vehículo → precarga cliente → alta vehículo → OT |
| 3 | Cita ya con id_orden → redirect detalle, no duplicar |
| 4 | Cita CANCELADA → botón deshabilitado / 400 |
| 5 | Motivo corto en cita → precarga enriquecida ≥10 |
| 6 | Rol TECNICO → sin conversión |
| 7 | Idempotencia: doble clic no crea dos OT |

---

## Fase 10 — Estimación y dependencias

| Tarea | Días |
|-------|------|
| Backend vínculo cita↔OT (A o B) | 1–1.5 |
| Precarga `?cita_id=` en RecepcionRapida | 0.5–1 |
| Botones Citas + Dashboard | 0.5–1 |
| Tests E2E | 0.5–1 |
| QA + docs | 0.5 |

**Dependencias:** P1 Recepción Rápida **cerrado** ✅

**Deuda relacionada (no P2):** adopción `ClienteAutocompleteConAltaRapida` / `VehiculoSelectorConAltaRapida` dentro de `Citas.jsx`.

---

## Control de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | Jun 2026 | Análisis inicial P2 — sin implementación |

**Recomendación implementada:** **Opción B** — `POST /api/citas/{id}/convertir-orden` (atómico). Recepción rápida con `?cita_id=` cubre citas sin vehículo.

**Complejidad real:** Media-baja (implementado en P2).

---

## Implementación P2 (Jun 2026)

### Decisión final: Opción B

Endpoint atómico `POST /api/citas/{id}/convertir-orden` crea OT PENDIENTE y vincula `cita.id_orden` + `estado=SI_ASISTIO` en una transacción.

**Caso sin vehículo:** HTTP 409 con `accion: COMPLETAR_RECEPCION` → redirect a `/operaciones/recepcion?cita_id={id}`. Al crear OT vía `POST /recepcion-rapida` con `cita_id`, el vínculo ocurre en la misma transacción.

### Archivos clave

| Área | Archivo |
|------|---------|
| Servicio compartido | `app/services/recepcion_ot_service.py` |
| Endpoint convertir | `app/routers/citas.py` → `POST /{id}/convertir-orden` |
| Recepción + vínculo cita | `app/routers/ordenes_trabajo/crud.py` |
| Tests | `tests/test_cita_convertir_orden.py` |
| Frontend Citas | `frontend/src/pages/Citas.jsx` |
| Precarga recepción | `frontend/src/pages/operaciones/RecepcionRapida.jsx` |
| Utilidades | `frontend/src/utils/citaOt.js` |

### Reglas de negocio implementadas

| Regla | Comportamiento |
|-------|----------------|
| Roles convertir | ADMIN, CAJA, EMPLEADO |
| TECNICO | 403 |
| Cita cancelada | 400 |
| **Cita NO_ASISTIO** | **409 `ESTADO_NO_CONVERTIBLE`; no cambia estado ni crea OT** |
| Estados convertibles | Solo `CONFIRMADA` o `SI_ASISTIO` |
| Cita CONFIRMADA → OT | `estado` pasa a `SI_ASISTIO` al vincular |
| Cita SI_ASISTIO → OT | `estado` se mantiene `SI_ASISTIO` |
| Cita con id_orden | 409 + `VER_ORDEN` |
| Sin vehículo | 409 + `COMPLETAR_RECEPCION` |
| OT estado | PENDIENTE |
| Motivo | `motivo` + `notas` → `diagnostico_inicial` + `observaciones_cliente` |
| POST estándar OT | Sin cambios |
| Walk-in recepción | Sin cambios |

### Reportes de asistencia (base futura)

`GET /api/citas/reportes/asistencia` — totales por estado, `porcentaje_no_asistencia` (no_asistidas / asistidas+no_asistidas) y `clientes_mayor_inasistencia`. Filtros opcionales `fecha_desde`, `fecha_hasta`.

### Auditoría

- `CITA_CONVERTIDA_OT` — al usar convertir-orden
- `CITA_VINCULADA_OT` — al vincular desde recepción rápida con `cita_id`
- `RECEPCION_RAPIDA` — trazabilidad con `via: convertir_cita` o `recepcion_rapida`

### Pruebas backend

`tests/test_cita_convertir_orden.py`:

1. Convertir cita válida → OT PENDIENTE
2. Cita queda con `id_orden` y `SI_ASISTIO`
3. Motivo + notas copiados
4. Cita cancelada → 400
5. **Cita NO_ASISTIO → 409 `ESTADO_NO_CONVERTIBLE` (estado conservado)**
6. **Cita SI_ASISTIO previa → OT + mantiene SI_ASISTIO**
7. Cita ya convertida → 409 `VER_ORDEN`
8. Sin vehículo → 409 `COMPLETAR_RECEPCION`
9. TECNICO → 403
10. Recepción rápida con `cita_id` vincula cita
11. **Recepción con cita NO_ASISTIO → 409**
12. **GET reportes/asistencia → totales y no-show**
13. POST estándar OT sin regresión
14. Walk-in recepción sin `cita_id`

### Riesgos / deuda

| Riesgo | Mitigación |
|--------|------------|
| Doble conversión | Validación `id_orden` en backend + UI "Ver OT" |
| Motivo corto | `construir_motivo_desde_cita` garantiza ≥10 chars |
| Citas.jsx sin componentes V2 | Deuda: migrar a `ClienteAutocompleteConAltaRapida` (no bloqueante P2) |

### QA manual pendiente (Railway)

1. Cita completa → Convertir → detalle OT
2. Cita sin vehículo → recepción precargada → OT vinculada
3. Cita convertida → Ver OT
4. Cita cancelada → sin botón convertir
5. **Cita NO_ASISTIO → sin botón convertir; opciones Reactivar / Cambiar a Sí asistió**
6. Roles CAJA / EMPLEADO / TECNICO

**Próximo hito:** P3 Mi Taller (no iniciar hasta cerrar QA P2).

---

## Control de versiones (histórico)

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | Jun 2026 | Análisis inicial P2 — sin implementación |
| 2.0 | Jun 2026 | **P2 implementado** — Opción B, frontend, tests, docs |
| 2.1 | Jun 2026 | **NO_ASISTIO no convertible**; reporte asistencia; UI reactivar |

**Estado:** P2 completo en código; QA manual en Railway recomendado antes de tag.
