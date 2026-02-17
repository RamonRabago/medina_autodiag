# Análisis del Módulo de Inventario – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelos, servicios, routers, integración con ventas/órdenes y frontend.

---

## 1. Resumen ejecutivo

El módulo de inventario está bien estructurado y cubre los flujos principales:
- CRUD de repuestos con soft delete
- Movimientos (entrada, salida, ajuste, merma)
- Entrada masiva Excel/CSV
- Alertas de stock
- Reportes y dashboard
- Integración con ventas y órdenes de trabajo

Se han identificado varios **errores** y **mejoras** que conviene abordar.

---

## 2. Errores detectados

### 2.1 🔴 Críticos

#### E1. Import duplicado en `repuesto.py`

**Archivo:** `app/models/repuesto.py` líneas 2 y 6

```python
from sqlalchemy.orm import relationship
# ...
from sqlalchemy.orm import relationship
```

**Impacto:** Aunque no rompe la ejecución, duplica imports y puede generar avisos de linters.

**Corrección:** Eliminar la línea 6.

---

#### E2. Inconsistencia en `get_current_user` – router devoluciones

**Archivo:** `app/routers/devoluciones.py` línea 16

```python
from app.utils.jwt import get_current_user
```

**Impacto:** El resto de routers usan `app.utils.dependencies.get_current_user` (que a su vez usa jwt). Usar el mismo origen mejora trazabilidad y futuras extensiones (roles, etc.).

**Corrección:** Cambiar a:
```python
from app.utils.dependencies import get_current_user
```

---

### 2.2 🟡 Medios

#### E3. Confusión entre desactivar y eliminar permanentemente

**Archivo:** `app/routers/repuestos.py`

- `DELETE /{id_repuesto}` (eliminar_repuesto): pone `activo=False` y altera el código (`codigo_ELIM_id`), pero **no** marca `eliminado=True`.
- `DELETE /{id_repuesto}/eliminar-permanentemente`: marca `eliminado=True` y sí modifica el código.

**Impacto:** Si se reactiva un repuesto desactivado con `POST /{id}/activar`, el código queda como `MOT-001_ELIM_123` en lugar de `MOT-001`, lo que resulta confuso para el usuario.

**Recomendación:** Definir con claridad si:
- El “desactivar” ligero debe conservar el código original para permitir una reactivación limpia, o
- Si la modificación del código es intencional en todos los casos y documentarlo.

---

#### E4. Fechas en auditoría de ajustes como string

**Archivo:** `app/routers/inventario_reportes.py` líneas 106-107

```python
if fecha_desde:
    query = query.filter(func.date(MovimientoInventario.fecha_movimiento) >= fecha_desde)
```

**Impacto:** Se compara `date` con string (`YYYY-MM-DD`). En PostgreSQL suele funcionar, pero en otros motores podría fallar. Es más robusto parsear explícitamente.

**Recomendación:** Normalizar con `datetime.strptime` o validar con Pydantic:
```python
from datetime import datetime
if fecha_desde:
    fd = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
    query = query.filter(func.date(MovimientoInventario.fecha_movimiento) >= fd)
```

---

### 2.3 🟢 Menores

#### E5. Docstring roto en devoluciones

**Archivo:** `app/routers/devoluciones.py`

El docstring de `listar_devoluciones` podría estar mal formateado respecto al cierre `"""`.

**Recomendación:** Revisar que el docstring esté correctamente cerrado.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Transacción en entrada masiva

**Situación actual:** `entrada_masiva` procesa cada fila con `registrar_movimiento` y hace commit por fila (`autocommit=True`). Si falla la fila 50 de 100, las 49 anteriores ya se habrán guardado.

**Propuesta:** Opción transaccional para modo “todo o nada”:
- Parámetro opcional `transaccional: bool = False`.
- Si `transaccional=True`, envolver el bucle en una transacción y hacer rollback ante el primer error.

---

#### M2. Bloqueo explícito en `ajustar_inventario`

**Situación actual:** `ajustar_inventario` obtiene el repuesto sin bloqueo y luego llama a `registrar_movimiento`, que sí usa `with_for_update()`.

**Impacto:** El flujo final está protegido porque `registrar_movimiento` adquiere el lock. No hay condición de carrera en la práctica.

**Propuesta:** Documentar claramente en el código que la seguridad se garantiza en `registrar_movimiento`.

---

#### M3. Índices para consultas frecuentes

**Tablas:** `movimientos_inventario`, `alertas_inventario`

**Propuesta:** Evaluar índices compuestos para:
- `movimientos_inventario(id_repuesto, fecha_movimiento DESC)` – kardex, reportes
- `alertas_inventario(id_repuesto, activa)` – listado de alertas

---

#### M4. Validación de `stock_nuevo` en ajustes

**Situación actual:** `AjusteInventario.stock_nuevo` permite 0 o decimales. Un ajuste a 0 puede ser legítimo (agotamiento por merma), pero conviene exigir un motivo claro.

**Propuesta:** Si `stock_nuevo == 0`, exigir motivo más explícito (por ejemplo, longitud mínima mayor) o un campo específico de justificación para inventario en cero.

