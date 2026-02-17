# Análisis del Módulo de Gastos Operativos – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelo, router, schemas, exportaciones, integración con caja y frontend.

---

## 1. Resumen ejecutivo

El módulo de gastos operativos registra egresos del negocio:
- **Categorías:** RENTA, SERVICIOS, MATERIAL, NOMINA, OTROS, DEVOLUCION_VENTA
- **Vinculación:** Opcional con turno de caja (`id_turno`)
- **Auditoría:** Creación, actualización y eliminación se registran

Se han identificado **errores** y **mejoras**.

---

## 2. Errores detectados

### 2.1 Medios

#### E1. Fechas como string en filtros

**Archivos:** `app/routers/gastos.py` — `listar_gastos`, `resumen_gastos`; `app/routers/exportaciones.py` — `exportar_gastos`

```python
if fecha_desde:
    query = query.filter(GastoOperativo.fecha >= fecha_desde)
if fecha_hasta:
    query = query.filter(GastoOperativo.fecha <= fecha_hasta)
```

**Impacto:** Se compara columna `Date` con string. Suele funcionar por conversión implícita, pero es frágil según motor SQL. Debe parsearse explícitamente como en citas y devoluciones.

**Recomendación:** Usar `datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date()` antes de comparar.

---

#### E2. Categoría inválida en actualización

**Archivo:** `app/schemas/gasto_operativo.py` — `GastoOperativoUpdate`

**Situación:** `categoria: Optional[str] = None` no tiene validación. Al enviar `categoria: "INVALIDO"` pasa el schema y se hace `setattr`. La base de datos puede rechazarlo (Enum) o persistir datos incorrectos.

**Recomendación:** Validar con `pattern` o `Literal`; si se envía categoría, debe ser un valor permitido. En caso de valor inválido, devolver 400.

---

#### E3. Lógica duplicada entre listado, resumen y exportación

**Archivos:** `app/routers/gastos.py`, `app/routers/exportaciones.py`

**Situación:** Los filtros (fecha_desde, fecha_hasta, categoria, buscar) se repiten en:
- `listar_gastos`
- `resumen_gastos`
- `exportar_gastos`
- Y además en `q_sum` dentro de `listar_gastos`

**Recomendación:** Extraer una función común, p. ej. `query_gastos(db, fecha_desde, fecha_hasta, categoria, buscar)`, y reutilizarla en los tres flujos.

---

### 2.2 Menores

#### E4. Variable `term` en scope de `q_sum`

**Archivo:** `app/routers/gastos.py` — `listar_gastos`

**Situación:** La variable `term` se define dentro del `if buscar and buscar.strip()`. Si `buscar` está vacío, `term` no existe, pero `q_sum` usa `term` en su propio `if buscar and buscar.strip()`. En ese caso sí se evalúa el mismo bloque, por lo que `term` está definido. No hay bug real; es correcto.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Validar `orden_por` y `direccion`

**Situación:** Se usa `col_map.get((orden_por or "fecha").lower(), GastoOperativo.fecha)`. Valores inválidos caen al default sin avisar.

**Propuesta:** Validar contra valores permitidos; si es inválido, devolver 400 con mensaje claro.

---

#### M2. Validar categoría en query (filtro)

**Situación:** El parámetro `categoria` en `listar_gastos` acepta cualquier string. Si se envía "XYZ", el filtro no devuelve resultados (no hay coincidencias) pero no hay feedback al usuario.

**Propuesta:** Validar que `categoria` sea un valor del enum antes de filtrar; si no, devolver 400.

---

### 3.2 Frontend

#### M3. Formateo de fecha en tabla

**Archivo:** `frontend/src/pages/Gastos.jsx`

**Situación:** Se usa `(g.fecha || '').toString().slice(0, 10)` para mostrar. Funciona si la API devuelve ISO o "YYYY-MM-DD", pero no usa `formatearFechaSolo` para localización.

**Propuesta:** Usar `formatearFechaSolo(g.fecha)` para consistencia con otros módulos y mejor formato local (ej. dd/mm/yyyy).

---

#### M4. Validación concepto vacío al editar

**Situación:** El formulario de edición requiere concepto, pero si por error se envía vacío, el schema lo rechaza (min_length=1). El frontend ya valida. Correcto.

---

### 3.3 Integración

#### M5. Resumen de gastos en Dashboard

**Situación:** El Dashboard usa `/gastos/resumen` con parámetros de período. La ruta `/resumen` está definida antes de `/{id_gasto}`, por lo que se resuelve bien.

---

## 4. Flujos verificados

| Flujo | Estado | Detalle |
|-------|--------|---------|
| Crear gasto | ✅ | Valida concepto, monto; vincula turno si hay uno abierto |
| Listar gastos | ✅ | Filtros, paginación, total_monto |
| Resumen gastos | ✅ | Suma en período para dashboard |
| Obtener por ID | ✅ | 404 si no existe |
| Actualizar gasto | ⚠️ | Falta validación de categoría |
| Eliminar gasto | ✅ | Auditoría registrada |
| Exportar Excel | ✅ | Mismos filtros que listado |

---

## 5. Integración con otros módulos

| Módulo | Integración |
|--------|-------------|
| Caja | Gastos opcionalmente vinculados a turno (`id_turno`); se incluyen en arqueo |
| Auditoría | CREAR, ACTUALIZAR, ELIMINAR de GASTO registrados |
| Reportes utilidad | Gastos restados de utilidad bruta para utilidad neta |
| Exportaciones | Endpoint `/exportaciones/gastos` |

---

## 6. Checklist de implementación sugerido

**Prioridad alta:**
- [x] E1: Parsear fechas en listar, resumen y exportación
- [x] E2: Validar categoría en GastoOperativoUpdate

**Prioridad media:**
- [x] E3: Extraer lógica común de query (gastos_service)

**Prioridad baja:**
- [ ] M1: Validar orden_por/direccion explícitamente
- [ ] M2: Validar categoría en filtro de listado
- [ ] M3: Usar formatearFechaSolo en frontend para fechas

---

## 7. Archivos revisados

| Archivo | Rol principal |
|---------|---------------|
| `app/models/gasto_operativo.py` | Modelo GastoOperativo |
| `app/routers/gastos.py` | Router CRUD y resumen |
| `app/schemas/gasto_operativo.py` | Schemas Pydantic |
| `app/routers/exportaciones.py` | Exportación Excel |
| `frontend/src/pages/Gastos.jsx` | Vista de gastos |
