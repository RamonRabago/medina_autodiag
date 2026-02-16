# Análisis del Módulo de Órdenes de Trabajo

Análisis detallado de posibles problemas, incoherencias y mejoras en el módulo de órdenes de trabajo (backend + frontend).

---

## Resumen ejecutivo

| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| Crítica   | 3        | Bugs que pueden causar pérdida de datos o errores en producción |
| Alta      | 4        | Inconsistencias de lógica de negocio o riesgo de corrupción |
| Media     | 5        | Problemas de UX, validaciones faltantes, posibles race conditions |
| Baja      | 4        | Mejoras de consistencia, documentación, mantenibilidad |

---

## 1. Problemas críticos

### 1.1 Cancelar orden: devolver repuestos con `repuesto_id` null

**Archivo:** `app/routers/ordenes_trabajo/acciones.py` líneas 227-248

Al cancelar una orden en `EN_PROCESO` con `devolver_repuestos=True`, el loop itera sobre `orden.detalles_repuesto` sin filtrar los que tienen `repuesto_id=None` (repuestos con `descripcion_libre`). `InventarioService.registrar_movimiento` exige `id_repuesto` y lanzará error al intentar devolver un repuesto sin ID.

**Solución:** Añadir `if not detalle_repuesto.repuesto_id: continue` antes del `registrar_movimiento`.

---

### 1.2 Eliminar repuesto de orden en EN_PROCESO: no se devuelve stock

**Archivo:** `app/routers/ordenes_trabajo/detalles.py` líneas 211-250

Cuando se agrega un repuesto a una orden en `EN_PROCESO`, se registra una SALIDA de inventario (líneas 180-197). Al eliminarlo con `eliminar_repuesto_de_orden`, solo se borra el detalle y se recalcula el total; no se genera movimiento de ENTRADA para devolver el stock.

**Consecuencia:** Pérdida de inventario al quitar repuestos de órdenes en proceso.

**Solución:** Si `estado == EN_PROCESO` y `not cliente_proporciono_refacciones` y `detalle.repuesto_id`, registrar un movimiento ENTRADA antes de borrar el detalle.

---

### 1.3 Agregar repuesto a orden: no soporta `descripcion_libre`

**Archivo:** `app/routers/ordenes_trabajo/detalles.py` líneas 127-208

El endpoint `agregar_repuesto_a_orden` asume que siempre hay `repuesto_id`:

```python
repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == repuesto_data.repuesto_id).first()
```

Pero `AgregarRepuestoRequest` extiende `DetalleRepuestoCreate`, que permite `repuesto_id=None` cuando hay `descripcion_libre`. Si se envía `descripcion_libre` sin `repuesto_id`, el query devuelve `None` y se responde 404.

**Solución:** Permitir repuestos sin inventario (solo `descripcion_libre`) y crear `DetalleRepuestoOrden` con `repuesto_id=None`, similar al flujo de crear orden en `crud.py`.

---

## 2. Problemas de alta severidad

### 2.1 Actualizar orden (PUT): repuestos con `descripcion_libre`

**Archivo:** `app/routers/ordenes_trabajo/crud.py` líneas 359-380

Al actualizar repuestos en estado PENDIENTE, el código asume que todos tienen `repuesto_id`:

```python
rid = r.get("repuesto_id") if isinstance(r, dict) else r.repuesto_id
repuesto = db.query(Repuesto).filter(Repuesto.id_repuesto == rid).first()
if not repuesto:
    raise HTTPException(404, ...)
```

Con `rid=None` (repuesto solo con `descripcion_libre`), el resultado es siempre 404.

**Solución:** Tratar por separado:
- Si `rid`: repuesto de catálogo (comprobar stock, crear con `repuesto_id`).
- Si `descripcion_libre` sin `rid`: crear `DetalleRepuestoOrden` con `repuesto_id=None`.

---

### 2.2 Frontend edición: no mapea `descripcion_libre` en repuestos

**Archivo:** `frontend/src/pages/OrdenesTrabajo.jsx` línea 213

```javascript
repuestosMap = (datos.detalles_repuesto || []).map((d) => ({
  repuesto_id: d.repuesto_id,
  cantidad: d.cantidad || 1,
  precio_unitario: d.precio_unitario ?? null
}))
```

No se envía `descripcion_libre`. Al editar una orden con repuestos “libres”, el backend recibe `repuesto_id: null` sin descripción y falla.

**Solución:** Incluir `descripcion_libre` en el payload y en el modal de edición.

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

### 3.5 Frontend: opción duplicada en selector de estado

**Archivo:** `frontend/src/pages/OrdenesTrabajo.jsx` líneas 357-358

```jsx
<option value="COTIZADA">Cotizada</option>
<option value="COTIZADA">Cotizada</option>
```

Hay una opción duplicada en el filtro de estado.

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

1. **Inventario e integridad**
   - Resolver el bug de no devolver stock al eliminar repuestos en órdenes en proceso.
   - Añadir la comprobación para no devolver repuestos con `repuesto_id=None` al cancelar.

2. **Repuestos con `descripcion_libre`**
   - Soportar `descripcion_libre` en agregar repuesto y en la actualización de orden.
   - Ajustar el frontend para enviar y mostrar `descripcion_libre` en edición.

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

| Archivo | Líneas aprox. | Estado |
|---------|---------------|--------|
| `app/models/orden_trabajo.py` | 107 | OK |
| `app/models/detalle_orden.py` | 81 | OK |
| `app/schemas/orden_trabajo_schema.py` | 194 | OK (pequeño ajuste en validador) |
| `app/routers/ordenes_trabajo/crud.py` | 415 | Ver 1.1, 2.1 |
| `app/routers/ordenes_trabajo/acciones.py` | 340 | Ver 1.1, 2.3, 3.2 |
| `app/routers/ordenes_trabajo/detalles.py` | 254 | Ver 1.2, 1.3 |
| `app/routers/ordenes_trabajo/cotizacion.py` | 468 | Ver 2.4 |
| `app/routers/ordenes_trabajo/catalogos.py` | 89 | Ver 3.3 |
| `app/routers/ordenes_trabajo/helpers.py` | 23 | Ver 3.1 |
| `frontend/src/pages/OrdenesTrabajo.jsx` | 638 | Ver 2.2, 3.5 |
| `frontend/src/pages/DetalleOrdenTrabajo.jsx` | 387 | OK |
| `frontend/src/pages/NuevaOrdenTrabajo.jsx` | 758 | Soporta descripcion_libre en creación |
