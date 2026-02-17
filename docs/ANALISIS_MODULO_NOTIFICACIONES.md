# Análisis del Módulo de Notificaciones – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Página frontend que agrega alertas de caja, inventario y órdenes de compra. No existe router backend dedicado a "notificaciones"; es una vista de agregación.

---

## 1. Resumen ejecutivo

El módulo de Notificaciones es una **vista de agregación** en el frontend que consume tres fuentes:

| Fuente | Endpoint | Rol | Tipos |
|--------|----------|-----|-------|
| **Caja** | `GET /admin/alertas` | Solo ADMIN | DIFERENCIA_CIERRE, TURNO_LARGO |
| **Inventario** | `GET /inventario/alertas`, `GET /inventario/alertas/resumen` | Cualquiera | STOCK_BAJO, STOCK_CRITICO, SIN_STOCK, SIN_MOVIMIENTO, SOBRE_STOCK |
| **Órdenes de compra** | `GET /ordenes-compra/alertas` | ADMIN, CAJA | Pendientes de recibir, vencidas |

Las alertas se pueden marcar como resueltas mediante:
- `POST /admin/{id_alerta}/resolver` (caja)
- `POST /inventario/alertas/{id_alerta}/resolver` (inventario)

---

## 2. Errores detectados

### 2.1 Medios

#### E1. Parámetro `resueltas` vs `resuelta`

**Archivo:** `frontend/src/pages/Notificaciones.jsx`, línea 48

**Situación:** El frontend envía `resueltas: false` al endpoint `/admin/alertas`. El backend (`admin_alertas.py`) espera el parámetro `resueltas` (correcto). La comparación en el backend es `CajaAlerta.resuelta == resueltas`. Coherencia correcta.

**Nota:** No hay error; el nombre del parámetro es plural (resueltas = "las que están resueltas") y el filtro es "resueltas=false" = no resueltas. Correcto.

---

#### E2. Orden de rutas en admin_alertas

**Archivo:** `app/routers/admin_alertas.py`

**Situación:** Existen rutas `GET /alertas`, `GET /dashboard/resumen`, `GET /dashboard/ultimas` y `POST /{id_alerta}/resolver`. La ruta `/{id_alerta}/resolver` captura cualquier segmento. Una petición `POST /admin/alertas/resolver` (hipotética) no existe; `POST /admin/123/resolver` es correcta.

**Recomendación:** Las rutas literales (`/alertas`, `/dashboard/...`) están definidas antes que `/{id_alerta}/resolver`, por lo que el orden es correcto. No requiere cambios.

---

#### E3. Manejo de errores en carga

**Archivo:** `frontend/src/pages/Notificaciones.jsx`

**Situación:** Si `inventario` o `inventarioResumen` fallan (500, timeout), no se actualiza el estado ni se muestra mensaje de error. Solo se tratan 403 para caja y ordenesCompra.

**Impacto:** Ante un fallo en inventario, la página puede quedar vacía o desactualizada sin indicar al usuario que hubo un problema.

**Recomendación:** Gestionar errores genéricos: establecer `setError(...)` y/o `setAlertasInventario([])` cuando falle alguna petición crítica.

---

### 2.2 Menores

#### E4. Función `formatearFecha` local vs utilidad compartida

**Archivo:** `frontend/src/pages/Notificaciones.jsx`, líneas 23-29

**Situación:** Existe una función local `formatearFecha(s)` que usa `new Date(s).toLocaleString('es-MX', ...)`. El proyecto tiene `formatearFechaHora` en `utils/fechas.js` que ya contempla ISO y zonas horarias.

**Recomendación:** Usar `formatearFechaHora` de `utils/fechas` para consistencia y evitar duplicación.

---

#### E5. Dependencias del useEffect

**Archivo:** `frontend/src/pages/Notificaciones.jsx`, línea 76

**Situación:** `useEffect(() => { cargar() }, [user?.rol])` no incluye `cargar` en las dependencias. ESLint suele advertir sobre esto.

**Recomendación:** Establecer `cargar` como estable (ej. con `useCallback`) o añadirla a las dependencias si no genera bucles.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Validar tipo de alerta en admin/alertas

