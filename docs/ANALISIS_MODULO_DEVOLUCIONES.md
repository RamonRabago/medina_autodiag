# Análisis del Módulo de Devoluciones – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Router, integración con movimientos de inventario, ventas, órdenes de trabajo, exportaciones y frontend.

---

## 1. Resumen ejecutivo

El módulo de devoluciones lista entradas al inventario causadas por:
- **Devolución por venta:** Cancelación o actualización de venta (productos removidos)
- **Cancelación orden:** Orden de trabajo cancelada (repuestos no utilizados)

Las devoluciones son **movimientos de inventario** (`MovimientoInventario`) con `tipo_movimiento=ENTRADA` y motivo que empieza por "Devolución%" o "Cancelación orden%". No existe modelo propio de devolución; se consulta la vista de movimientos filtrada.

Se han identificado **errores** y **mejoras**.

---

## 2. Errores detectados

### 2.1 Medios

#### E1. Fechas como string en exportación

**Archivo:** `app/routers/exportaciones.py` — `exportar_devoluciones`, líneas 923-927

```python
if fecha_desde:
    query = query.filter(func.date(MovimientoInventario.fecha_movimiento) >= fecha_desde)
if fecha_hasta:
    query = query.filter(func.date(MovimientoInventario.fecha_movimiento) <= fecha_hasta)
```

**Impacto:** Se compara `func.date()` con string. Mismo patrón que E1 de citas (ya corregido). Puede fallar o comportarse distinto según el motor SQL.

**Recomendación:** Parsear explícitamente con `datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date()`.

---

#### E2. Validación de fechas vacías/inválidas

**Archivo:** `app/routers/devoluciones.py` y frontend

**Situación:** El frontend envía `fecha_desde + 'T00:00:00'` y `fecha_hasta + 'T23:59:59'` solo si las fechas tienen valor. Si el usuario borra el input de fecha, `fechaDesde`/`fechaHasta` quedan como `''` y no se envían. El backend recibe sin filtro de fecha.

**Impacto:** Menor. Comportamiento esperado: sin fechas = sin filtro. Pero si en algún momento se envía `""` explícitamente, FastAPI con `Optional[datetime]` podría devolver error de validación.

**Recomendación:** Asegurar que el frontend nunca envíe cadena vacía cuando el campo está vacío (actualmente ya lo evita con `if (fechaDesde)`).

---

### 2.2 Menores

#### E3. Lógica duplicada entre listado y exportación

**Archivos:** `app/routers/devoluciones.py` y `app/routers/exportaciones.py`

**Situación:** La construcción del query (filtro `motivo`, `buscar`, `tipo_motivo`, fechas) está duplicada. Cualquier cambio en criterios exige editar dos lugares.

**Recomendación:** Extraer función común, p. ej. `_query_devoluciones(db, fecha_desde, fecha_hasta, buscar, tipo_motivo)`, y usar en ambos endpoints.

---

#### E4. Inconsistencia de permisos

**Archivo:** `app/routers/devoluciones.py`

**Situación:** `listar_devoluciones` usa `get_current_user` (cualquier usuario autenticado). `exportar_devoluciones` usa `require_roles("ADMIN", "CAJA", "TECNICO")`. Esto permite que un rol como `EMPLEADO` vea el listado pero no pueda exportar.

**Impacto:** Puede ser intencional (solo ciertos roles exportan). Si se desea coherencia, valorar usar `require_roles` también en el listado.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Parsear fechas en exportación (relacionado con E1)

**Propuesta:** Aplicar el mismo patrón que en citas: parsear `fecha_desde`/`fecha_hasta` como `date` antes de comparar con `func.date()`.

---

#### M2. Validar `orden_por` y `direccion` en listado

**Archivo:** `app/routers/devoluciones.py`

**Situación:** Se usa `col_map.get((orden_por or "fecha").lower(), ...)`. Valores inválidos caen al default (fecha). Para `orden_por == "repuesto"` se usa lógica especial. No hay validación estricta.

**Propuesta:** Validar contra valores permitidos; si es inválido, devolver 400 con detalle en lugar de fallar silenciosamente al default.

---

#### M3. Manejo de repuesto eliminado

