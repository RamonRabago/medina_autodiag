# Análisis del Módulo Vehículos

**Fecha:** Febrero 2026

---

## 1. Resumen ejecutivo

El módulo de vehículos está bien integrado con clientes, órdenes de trabajo, ventas, citas y órdenes de compra. La lógica es coherente. Se identifican: (1) bug en eliminación por falta de verificación de ventas/citas, (2) permisos CAJA excluidos en endpoints usados por Ventas/Citas, (3) mejoras de UX (loading en refetch, feedback, debounce).

---

## 2. Estructura del módulo

| Componente | Ubicación | Rol |
|------------|-----------|-----|
| Modelo | `app/models/vehiculo.py` | Vehiculo (marca, modelo, anio, color, motor, vin, id_cliente) |
| Modelo auditoría | `app/models/registro_eliminacion_vehiculo.py` | RegistroEliminacionVehiculo |
| Schemas | `app/schemas/vehiculo.py` | VehiculoCreate, VehiculoUpdate, VehiculoOut |
| Router | `app/routers/vehiculos.py` | CRUD, historial, vehiculos_por_cliente |
| Exportación | `app/routers/exportaciones.py` | GET /exportaciones/vehiculos |
| Frontend | `frontend/src/pages/Vehiculos.jsx` | Lista, crear/editar, historial, eliminar |

---

## 3. Permisos por endpoint

| Endpoint | Roles permitidos |
|----------|------------------|
| GET / (listar) | ADMIN, EMPLEADO, TECNICO, CAJA |
| POST / (crear con cliente) | ADMIN, EMPLEADO, TECNICO |
| POST /sin-cliente | ADMIN, CAJA, EMPLEADO, TECNICO |
| GET /cliente/{id} | ADMIN, EMPLEADO, TECNICO |
| GET /{id} | ADMIN, EMPLEADO, TECNICO |
| GET /{id}/historial | ADMIN, EMPLEADO, TECNICO |
| PUT /{id} | ADMIN, EMPLEADO, TECNICO |
| DELETE /{id} | ADMIN |

**Problemas:**
- **Ventas.jsx** llama a `GET /vehiculos/cliente/{id}` al seleccionar cliente; **CAJA** no está en ese endpoint → 403.
- **Citas.jsx** usa el mismo endpoint y `POST /vehiculos/`. Si CAJA gestiona citas, recibe 403.
- **NuevaOrdenTrabajo.jsx** usa `POST /vehiculos/` para agregar vehículo; CAJA no puede crear (coherente si solo técnicos crean OT).

**Recomendación:** Incluir CAJA en `vehiculos_por_cliente`, `obtener_vehiculo` y `crear_vehiculo` (con cliente) si Ventas/Citas requieren esos flujos para CAJA.

---

## 4. Errores y bugs detectados

### 4.1 Bug: Eliminación no verifica ventas ni citas

**Ubicación:** `app/routers/vehiculos.py` líneas 322-333

**Problema:** Antes de eliminar, se comprueban solo **OrdenTrabajo** y **OrdenCompra**. No se comprueban:
- **Venta** (Venta.id_vehiculo)
- **Cita** (Cita.id_vehiculo)

Si un vehículo tiene ventas o citas asociadas, `db.delete(vehiculo)` fallará por FK (RESTRICT) y se obtendrá un error 500 en lugar de un 400 con mensaje claro.

**Corrección:** Añadir:
```python
n_ventas = db.query(Venta).filter(Venta.id_vehiculo == id_vehiculo).count()
if n_ventas > 0:
    raise HTTPException(400, f"No se puede eliminar: hay {n_ventas} venta(s) asociada(s).")
n_citas = db.query(Cita).filter(Cita.id_vehiculo == id_vehiculo).count()
if n_citas > 0:
    raise HTTPException(400, f"No se puede eliminar: hay {n_citas} cita(s) asociada(s).")
```

### 4.2 Modal de eliminación sin órdenes de compra

**Situación:** El modal de eliminar muestra órdenes de trabajo y permite cancelar/eliminar. No muestra **órdenes de compra**. Si hay OC asociadas, el backend bloquea con mensaje genérico.

**Recomendación:** Incluir en `historial_vehiculo` (o en el flujo de eliminación) las órdenes de compra y mostrarlas en el modal para que el usuario sepa qué debe resolver.

---

## 5. Mejoras recomendadas

### 5.1 Loading en refetch

**Situación:** Al cambiar `pagina`, `buscar` o `filtroCliente`, `cargar()` no pone `loading = true`. La tabla conserva datos viejos hasta que termina la nueva petición.

**Recomendación:** Añadir `setLoading(true)` al inicio de `cargar()` (como en Clientes corregido).

### 5.2 Feedback al guardar

**Situación:** Tras crear/editar vehículo correctamente, no hay `showSuccess`.

**Recomendación:** Añadir `showSuccess('Vehículo guardado')` tras guardar.

### 5.3 Editar: permitir cambiar cliente

**Situación:** En edición, el cliente se muestra como solo lectura. El backend `VehiculoUpdate` acepta `id_cliente`.

**Recomendación:** Opcionalmente permitir cambiar cliente al editar (útil para reasignar vehículo vendido/transferido).

### 5.4 Debounce en búsqueda

Igual que en Clientes: debounce de 300–400 ms en el input de búsqueda para reducir requests.

### 5.5 Validación de VIN

El VIN (numero_serie) no tiene validación de formato. Opcional: validar longitud (17 caracteres estándar) o estructura básica.

---

## 6. Flujos verificados

| Flujo | Estado |
|-------|--------|
| Crear vehículo (con cliente) | ✓ Valida cliente existe |
| Crear vehículo sin cliente | ✓ |
| Listar con filtros (cliente, buscar, paginación) | ✓ |
| Historial (órdenes, ventas) | ✓ |
| Editar vehículo | ✓ Mapeo numero_serie ↔ vin |
| Eliminar (sin deps) | ✓ Registro en auditoría |
| Eliminar con órdenes | ✓ Bloqueado con mensaje |
| Eliminar con órdenes de compra | ✓ Bloqueado |
| Vehículos por cliente | ✓ Usado en Ventas, Citas |
| Color display | ✓ Motor como fallback si color vacío |
| Exportar Excel | ✓ Incluye cliente |

---

## 7. Integración con otros módulos

| Módulo | Relación |
|--------|----------|
| Clientes | Vehiculo.id_cliente, CASCADE si se borra cliente |
| Órdenes de trabajo | OrdenTrabajo.vehiculo_id |
| Ventas | Venta.id_vehiculo (nullable) |
| Citas | Cita.id_vehiculo (nullable) |
| Órdenes de compra | OrdenCompra.id_vehiculo (legacy) |
| Catálogo vehículos | Independiente (catalogo_vehiculos para OC) |

---

## 8. Mejoras priorizadas

| Prioridad | Acción |
|-----------|--------|
| **Alta** | Verificar ventas y citas antes de eliminar vehículo |
| Media | Incluir CAJA en vehiculos_por_cliente si Ventas lo usa |
| Media | `setLoading(true)` al inicio de cargar() |
| Media | showSuccess al guardar vehículo |
| Baja | Mostrar órdenes de compra en modal de eliminación |
| Baja | Debounce en búsqueda |
| Baja | Permitir cambiar cliente al editar (opcional) |

---

## 9. Conclusión

El módulo es sólido. Los puntos principales son el bug de eliminación (ventas/citas) y los permisos de CAJA en endpoints usados desde Ventas/Citas. No hay errores críticos de cálculo; el historial y la relación con órdenes/ventas son correctos.