---

#### M5. Filtro de bodega para repuestos sin ubicación

**Archivo:** `app/routers/repuestos.py`, filtro de `id_bodega`

**Situación:** Los repuestos sin `id_ubicacion` ni `id_estante` se incluyen para usuarios con bodegas asignadas. No queda claro si es intencional (“sin ubicación = visible para todos”) o si deberían tratarse distinto.

**Propuesta:** Definir la regla de negocio y documentarla (p. ej. en el docstring del endpoint).

---

### 3.2 Frontend

#### M6. Manejo de repuestos eliminados en Kardex

**Archivo:** `frontend/src/pages/Kardex.jsx`

Si se accede al kardex de un repuesto eliminado (`eliminado=True`), `GET /repuestos/{id}` devolvería 404. El manejo actual parece correcto (mensaje de error genérico).

**Propuesta:** Diferenciar “repuesto no encontrado” de “repuesto eliminado” si la API lo permite (p. ej. endpoint histórico para ADMIN).

---

#### M7. Feedback tras entrada masiva

**Archivo:** `frontend/src/pages/Inventario.jsx`, modal de entrada masiva

**Situación:** Se muestran errores por fila, lo cual está bien, pero no se muestra un resumen rápido de éxito/fallo en la parte superior.

**Propuesta:** Añadir un banner tipo “X de Y filas procesadas correctamente” y destacar el número de errores.

---

### 3.3 Operacionales

#### M8. Límite de filas en entrada masiva

**Situación actual:** `MAX_ENTRADA_MASIVA_MB = 10` limita por tamaño de archivo, no por número de filas.

**Propuesta:** Añadir un límite de filas (p. ej. 500 o 1000) para evitar timeouts y sobrecarga en el servidor.

---

#### M9. Logging de movimientos sensibles

**Situación actual:** Existe logging en `registrar_movimiento` e `InventarioService`.

**Propuesta:** Incluir siempre `id_usuario` y un identificador de operación (p. ej. id de venta, orden, ajuste) en los logs relevantes, para facilitar auditoría.

---

## 4. Flujos verificados

| Flujo                          | Estado | Detalle |
|--------------------------------|--------|---------|
| Crear repuesto                 | ✅     | Validaciones y alertas correctas |
| Entrada manual                 | ✅     | Usa `registrar_movimiento` con costo promedio |
| Entrada masiva                 | ✅     | Excel/CSV, procesamiento correcto |
| Ajuste a stock específico      | ✅     | Delega a `registrar_movimiento` con lock |
| Salida por venta               | ✅     | `ventas_service.crear_venta` |
| Devolución por cancelación     | ✅     | `ventas_service.cancelar_venta` |
| Salida por orden en proceso    | ✅     | `ordenes_trabajo.detalles` al agregar repuesto |
| Devolución al quitar repuesto  | ✅     | `ordenes_trabajo.detalles` al eliminar repuesto |
| Alertas de stock               | ✅     | Tras movimientos y cambios de stock mínimo |
| Listado con bodegas            | ✅     | Filtro por bodegas del usuario |

---

## 5. Checklist de implementación sugerido

**Prioridad alta (errores críticos):**
- [x] E1: Eliminar import duplicado en `repuesto.py`
- [x] E2: Unificar `get_current_user` en `devoluciones.py`

**Prioridad media:**
- [x] E3: Ajustar desactivar para conservar código (solo activar_repuesto; eliminar-permanentemente libera código)
- [x] E4: Parsear fechas en auditoría de ajustes (datetime.strptime)

**Prioridad baja (mejoras):**
- [x] M1: Transacción opcional en entrada masiva (`transaccional=True`)
- [x] M4: Validación motivo mínimo 20 caracteres cuando stock_nuevo=0
- [x] M8: Límite de 500 filas en entrada masiva

---

## 6. Archivos revisados

| Archivo                                   | Rol principal |
|-------------------------------------------|---------------|
| `app/models/repuesto.py`                  | Modelo Repuesto |
| `app/models/movimiento_inventario.py`     | Movimientos y tipos |
| `app/models/alerta_inventario.py`         | Alertas de inventario |
| `app/services/inventario_service.py`      | Lógica de inventario |
| `app/routers/repuestos.py`                | CRUD repuestos |
| `app/routers/movimientos_inventario.py`   | Movimientos |
| `app/routers/inventario_reportes.py`      | Reportes y alertas |
| `app/routers/devoluciones.py`             | Listado de devoluciones |
| `app/services/ventas_service.py`          | Integración ventas |
| `app/routers/ordenes_trabajo/detalles.py` | Integración órdenes |
| `frontend/src/pages/Inventario.jsx`       | Vista principal inventario |
| `frontend/src/pages/EntradaInventario.jsx` | Entrada manual |
| `frontend/src/pages/InventarioAlertas.jsx`| Alertas |
| `frontend/src/pages/Kardex.jsx`           | Kardex por repuesto |
| `frontend/src/pages/Devoluciones.jsx`     | Listado devoluciones |
