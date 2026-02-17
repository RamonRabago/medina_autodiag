# Análisis del Módulo Órdenes de Trabajo (actualizado)

**Fecha:** Febrero 2026

---

## 1. Resumen ejecutivo

El módulo de órdenes de trabajo es el núcleo del taller: integra clientes, vehículos, inventario, servicios, ventas y órdenes de compra. La lógica es sólida. Existe documentación previa (`ANALISIS_ORDENES_TRABAJO.md`) con varios puntos ya implementados. Este análisis actualiza el estado y añade hallazgos recientes.

---

## 2. Estructura del módulo

| Componente | Ubicación | Rol |
|------------|-----------|-----|
| Modelo | `orden_trabajo.py` | OrdenTrabajo, EstadoOrden, PrioridadOrden |
| Detalles | `detalle_orden.py` | DetalleOrdenTrabajo, DetalleRepuestoOrden |
| Schemas | `orden_trabajo_schema.py` | Create, Update, Response |
| CRUD | `ordenes_trabajo/crud.py` | Crear, listar, obtener, actualizar, eliminar |
| Acciones | `ordenes_trabajo/acciones.py` | Iniciar, finalizar, entregar, cancelar, autorizar |
| Detalles | `ordenes_trabajo/detalles.py` | Agregar/quitar servicios y repuestos |
| Cotización | `ordenes_trabajo/cotizacion.py` | PDF cotización y hoja técnico |
| Catálogos | `ordenes_trabajo/catalogos.py` | Estados, prioridades, dashboard |
| Helpers | `ordenes_trabajo/helpers.py` | generar_numero_orden (con FOR UPDATE) |
| Frontend | OrdenesTrabajo.jsx, NuevaOrdenTrabajo.jsx, DetalleOrdenTrabajo.jsx | UI |

---

## 3. Permisos por rol

| Acción | ADMIN | CAJA | TECNICO | EMPLEADO |
|--------|-------|------|---------|----------|
| Crear orden | ✓ | ✓ | ✗ | ✗ |
| Listar órdenes | ✓ Todas | ✓ Todas | ✓ Solo asignadas | ✓ Todas |
| Obtener detalle | ✓ | ✓ | ✓ Si asignada | ✓ |
| Actualizar | ✓ | ✓ | ✓ Si asignada | ✗ |
| Eliminar (CANCELADA) | ✓ | ✗ | ✗ | ✗ |
| Iniciar | ✓ | ✗ | ✓ Si asignada | ✗ |
| Finalizar | ✓ | ✗ | ✓ Si asignada | ✗ |
| Entregar | ✓ | ✓ | ✗ | ✗ |
| Cancelar | ✓ | ✓ | ✗ | ✗ |
| Autorizar | ✓ | ✓ | ✗ | ✗ |
| Marcar cotización enviada | ✓ | ✓ | ✓ Si asignada | ✗ |
| Agregar servicio/repuesto | ✓ | ✗ | ✓ | ✗ |
| Cotización PDF / Hoja técnico | ✓ | ✓ | ✓ Si asignada | ✓ |
| Dashboard estadísticas | ✓ | ✓ | ✗ | ✗ |

**Nota:** `listar_ordenes` y `obtener_orden` usan `get_current_user` (cualquier autenticado). EMPLEADO no está en `require_roles` de actualizar; si el frontend muestra edición a EMPLEADO, recibiría 403. Verificar si EMPLEADO debe poder editar.

---

## 4. Hallazgos y mejoras

### 4.1 Ya implementados (documentación previa)

- ✅ Cancelar orden: no devolver repuestos con `repuesto_id=None`
- ✅ Eliminar repuesto en EN_PROCESO: devuelve stock al inventario
- ✅ Agregar repuesto con `descripcion_libre`
- ✅ Actualizar orden: soporta repuestos con `descripcion_libre`
- ✅ Frontend: envía `descripcion_libre` en edición
- ✅ `generar_numero_orden`: usa `with_for_update()` para evitar colisiones

### 4.2 Comparación estado con Enum

**Situación:** En varios archivos se usa `orden.estado in ["ENTREGADA", "CANCELADA"]`. `EstadoOrden` hereda de `str`, por lo que la comparación funciona. Si se cambiara a `Enum` puro, fallaría.

**Recomendación:** Usar `orden.estado.value in [...]` o `orden.estado == EstadoOrden.ENTREGADA` para mayor claridad y robustez.

### 4.3 Inconsistencia datetime (local vs UTC)

**Situación:** Se mezcla `datetime.now()` y `datetime.utcnow()`:
- Modelo: `fecha_ingreso = default=datetime.now`
- Acciones: `fecha_finalizacion`, `fecha_cancelacion`, etc. usan `datetime.utcnow()`

**Impacto:** Posibles desfases en zonas horarias y auditorías.

**Recomendación:** Unificar en UTC (`datetime.utcnow()` o `datetime.now(timezone.utc)`).

### 4.4 Entregar/Autorizar: respuesta sin joinedload completo