**Archivo:** `app/routers/admin_alertas.py`

**Situación:** Los filtros `tipo` y `nivel` aceptan cualquier string. Si se envía un valor no existente, el filtro no encuentra coincidencias (comportamiento silencioso).

**Propuesta:** Validar contra valores permitidos (p. ej. TIPO permitidos, NIVEL en CRITICO/WARNING/INFO) y devolver 400 si es inválido.

---

#### M2. Documentar estructura de respuesta en ordenes-compra/alertas

**Situación:** La respuesta tiene `ordenes_sin_recibir`, `ordenes_vencidas`, `items`. Falta documentación explícita en OpenAPI o en el código.

**Propuesta:** Añadir `response_model` o descripción en el docstring del endpoint.

---

### 3.2 Frontend

#### M3. Recarga periódica o manual

**Situación:** Las notificaciones solo se cargan al montar la página o al cambiar el rol. No hay recarga automática ni botón para actualizar.

**Propuesta:** Añadir botón "Actualizar" y/o recarga automática cada X minutos (opcional).

---

#### M4. Badge en menú lateral

**Situación:** El menú no muestra el número de alertas pendientes. El usuario debe entrar a Notificaciones para verlas.

**Propuesta:** Mostrar badge con el total de alertas en el ítem de Notificaciones del menú (requiere endpoint de resumen global o agregación en el frontend).

---

### 3.3 Arquitectura

#### M5. Endpoint unificado de notificaciones

**Situación:** El frontend hace 3–4 peticiones para mostrar la vista. Aumenta latencia y complejidad.

**Propuesta:** Crear un endpoint `GET /notificaciones` o `GET /notificaciones/resumen` que agregue caja, inventario y órdenes en una sola respuesta, según el rol del usuario.

---

## 4. Flujos verificados

| Flujo | Estado | Detalle |
|-------|--------|---------|
| Cargar alertas caja (ADMIN) | ✅ | Filtra resueltas=false |
| Cargar alertas inventario | ✅ | activas_solo=true, limit=50 |
| Cargar resumen inventario | ✅ | total_alertas, por tipo |
| Cargar ordenes compra (ADMIN/CAJA) | ✅ | limit=15 |
| Resolver alerta caja | ✅ | POST /admin/{id}/resolver |
| Resolver alerta inventario | ✅ | POST /inventario/alertas/{id}/resolver |
| Visibilidad por rol | ✅ | Caja solo ADMIN; OC solo ADMIN/CAJA |

---

## 5. Integración con otros módulos

| Módulo | Integración |
|--------|-------------|
| Admin | Alertas de caja (diferencias, turnos largos) |
| Inventario | Alertas de stock (bajo, crítico, sin stock, sin movimiento, sobre stock) |
| Órdenes de compra | Órdenes pendientes de recibir y vencidas |
| Caja | Generación de alertas en cierre de turno |

---

## 6. Checklist de implementación sugerido

**Prioridad media:**
- [x] E3: Manejo de errores en carga (inventario, resumen)
- [x] E4: Usar formatearFechaHora de utils/fechas en lugar de formatearFecha local

**Prioridad baja:**
- [x] E5: Ajustar dependencias del useEffect (useCallback)
- [x] M3: Botón "Actualizar" en Notificaciones
- [x] M4: Badge en menú lateral con total de alertas
- [x] M5: Endpoint unificado GET /notificaciones y GET /notificaciones/count

---

## 7. Archivos revisados

| Archivo | Rol principal |
|---------|---------------|
| `frontend/src/pages/Notificaciones.jsx` | Vista agregadora |
| `app/routers/admin_alertas.py` | Alertas de caja |
| `app/routers/inventario_reportes.py` | Alertas de inventario |
| `app/routers/ordenes_compra.py` | Alertas de órdenes de compra |
| `app/models/caja_alerta.py` | Modelo CajaAlerta |
| `app/models/alerta_inventario.py` | Modelo AlertaInventario |
| `app/routers/notificaciones.py` | Endpoint unificado (M5) |