**Situación:** Si un repuesto fue eliminado (hard delete), `MovimientoInventario.id_repuesto` sigue apuntando a ese ID. El `outerjoin` con Repuesto devuelve NULL en `repuesto`. La serialización ya contempla `m.repuesto` nulo mostrando `#id_repuesto`. En el filtro `buscar` con `Repuesto.nombre.ilike(term)` cuando repuesto es NULL, la fila podría excluirse si no coincide por referencia/motivo.

**Propuesta:** Documentar el comportamiento. Si se implementa soft delete en repuestos, asegurar que las devoluciones históricas sigan mostrándose.

---

### 3.2 Frontend

#### M4. Deep-link a venta desde referencia

**Archivo:** `frontend/src/pages/Devoluciones.jsx`, línea 205

**Situación:** El enlace "Venta #123" va a `/ventas`. La página de Ventas acepta `?id=123` para abrir directamente el detalle de la venta.

**Propuesta:** Cambiar el enlace a `/ventas?id=${m.id_venta}` para abrir la venta específica en el modal de detalle.

---

#### M5. Filtro por repuesto

**Situación:** El backend expone `id_repuesto` como filtro, pero el frontend no lo usa.

**Propuesta:** Añadir selector de repuesto (autocompletado o desplegable) cuando tenga sentido para el flujo de uso.

---

#### M6. Paginación: dependencia en `cargar`

**Situación:** El `useEffect` recarga con `cargar(1)` al cambiar filtros. Los botones Anterior/Siguiente llaman `cargar(pagina - 1)` y `cargar(pagina + 1)`. Al cambiar filtros, `pagina` no se resetea explícitamente, pero `cargar(1)` se ejecuta y `setPagina(data.pagina ?? 1)` ajusta a 1. Correcto.

**Propuesta:** Ninguna; el flujo es coherente.

---

### 3.3 Documentación

#### M7. Documentar orígenes de devoluciones

**Propuesta:** Añadir a la documentación del módulo (o a `LOGICA_INVENTARIO`) los flujos que generan devoluciones:
- Cancelación de venta → `ventas_service.py`
- Actualización de venta (productos removidos) → `ventas_service.py`
- Cancelación de orden (repuestos no utilizados) → `ordenes_trabajo/acciones.py`

---

## 4. Flujos verificados

| Flujo | Estado | Detalle |
|-------|--------|---------|
| Listar devoluciones | ✅ | Filtros por fecha, buscar, tipo motivo, orden |
| Exportar a Excel | ✅ | Misma lógica de filtros; requiere roles ADMIN/CAJA/TECNICO |
| Link a kardex de repuesto | ✅ | `/inventario/kardex/{id_repuesto}` |
| Link a ventas | ⚠️ | Va a `/ventas`; podría mejorar a `/ventas?id=X` |
| Paginación | ✅ | Funciona correctamente |

---

## 5. Integración con otros módulos

| Módulo | Integración |
|--------|-------------|
| Inventario | Devoluciones = movimientos ENTRADA con motivo Devolución%/Cancelación orden% |
| Ventas | Cancelación o actualización de venta genera movimientos de devolución |
| Órdenes de trabajo | Cancelación de orden con repuestos no utilizados genera devoluciones |
| Exportaciones | Endpoint `/exportaciones/devoluciones` reutiliza criterios del listado |

---

## 6. Checklist de implementación sugerido

**Prioridad alta:**
- [x] E1: Parsear fechas en exportación de devoluciones (igual que E1 citas)

**Prioridad media:**
- [x] E3: Extraer lógica común de query entre listado y exportación
- [ ] M4: Deep-link a venta desde "Venta #X" en frontend

**Prioridad baja:**
- [x] E4: Unificar permisos con require_roles (ADMIN, CAJA, TECNICO) en listado
- [ ] M2: Validar `orden_por`/`direccion` explícitamente
- [ ] M5: Exponer filtro por repuesto en frontend (si aplica)
- [ ] M7: Documentar flujos de origen en docs

---

## 7. Archivos revisados

| Archivo | Rol principal |
|---------|---------------|
| `app/routers/devoluciones.py` | Listado de devoluciones |
| `app/routers/exportaciones.py` | Exportación Excel de devoluciones |
| `app/models/movimiento_inventario.py` | Modelo base |
| `app/services/ventas_service.py` | Creación de devoluciones por venta |
| `app/routers/ordenes_trabajo/acciones.py` | Devoluciones por cancelación de orden |
| `frontend/src/pages/Devoluciones.jsx` | Vista de listado |