**Situación:** `entregar_orden_trabajo` y `autorizar_orden_trabajo` devuelven `OrdenTrabajoResponse` pero cargan solo `detalles_servicio` y `detalles_repuesto` en el query. La serialización puede provocar N+1 si el schema accede a relaciones no cargadas.

**Recomendación:** Revisar si la respuesta incluye relaciones que requieran `joinedload` adicional.

### 4.5 EMPLEADO: ¿puede actualizar órdenes?

**Situación:** `actualizar_orden_trabajo` permite ADMIN, CAJA, TECNICO. EMPLEADO no está incluido. Si en recepción hay usuarios EMPLEADO que deben editar órdenes, recibirían 403.

**Recomendación:** Incluir EMPLEADO si el flujo lo requiere, o documentar que solo ADMIN/CAJA/TECNICO editan.

### 4.6 Ruta duplicada marcar-cotizacion-enviada

**Situación:** Existen dos rutas:
- `POST /ordenes-trabajo/{orden_id}/marcar-cotizacion-enviada` (acciones)
- `POST /ordenes-trabajo/marcar-cotizacion-enviada?orden_id=X` (catalogos)

El frontend `DetalleOrdenTrabajo.jsx` usa la segunda (`/marcar-cotizacion-enviada` con `params: { orden_id }`). Ambas funcionan.

**Recomendación:** Mantener la ruta REST `/{orden_id}/marcar-cotizacion-enviada` como principal; la de catalogos puede ser legacy. Valorar deprecar la de catalogos para simplificar.

### 4.7 NuevaOrdenTrabajo: TECNICO redirigido

**Situación:** Si TECNICO intenta acceder a `/ordenes-trabajo/nueva`, se redirige a `/ordenes-trabajo`. Coherente con permisos (solo ADMIN/CAJA crean).

### 4.8 OrdenesTrabajo: debounce en búsqueda

**Situación:** Ya implementado: `useEffect` con debounce de 400 ms antes de `setBuscarDebounced`. Buena práctica.

### 4.9 Finalizar orden: sin confirmación

**Situación:** A diferencia de cancelar (que tiene modal), finalizar se ejecuta sin confirmación. Es una decisión de UX.

**Recomendación:** Valorar añadir confirmación si la acción tiene impacto fuerte (ej. "¿Marcar orden como completada?").

### 4.10 Crear orden: validaciones obligatorias

**Situación:** Backend exige `diagnostico_inicial` y `observaciones_cliente` no vacíos. Al menos un servicio o repuesto. Validación de stock para repuestos (salvo `cliente_proporciono_refacciones`).

---

## 5. Flujos verificados

| Flujo | Estado |
|-------|--------|
| Crear orden (servicios + repuestos) | ✓ |
| Crear con repuesto descripcion_libre | ✓ |
| Crear con cliente_proporciono_refacciones | ✓ No descuenta stock |
| Listar (filtros, paginación, TECNICO solo asignadas) | ✓ |
| Obtener detalle (con venta, saldo, usuario_creo) | ✓ |
| Actualizar (PENDIENTE, servicios/repuestos) | ✓ |
| Iniciar (descuenta inventario) | ✓ |
| Finalizar | ✓ |
| Entregar (requiere venta pagada) | ✓ |
| Cancelar (devolver repuestos opcional) | ✓ |
| Cancelar con venta vinculada | ✓ Desvincula y ajusta venta |
| Eliminar orden CANCELADA (sin venta) | ✓ |
| Cotización PDF | ✓ |
| Hoja técnico PDF | ✓ |
| Generar número orden (concurrencia) | ✓ FOR UPDATE |

---

## 6. Integración con otros módulos

| Módulo | Relación |
|--------|----------|
| Clientes | OrdenTrabajo.cliente_id |
| Vehículos | OrdenTrabajo.vehiculo_id |
| Servicios | DetalleOrdenTrabajo.servicio_id |
| Repuestos | DetalleRepuestoOrden.repuesto_id |
| Inventario | Movimientos SALIDA al iniciar, ENTRADA al cancelar/devolver |
| Ventas | Venta.id_orden, crear desde orden, vincular/desvincular |
| Órdenes de compra | OrdenCompra.id_orden_trabajo |
| Citas | Cita.id_orden (opcional) |

---

## 7. Mejoras priorizadas

| Prioridad | Acción |
|-----------|--------|
| Baja | Unificar fechas a UTC |
| Baja | Usar EstadoOrden.X en comparaciones en lugar de strings |
| Baja | Incluir EMPLEADO en actualizar si el flujo lo requiere |
| Baja | Confirmación al finalizar orden (UX) |
| Baja | Deprecar ruta marcar-cotizacion-enviada de catalogos |

---

## 8. Conclusión

El módulo está maduro y bien integrado. Los problemas críticos documentados anteriormente están resueltos. Las mejoras restantes son menores (fechas, comparaciones, permisos EMPLEADO, UX). No se detectan errores que afecten la integridad de datos o el flujo principal.
