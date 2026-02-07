# Análisis de la lógica de Órdenes de Compra

**Fecha:** 29/01/2026  
**Objetivo:** Verificar consistencia, manejo de tipos (Decimal/float), diccionarios, y posibles errores de compatibilidad.

---

## 1. Resumen ejecutivo

La lógica de órdenes de compra está **en general bien estructurada**, con buen uso de `Decimal` en el backend para montos y conversiones seguras. Se detectaron **algunos puntos a corregir** que podrían causar errores en producción.

---

## 2. Backend – Modelos y esquemas

### 2.1 Modelos (`app/models/`)

| Campo | Modelo | Tipo DB | Uso |
|-------|--------|---------|-----|
| `total_estimado` | OrdenCompra | Numeric(12,2) | ✅ Correcto |
| `precio_unitario_estimado` | DetalleOrdenCompra | Numeric(10,2) | ✅ Correcto |
| `precio_unitario_real` | DetalleOrdenCompra | Numeric(10,2) | ✅ Correcto |
| `monto` | PagoOrdenCompra | Numeric(10,2) | ✅ Correcto |

### 2.2 Schemas Pydantic (`app/schemas/orden_compra.py`)

- **DetalleOrdenCompraItem**: `precio_unitario_estimado: float`, `cantidad_solicitada: int` → Pydantic acepta int/float y los valida correctamente.
- **ItemRecepcion**: `precio_unitario_real: Optional[float]` → ✅
- **PagoOrdenCompraCreate**: `monto: float` → ✅

### 2.3 Utilidades (`app/utils/decimal_utils.py`)

- `to_decimal()`: Convierte int, float, str y `None` de forma segura.
- `money_round()`: Redondeo bancario a 2 decimales.
- `to_float_money()`: Para serializar montos a JSON sin problemas de precisión.

**Uso en ordenes_compra.py:** ✅ Uso correcto en `_calcular_total_a_pagar`, `listar_cuentas_por_pagar`, `registrar_pago`, etc.

---

## 3. Flujo de datos Backend ↔ Frontend

### 3.1 Respuestas del API

| Endpoint | Campos monetarios | Formato |
|----------|-------------------|---------|
| `_orden_a_dict` | `saldo_pendiente`, `total_estimado`, `precio_unitario_estimado`, `precio_unitario_real` | `float()` |
| `listar_cuentas_por_pagar` | `total_a_pagar`, `total_pagado`, `saldo_pendiente`, `total_saldo_pendiente` | `to_float_money()` → float |

**Conclusión:** Todos los montos se devuelven como `float` en JSON, coherente con el frontend.

### 3.2 Detalles – Clave `id` vs `id_detalle`

- Backend `_orden_a_dict`: devuelve `"id": d.id` en cada detalle.
- Frontend recibir: usa `id_detalle: d.id` → ✅ Coincide.
- Schema `ItemRecepcion`: usa `id_detalle: int` → ✅ Coincide.

---

## 4. API de catálogos (proveedores, repuestos, vehículos)

| API | Respuesta | Frontend |
|-----|-----------|----------|
| `/proveedores/` | `{ proveedores: [...], total, pagina, ... }` | `r.data?.proveedores ?? r.data ?? []` ✅ |
| `/repuestos/` | `{ repuestos: [...], total, ... }` | `r.data?.repuestos ?? r.data ?? []` ✅ |
| `/catalogo-vehiculos/` | `{ vehiculos: [...], total, ... }` | `r.data?.vehiculos ?? r.data ?? []` ✅ |

---

## 5. InventarioService y recepción

- `MovimientoInventarioCreate(precio_unitario=Decimal(str(precio)))` → ✅ Conversión explícita a `Decimal`.
- `InventarioService.registrar_movimiento` usa `to_decimal()` para `precio_unitario` y cálculos internos → ✅ Correcto.

---

## 6. Problemas detectados y recomendaciones

### 6.1 Error de renderizado React por `detail` (alta prioridad)

**Ubicación:** `NuevaOrdenCompra.jsx`, `EditarOrdenCompra.jsx`  
**Problema:** Si la API devuelve errores de validación, `detail` es un array de objetos (`{type, loc, msg, ...}`). Asignar eso a `error` y renderizar `{error}` provoca:

