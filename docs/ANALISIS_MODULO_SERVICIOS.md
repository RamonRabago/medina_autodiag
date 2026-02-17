# Análisis del Módulo Servicios

**Fecha:** Febrero 2026

---

## 1. Resumen ejecutivo

El módulo de servicios gestiona el catálogo de servicios del taller (código, nombre, categoría, precio, tiempo, etc.). Está bien estructurado con categorías, soft delete y validaciones. Se identifican un posible bug en exportaciones (tipo de `categoria`), mejoras de UX y recomendaciones menores.

---

## 2. Estructura del módulo

| Componente | Ubicación | Rol |
|------------|-----------|-----|
| Modelo | `app/models/servicio.py` | Servicio (codigo, nombre, categoria, precio_base, tiempo, activo) |
| Categorías | `app/models/categoria_servicio.py` | CategoriaServicio |
| Schemas | `app/schemas/servicio_schema.py` | Create, Update, Response |
| Router | `app/routers/servicios.py` | CRUD, activar, categorias/listar (legacy) |
| Categorías | `app/routers/categorias_servicios.py` | CRUD categorías |
| Exportación | `app/routers/exportaciones.py` | GET /exportaciones/servicios |
| Frontend | `frontend/src/pages/Servicios.jsx` | Lista, crear/editar, desactivar, reactivar |

---

## 3. Permisos por endpoint

| Endpoint | ADMIN | Otros |
|----------|-------|-------|
| Crear servicio | ✓ | ✗ |
| Listar servicios | ✓ | ✓ (autenticado) |
| Obtener servicio | ✓ | ✓ |
| Actualizar servicio | ✓ | ✗ |
| Eliminar (desactivar) | ✓ | ✗ |
| Activar servicio | ✓ | ✗ |
| Categorías CRUD | ✓ | Listar/obtener: todos |
| Exportar | ✓ | ✓ (ADMIN, EMPLEADO, TECNICO, CAJA) |

---

## 4. Hallazgos y posibles errores

### 4.1 Exportar servicios: tipo de `categoria`

**Ubicación:** `app/routers/exportaciones.py` líneas 285, 298-299

**Problema:** El parámetro `categoria` se declara como `str | None`. Se usa en `Servicio.id_categoria == categoria`. Si el frontend envía `categoria=5` (número), la query string lo convierte a `"5"`. La comparación `id_categoria == "5"` puede fallar según el driver o no filtrar correctamente.

**Corrección:** Usar `categoria: int | None = Query(None)` y, si se recibe string, convertir con `int(categoria)` antes de filtrar.

### 4.2 Servicios desactivados en órdenes existentes

**Situación:** Al desactivar un servicio, los `DetalleOrdenTrabajo` que ya lo usan siguen existiendo. El servicio inactivo no aparece en selectores de nuevas órdenes, pero las órdenes históricas lo referencian.

**Impacto:** Correcto para integridad histórica. No es un error.

### 4.3 Sin validación de código duplicado (case-insensitive)

**Situación:** El código es único con validación exacta. "SRV-001" y "srv-001" se consideran distintos.

**Recomendación:** Valorar normalizar a mayúsculas al guardar (`.strip().upper()`) para evitar duplicados por mayúsculas/minúsculas.

### 4.4 Categorías: eliminación física

**Situación:** Eliminar categoría hace `db.delete(cat)` (borrado físico). Se bloquea si hay servicios asociados. No hay desactivación (soft delete) de categorías.

**Recomendación:** Valorar endpoint de desactivación (`activo=False`) además de la eliminación física, para mantener historial.

### 4.5 Nuevo servicio sin categorías

**Situación:** Si no hay categorías, el formulario muestra "Seleccionar..." y `id_categoria` puede quedar vacío o 0. El backend rechaza con "Categoría no válida".

**Recomendación:** Mostrar mensaje cuando `categorias.length === 0`: "Crea una categoría en Configuración primero" y deshabilitar el botón "Nuevo servicio".

---

## 5. Mejoras de UX

### 5.1 Sin feedback al guardar

Tras crear o actualizar un servicio correctamente no hay `showSuccess`.

**Recomendación:** Añadir `showSuccess('Servicio guardado')` en `handleSubmit`.

### 5.2 Sin feedback al desactivar/reactivar

Tras desactivar o reactivar no hay toast de confirmación.

**Recomendación:** Añadir `showSuccess` en `confirmarEliminar` y `activarServicio`.

### 5.3 Orden de rutas

En `servicios.py`, la ruta `GET /categorias/listar` está después de `GET /{servicio_id}`. La ruta `/categorias/listar` tiene dos segmentos y no colisiona con `/{servicio_id}` (un solo segmento). No hay conflicto.

---

## 6. Flujos verificados

| Flujo | Estado |
|-------|--------|
| Crear servicio | ✓ Valida categoría activa, código único |
| Listar (filtros: activo, categoría, buscar) | ✓ |
| Obtener servicio | ✓ joinedload(categoria) |
| Actualizar | ✓ Código único, categoría válida |
| Desactivar (soft delete) | ✓ activo=False |
| Activar | ✓ |
| Crear categoría | ✓ Nombre único (case-insensitive) |
| Eliminar categoría | ✓ Bloqueado si hay servicios |
| Exportar Excel | ⚠ Ver 4.1 (tipo categoria) |
| Integración órdenes de trabajo | ✓ DetalleOrdenTrabajo.servicio_id |
| Uso en NuevaOrdenTrabajo | ✓ GET /servicios/ |
| Uso en OrdenesTrabajo | ✓ GET /servicios/ |

---

## 7. Integración con otros módulos

| Módulo | Relación |
|--------|----------|
| Órdenes de trabajo | DetalleOrdenTrabajo.servicio_id |
| Categorías | Servicio.id_categoria → CategoriaServicio |
| Ventas | Servicios se copian a DetalleVenta vía órdenes |
| Exportaciones | GET /exportaciones/servicios |

---

## 8. Mejoras priorizadas

| Prioridad | Acción |
|-----------|--------|
| **Alta** | Corregir tipo `categoria` en exportar_servicios (int) |
| Media | showSuccess al guardar, desactivar y reactivar |
| Baja | Normalizar código a mayúsculas |
| Baja | Mensaje cuando no hay categorías (crear primero) |
| Baja | Valorar soft delete para categorías |

---

## 9. Conclusión

El módulo es sólido. El único posible bug claro es el tipo de `categoria` en exportaciones. El resto son mejoras de UX y robustez. No se detectan errores críticos de integridad de datos.
