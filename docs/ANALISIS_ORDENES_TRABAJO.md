# Análisis del Módulo de Órdenes de Trabajo

Análisis detallado de posibles problemas, incoherencias y mejoras en el módulo de órdenes de trabajo (backend + frontend).

**Última actualización:** Febrero 2026

---

## Resumen ejecutivo

| Severidad | Cantidad | Implementados | Pendientes |
|-----------|----------|---------------|------------|
| Crítica   | 3        | 3 ✅           | 0          |
| Alta      | 4        | 2 ✅           | 2          |
| Media     | 5        | 1 ✅           | 4          |
| Baja      | 4        | 0             | 4          |

---

## 1. Problemas críticos

### 1.1 Cancelar orden: devolver repuestos con `repuesto_id` null ✅ IMPLEMENTADO

**Archivo:** `app/routers/ordenes_trabajo/acciones.py` líneas 249-252

Al cancelar una orden en `EN_PROCESO` con `devolver_repuestos=True`, el loop itera sobre `orden.detalles_repuesto` sin filtrar los que tienen `repuesto_id=None` (repuestos con `descripcion_libre`).

**Implementado:** `if not detalle_repuesto.repuesto_id: continue` antes del `registrar_movimiento`.

---

### 1.2 Eliminar repuesto de orden en EN_PROCESO: no se devuelve stock ✅ IMPLEMENTADO

**Archivo:** `app/routers/ordenes_trabajo/detalles.py` líneas 265-282

Cuando se agrega un repuesto a una orden en `EN_PROCESO`, se registra una SALIDA de inventario. Al eliminarlo con `eliminar_repuesto_de_orden`, antes se genera movimiento ENTRADA para devolver el stock.

**Implementado:** Si `estado == EN_PROCESO` y `not cliente_proporciono_refacciones` y `detalle.repuesto_id`, se registra ENTRADA antes de borrar el detalle.

---

### 1.3 Agregar repuesto a orden: no soporta `descripcion_libre` ✅ IMPLEMENTADO

**Archivo:** `app/routers/ordenes_trabajo/detalles.py` líneas 146-196

El endpoint `agregar_repuesto_a_orden` ahora soporta ambos casos: con `repuesto_id` (catálogo) o con `descripcion_libre` (repuesto libre sin inventario).

**Implementado:** Si `repuesto_id`: busca en catálogo y valida stock. Si solo `descripcion_libre`: crea `DetalleRepuestoOrden` con `repuesto_id=None`.

---

## 2. Problemas de alta severidad

### 2.1 Actualizar orden (PUT): repuestos con `descripcion_libre` ✅ IMPLEMENTADO

**Archivo:** `app/routers/ordenes_trabajo/crud.py` líneas 516-551

Al actualizar repuestos en estado PENDIENTE, el código trata ambos casos.

**Implementado:** Si `rid`: repuesto de catálogo (comprobar stock). Si `descripcion_libre` sin `rid`: crear `DetalleRepuestoOrden` con `repuesto_id=None`.

---

### 2.2 Frontend edición: no mapea `descripcion_libre` en repuestos ✅ IMPLEMENTADO


**Implementado:** Se envía `descripcion_libre`. El modal permite repuestos “libres” y envía el payload correcto.


---

### 2.3 Inconsistencia `datetime.now()` vs `datetime.utcnow()`

**Archivos varios**

- `acciones.py`: `fecha_finalizacion = datetime.now()`, `fecha_cancelacion = datetime.utcnow()`, `fecha_autorizacion = datetime.utcnow()`
- `orden_trabajo.py`: `fecha_ingreso = default=datetime.now`
- `crud.py` `_isoformat_utc`: se asume UTC añadiendo `Z`

Se mezcla hora local y UTC. Para auditorías y comparaciones entre zonas, es preferible usar UTC de forma uniforme (p. ej. `datetime.utcnow()` o `datetime.now(timezone.utc)`).

---

### 2.4 Cotización PDF: rol "EMPLEADO"

**Archivo:** `app/routers/ordenes_trabajo/cotizacion.py` línea 242

```python
current_user=Depends(require_roles("ADMIN", "EMPLEADO", "CAJA", "TECNICO"))
```

En el modelo `Usuario`, el rol es `Enum("ADMIN", "EMPLEADO", "TECNICO", "CAJA")`. Si no existen usuarios con rol `EMPLEADO`, esa comprobación no aporta nada. Confirmar si “EMPLEADO” sigue en uso; si no, quitar del `require_roles`.

---

## 3. Problemas de severidad media

### 3.1 Posible colisión de números de orden (race condition)

**Archivo:** `app/routers/ordenes_trabajo/helpers.py`

`generar_numero_orden` consulta la última orden y genera la siguiente sin bloqueo. Dos peticiones simultáneas podrían obtener el mismo “último” número y producir duplicados.

**Solución:** Usar `SELECT ... FOR UPDATE` o un bloqueo explícito, o una secuencia/constraint única con retry.

---

### 3.2 Entregar/Autorizar: falta `joinedload` para OrdenTrabajoResponse

**Archivos:** `app/routers/ordenes_trabajo/acciones.py`  
- `entregar_orden_trabajo` (línea 174)  
- `autorizar_orden_trabajo` (línea 312)

Ambos devuelven `orden` con `response_model=OrdenTrabajoResponse`, pero no usan `joinedload` para `detalles_servicio` ni `detalles_repuesto`. La serialización puede provocar N+1 o errores de lazy loading, como el ya corregido en `finalizar`.