```
Objects are not valid as a React child
```

**Solución:** Extraer mensaje legible como en `Kardex.jsx`:

```javascript
const d = err.response?.data?.detail
const msg = typeof d === 'string' ? d : (Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : 'Error al...')
setError(msg)
```

**Archivos a corregir:**

- `frontend/src/pages/NuevaOrdenCompra.jsx` (líneas 69, 143)
- `frontend/src/pages/EditarOrdenCompra.jsx` (líneas 69, 96, 195)

---

### 6.2 Comparación de float para `precio_unitario_real` (prioridad media)

**Ubicación:** `app/routers/ordenes_compra.py`, líneas 545-546

```python
if precio != float(det.precio_unitario_estimado):
    det.precio_unitario_real = precio
```

**Problema:** Comparación directa de float puede dar falsos positivos por precisión (p. ej. 59.999999 vs 60.0).

**Recomendación:**

```python
from app.utils.decimal_utils import to_decimal, money_round
# ...
precio_dec = to_decimal(precio)
estimado_dec = to_decimal(det.precio_unitario_estimado or 0)
if abs(precio_dec - estimado_dec) >= Decimal("0.01"):
    det.precio_unitario_real = float(money_round(precio_dec))
```

---

### 6.3 Precio estimado para repuestos “nuevos” en NuevaOrdenCompra (prioridad baja)

**Ubicación:** `NuevaOrdenCompra.jsx`  
**Problema:** Solo se muestra el input de precio para `tipo === 'existente'`. Los items “nuevo” quedan siempre con `precio_unitario_estimado: 0`, afectando el total estimado.

**Impacto:** En la recepción se obliga a ingresar precio real; el flujo funciona, pero el total estimado es engañoso.

**Recomendación:** Añadir campo de precio opcional para items “nuevo” para mejorar UX y total estimado.

---

### 6.4 Validación de `detail` en alertas

**Ubicación:** `OrdenesCompra.jsx`, `CuentasPorPagar.jsx`, etc.  
**Estado:** Usan `alert(err.response?.data?.detail || '...')`. Si `detail` es un array, `alert()` lo convierte a string y no rompe la app, pero el mensaje puede ser poco legible. Opcional: aplicar la misma normalización que para `setError`.

---

## 7. Checklist de consistencia

| Área | Estado |
|------|--------|
| Decimal vs float en backend | ✅ Uso correcto de Decimal y to_float_money |
| Serialización JSON de montos | ✅ Siempre float con 2 decimales |
| Claves de diccionarios (id vs id_detalle) | ✅ Consistentes |
| Conversión int/float en frontend | ✅ parseInt/parseFloat usados bien |
| Manejo de errores API | ⚠️ Corregir en NuevaOrdenCompra y EditarOrdenCompra |
| Comparación de precios | ⚠️ Evitar comparación directa de float |

---

## 8. Archivos revisados

- `app/models/orden_compra.py`
- `app/models/pago_orden_compra.py`
- `app/schemas/orden_compra.py`
- `app/routers/ordenes_compra.py`
- `app/services/inventario_service.py`
- `app/utils/decimal_utils.py`
- `frontend/src/pages/OrdenesCompra.jsx`
- `frontend/src/pages/NuevaOrdenCompra.jsx`
- `frontend/src/pages/EditarOrdenCompra.jsx`
- `frontend/src/pages/CuentasPorPagar.jsx`
- `app/routers/catalogo_vehiculos.py`
- `app/routers/proveedores.py`
- `app/routers/repuestos.py`

---

## 9. Conclusión

La lógica de órdenes de compra está bien integrada entre backend y frontend. Los puntos a corregir son:

1. Manejo de errores de validación en `NuevaOrdenCompra` y `EditarOrdenCompra`.
2. Comparación segura de precios en la recepción.
3. Opcionalmente, mejorar el total estimado para repuestos “nuevos”.

Con estos ajustes, se reduce el riesgo de fallos por incompatibilidad de tipos y errores de validación.
