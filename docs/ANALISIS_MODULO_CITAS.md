# Análisis del Módulo de Citas – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelo, router, schemas, integración con clientes, vehículos, órdenes y frontend.

---

## 1. Resumen ejecutivo

El módulo de citas permite agendar y gestionar citas del taller:
- Estados: CONFIRMADA, SI_ASISTIO, NO_ASISTIO, CANCELADA
- Tipos: REVISION, MANTENIMIENTO, REPARACION, DIAGNOSTICO, OTRO
- Vinculación opcional con orden de trabajo (`id_orden`)

Se han identificado **errores** y **mejoras**.

---

## 2. Errores detectados

### 2.1 Medios

#### E1. Fechas como string en filtros

**Archivo:** `app/routers/citas.py` — `listar_citas`, líneas 79-81

```python
if fecha_desde:
    query = query.filter(func.date(Cita.fecha_hora) >= fecha_desde)
if fecha_hasta:
    query = query.filter(func.date(Cita.fecha_hora) <= fecha_hasta)
```

**Impacto:** Se compara `date` con string. Puede fallar en algunos motores SQL. Conviene parsear explícitamente.

**Recomendación:**
```python
if fecha_desde:
    try:
        fd = datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date()
        query = query.filter(func.date(Cita.fecha_hora) >= fd)
    except (ValueError, TypeError):
        pass
```

---

#### E2. Estado inválido en actualización

**Archivo:** `app/routers/citas.py` — `actualizar_cita`

**Situación:** Al recibir `estado` inválido (ej. "INVALIDO"), se usa `getattr(EstadoCita, val, cita.estado)` y se mantiene el estado anterior sin avisar al usuario.

**Impacto:** El usuario puede enviar un valor incorrecto y no recibir feedback.

**Recomendación:** Validar contra los valores de `EstadoCita` y devolver 400 si es inválido.

---

#### E3. Orden de rutas – catalogos

**Archivo:** `app/routers/citas.py`

**Situación:** Las rutas `GET /catalogos/estados` y `GET /catalogos/tipos` están definidas después de `GET /{id_cita}`. Como `/{id_cita}` solo captura un segmento, `/catalogos/estados` (dos segmentos) no coincide con esa ruta. El orden actual funciona pero es frágil.

**Recomendación:** Colocar las rutas de catálogos antes de las rutas con parámetros para mayor claridad.

---

### 2.2 Menores

#### E4. Eliminar cita vinculada a orden

**Archivo:** `app/routers/citas.py` — `eliminar_cita`

**Situación:** Se permite eliminar físicamente una cita que tiene `id_orden` asignado (orden de trabajo derivada de la cita).

**Impacto:** Se pierde la trazabilidad cita → orden. La orden sigue existiendo.

**Recomendación:** Opcionalmente bloquear la eliminación o advertir cuando hay orden vinculada.

---

#### E5. Validación de tipo inválido

**Archivo:** `app/routers/citas.py` — `actualizar_cita`

**Situación:** Si se envía `tipo` inválido, `getattr(TipoCita, v.upper(), cita.tipo)` conserva el tipo actual sin avisar.

**Recomendación:** Validar y devolver 400 si el tipo no es válido.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Validar solapamiento de citas

**Propuesta:** Opcionalmente evitar citas a la misma hora para el mismo cliente o vehículo, según reglas de negocio.

---

#### M2. Soft delete en vez de hard delete

**Situación:** `eliminar_cita` hace borrado físico. No queda historial para auditoría.

**Propuesta:** Valorar soft delete (ej. `eliminada=True`) similar a repuestos o proveedores.

---

#### M3. Vinculación automática con orden

**Situación:** Al crear una orden desde una cita con estado SI_ASISTIO, el frontend/backend podría actualizar `Cita.id_orden` automáticamente. La vinculación ya existe en el modelo pero no está documentada en el flujo.

**Propuesta:** Documentar el flujo y, si aplica, automatizar la actualización de `id_orden`.

---

### 3.2 Frontend

#### M4. Normalizar error de validación

**Archivo:** `frontend/src/pages/Citas.jsx` — `handleSubmit`

**Situación:** Se usa `normalizeDetail(err.response?.data?.detail)`. La función `normalizeDetail` en `utils/toast.js` ya maneja arrays de errores Pydantic (extrae `msg` y une con saltos de línea). No requiere cambio.

---

#### M5. Orden por defecto “próximas primero”

**Situación:** El parámetro `orden` por defecto es "asc" (próximas primero). Está bien documentado en `LOGICA_CITAS.md`.

**Propuesta:** Confirmar que el frontend envía `orden=asc` cuando corresponde.

---

### 3.3 Documentación

#### M6. Documentar flujo cita → orden

**Propuesta:** Añadir a `LOGICA_CITAS.md` el flujo para crear orden desde cita y cómo se actualiza `id_orden`.

---

## 4. Flujos verificados

| Flujo | Estado | Detalle |
|-------|--------|---------|
| Crear cita | ✅ | Valida cliente, vehículo del cliente, fecha futura |
| Listar citas | ✅ | Filtros y paginación correctos |
| Obtener por ID | ✅ | Incluye orden vinculada |
| Actualizar cita | ✅ | Valida fecha futura, motivo al cancelar |
| Cambiar estado | ✅ | SI_ASISTIO, NO_ASISTIO, CANCELADA (con motivo) |
| Eliminar cita | ✅ | Hard delete (sin soft delete) |
| Dashboard próximas | ✅ | Solo CONFIRMADA y fecha futura |
| Catálogos | ✅ | Estados y tipos vía API |

---

## 5. Integración con otros módulos

| Módulo | Integración |
|--------|-------------|
| Clientes | Cita requiere `id_cliente`; historial en cliente |
| Vehículos | `id_vehiculo` opcional; debe pertenecer al cliente; vehículos valida citas al eliminar |
| Órdenes de trabajo | `id_orden` opcional; backref en OrdenTrabajo |
| Dashboard | Citas próximas para ADMIN y CAJA |

---

## 6. Checklist de implementación sugerido

**Prioridad media:**
- [x] E1: Parsear fechas en filtros de listar_citas
- [x] E2: Validar estado al actualizar; devolver 400 si es inválido
- [x] E5: Validar tipo al actualizar; devolver 400 si es inválido

**Prioridad baja:**
- [x] E3: Reordenar rutas (catalogos antes de parámetros)
- [x] E4: Bloquear eliminación de cita con orden vinculada (HTTP 400)
- [ ] M1: Validar solapamiento de citas
- [ ] M2: Evaluar soft delete

---

## 7. Archivos revisados

| Archivo | Rol principal |
|---------|----------------|
| `app/models/cita.py` | Modelo Cita |
| `app/routers/citas.py` | Router |
| `app/schemas/cita.py` | Schemas Pydantic |
| `frontend/src/pages/Citas.jsx` | Vista principal |
| `docs/LOGICA_CITAS.md` | Documentación de lógica |
| `app/routers/vehiculos.py` | Verificación de citas al eliminar vehículo |
| `app/routers/clientes.py` | Historial de citas por cliente |