**Solución:** Reutilizar el mismo patrón de `joinedload` usado en `finalizar_orden_trabajo`.

---

### 3.3 Dashboard: posible incompatibilidad con Enum en SQLAlchemy

**Archivo:** `app/routers/ordenes_trabajo/catalogos.py` líneas 77-80

```python
OrdenTrabajo.prioridad == "URGENTE",
OrdenTrabajo.estado.in_(["PENDIENTE", "EN_PROCESO"])
```

Si la columna usa `SQLEnum`, algunas versiones de SQLAlchemy pueden exigir valores del enum. Si hay problemas, usar `EstadoOrden.URGENTE`, `EstadoOrden.PENDIENTE`, etc.

---

### 3.4 DetalleOrdenTrabajo: validación de `cantidad` en schema

**Archivo:** `app/schemas/orden_trabajo_schema.py`

`DetalleRepuestoBase` usa `cantidad: Decimal = Field(..., ge=0.001)`. Cantidad 0 falla la validación. Si el modelo permite `cantidad=0`, considerar hacerlo explícito (p. ej. permitir 0 o rechazarlo con un mensaje claro).

---

### 3.5 Frontend: opción duplicada en selector de estado ✅ REVISADO

**Archivo:** `frontend/src/pages/OrdenesTrabajo.jsx`

Revisado: El selector de estado no tiene opciones duplicadas. Cada estado aparece una sola vez. (Si existió el bug, está corregido.)

---

## 4. Problemas de severidad baja

### 4.1 OrdenTrabajoUpdate: validador de `prioridad` sin soporte de enum

**Archivo:** `app/schemas/orden_trabajo_schema.py` líneas 124-131

`OrdenTrabajoUpdate` valida `prioridad` contra strings. Si el cliente envía un enum, podría fallar. En `OrdenTrabajoBase` ya se normaliza con `v.value if hasattr(v, "value") else str(v)`; conviene aplicar lo mismo aquí.

---

### 4.2 Obtención de orden: formato distinto a OrdenTrabajoResponse

**Archivo:** `app/routers/ordenes_trabajo/crud.py` `obtener_orden_trabajo`

Devuelve un diccionario construido a mano en lugar de usar `OrdenTrabajoResponse`. Es funcional pero implica dos formatos de respuesta distintos y más mantenimiento.

---

### 4.3 Iniciar orden: sin carga de detalles de servicio

**Archivo:** `app/routers/ordenes_trabajo/acciones.py` `iniciar_orden_trabajo`

Solo se hace `joinedload(OrdenTrabajo.detalles_repuesto)`; no se cargan `detalles_servicio`. Como la respuesta usa `OrdenTrabajoResponse`, puede haber lazy loading al serializar.

---

### 4.4 Falta confirmación al finalizar orden

**Archivo:** `frontend/src/pages/OrdenesTrabajo.jsx` y `DetalleOrdenTrabajo.jsx`

`finalizarOrden` no pide confirmación, a diferencia de cancelar. Es una decisión de UX: si es una acción irreversible o con impacto fuerte, conviene un modal de confirmación.

---

## 5. Recomendaciones generales

1. **Inventario e integridad** ✅
   - ✅ Devolver stock al eliminar repuestos en órdenes en proceso.
   - ✅ No devolver repuestos con `repuesto_id=None` al cancelar.

2. **Repuestos con `descripcion_libre`** ✅
   - ✅ Soportar `descripcion_libre` en agregar repuesto y en la actualización de orden.
   - ✅ Frontend envía y muestra `descripcion_libre` en edición.

3. **Unificación de fechas**
   - Usar siempre UTC (o un criterio explícito) para fechas de auditoría y eventos.

4. **Respuestas de la API**
   - Usar `OrdenTrabajoResponse` en todos los endpoints que devuelven una orden.
   - Aplicar `joinedload` donde haga falta para evitar lazy loading en serialización.

5. **Pruebas**
   - Casos de repuestos con `descripcion_libre`.
   - Cancelar con `devolver_repuestos` cuando hay repuestos libres.
   - Eliminar repuesto en orden EN_PROCESO y verificar stock.
   - Colisión de números de orden bajo carga.

---

## 6. Archivos revisados

| Archivo | Estado |
|---------|--------|
| `app/models/orden_trabajo.py` | OK |
| `app/models/detalle_orden.py` | OK |
| `app/schemas/orden_trabajo_schema.py` | OK |
| `app/routers/ordenes_trabajo/crud.py` | ✅ 2.1 implementado. Ver 2.3, 4.2 |
| `app/routers/ordenes_trabajo/acciones.py` | ✅ 1.1 implementado. Ver 2.3, 3.2, 4.3 |
| `app/routers/ordenes_trabajo/detalles.py` | ✅ 1.2, 1.3 implementados |
| `app/routers/ordenes_trabajo/cotizacion.py` | Ver 2.4 |
| `app/routers/ordenes_trabajo/catalogos.py` | Ver 3.3 |
| `app/routers/ordenes_trabajo/helpers.py` | Ver 3.1 |
| `frontend/src/pages/OrdenesTrabajo.jsx` | ✅ 2.2, 3.5 implementados/revisados |
| `frontend/src/pages/DetalleOrdenTrabajo.jsx` | OK |
| `frontend/src/pages/NuevaOrdenTrabajo.jsx` | Soporta descripcion_libre en creación |
