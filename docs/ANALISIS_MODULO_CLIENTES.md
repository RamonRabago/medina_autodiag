# Análisis del Módulo Clientes

**Fecha:** Febrero 2026

---

## 1. Resumen ejecutivo

El módulo de clientes está bien estructurado con CRUD completo, historial consolidado, eliminación con auditoría y flujo para gestionar órdenes antes de eliminar. Se identifican mejoras de UX (loading, debounce), permisos y posibles errores menores.

---

## 2. Estructura del módulo

| Componente | Ubicación | Rol |
|------------|-----------|-----|
| Modelo | `app/models/cliente.py` | Cliente (nombre, teléfono, email, direccion, rfc) |
| Modelo auditoría | `app/models/registro_eliminacion_cliente.py` | RegistroEliminacionCliente |
| Schemas | `app/schemas/cliente.py` | ClienteCreate, ClienteUpdate, ClienteOut |
| Router | `app/routers/clientes.py` | CRUD, historial, eliminación |
| Exportación | `app/routers/exportaciones.py` | GET /exportaciones/clientes |
| Frontend | `frontend/src/pages/Clientes.jsx` | Lista, modales crear/editar, historial, eliminar, agregar vehículo |

---

## 3. Permisos por endpoint

| Endpoint | Roles permitidos |
|----------|------------------|
| POST / (crear) | ADMIN, EMPLEADO, TECNICO |
| GET / (listar) | ADMIN, EMPLEADO, TECNICO, CAJA |
| GET /{id}/historial | ADMIN, EMPLEADO, TECNICO |
| GET /{id} | ADMIN, EMPLEADO, TECNICO |
| PUT /{id} | ADMIN, EMPLEADO, TECNICO |
| DELETE /{id} | ADMIN |
| Exportar clientes | ADMIN, EMPLEADO, TECNICO, CAJA |

**Inconsistencia:** CAJA puede listar y exportar clientes, pero no crear ni editar. Si CAJA registra ventas manuales y necesita dar de alta clientes al momento (ej. venta a cliente nuevo), recibirá 403.

**Recomendación:** Incluir CAJA en crear_cliente y actualizar_cliente si el flujo de caja requiere registrar clientes. Alternativa: mantener restricción y que CAJA pida a otro rol que cree el cliente.

---

## 4. Errores y bugs detectados

### 4.1 Bug: Loading se desactiva antes de que cargue la lista

**Ubicación:** `frontend/src/pages/Clientes.jsx` líneas 82-85

**Problema:** `useEffect(() => { setLoading(false) }, [])` se ejecuta al montar y pone `loading = false` de inmediato. La función `cargar()` no modifica `loading`. Resultado: el spinner desaparece casi al instante y la tabla queda vacía hasta que la API responde.

**Corrección:** Mover `setLoading(false)` al `.then()` y `.catch()` de `cargar()`, o usar un estado derivado de si hay datos pendientes.

### 4.2 Sin validación de clientes duplicados

**Problema:** No se valida nombre + teléfono (o email) para evitar duplicados. Se pueden crear varios registros del mismo cliente.

**Recomendación (opcional):** Añadir validación en backend o aviso en frontend al guardar (ej. "Ya existe un cliente con este teléfono").

---

## 5. Mejoras recomendadas

### 5.1 Debounce en búsqueda

**Situación:** Cada tecla en el input dispara `setBuscar` → `useEffect` → `cargar()`. Con muchos clientes, genera muchas requests.

**Recomendación:** Debounce de 300-400 ms antes de ejecutar la búsqueda.

### 5.2 Feedback al crear/editar

**Situación:** Tras guardar cliente correctamente, no hay `showSuccess`. Solo se cierra el modal y se refresca la lista.

**Recomendación:** Añadir `showSuccess('Cliente guardado')` (o similar) en `handleSubmit`.

### 5.3 Feedback al agregar vehículo

**Situación:** Tras agregar vehículo desde el modal, no hay toast de confirmación.

**Recomendación:** Añadir `showSuccess('Vehículo agregado')`.

### 5.4 Eliminación: reasignar ventas y vehículos

**Situación:** El backend bloquea la eliminación si hay ventas o vehículos. El mensaje indica "reasigna ventas y vehículos primero". En Ventas no hay flujo explícito para cambiar cliente; en Vehículos sí se puede cambiar `id_cliente`.

**Recomendación:** Documentar el flujo (ej. desde Vehículos cambiar cliente a "Cliente varios" o similar). Valorar permitir eliminar cliente dejando ventas/vehículos con `id_cliente = NULL` si el modelo lo soporta (actualmente Venta.id_cliente nullable=True, Vehiculo tiene ondelete=CASCADE en cliente).

### 5.5 Permisos: incluir CAJA en crear/editar

Si el negocio requiere que caja registre clientes al momento de una venta, añadir CAJA a `crear_cliente` y `actualizar_cliente`.

---

## 6. Flujos verificados

| Flujo | Estado |
|-------|--------|
| Crear cliente | ✓ Validaciones nombre, teléfono, email, RFC |
| Editar cliente | ✓ |
| Listar con búsqueda/paginación | ✓ |
| Ver historial (ventas, órdenes, citas, vehículos) | ✓ |
| Agregar vehículo desde Clientes | ✓ Mapeo numero_serie → vin |
| Eliminar cliente (sin dependencias) | ✓ Registro en RegistroEliminacionCliente |
| Eliminar con órdenes | ✓ Debe cancelar primero, luego eliminar canceladas |
| Eliminar con ventas/vehículos | ✓ Bloqueado; mensaje orientativo |
| Exportar a Excel | ✓ Incluye ventas y vehículos por cliente |
| Orden de rutas FastAPI | ✓ GET /{id}/historial antes de GET /{id} |

---

## 7. Integración con otros módulos

| Módulo | Relación |
|--------|----------|
| Vehículos | Cliente tiene vehículos; Vehiculo.id_cliente FK con CASCADE |
| Órdenes de trabajo | OrdenTrabajo.cliente_id |
| Ventas | Venta.id_cliente (nullable) |
| Citas | Cita.id_cliente |
| Dashboard | Cuenta total clientes |

---

## 8. Mejoras priorizadas

| Prioridad | Acción |
|-----------|--------|
| **Alta** | Corregir bug de loading (setLoading en .then/.catch de cargar) |
| Media | Añadir showSuccess al guardar cliente y al agregar vehículo |
| Media | Debounce en input de búsqueda |
| Baja | Incluir CAJA en crear/editar si el flujo lo requiere |
| Baja | Validación de duplicados (opcional) |

---

## 9. Conclusión

El módulo es funcional y coherente con el resto del sistema. Los puntos críticos son el bug de loading y las mejoras de feedback. No se detectan errores de integridad de datos o cálculos.
