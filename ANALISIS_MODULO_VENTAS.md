# Análisis del Módulo de Ventas

## Resumen ejecutivo

El módulo de ventas está bien integrado con órdenes de trabajo, inventario, caja y pagos. La lógica de negocio es coherente en la mayoría de los flujos. Se identifican algunos puntos de mejora y posibles inconsistencias menores relacionadas con contabilidad y UX.

---

## 1. Estructura del módulo

| Componente | Ubicación | Rol |
|------------|-----------|-----|
| Modelos | `venta.py`, `detalle_venta.py`, `pago.py` | Venta, DetalleVenta, Pago |
| Servicio | `ventas_service.py` | Lógica de negocio (crear, actualizar, cancelar, vincular) |
| Routers | `ventas/crud.py`, `acciones.py`, `reportes.py`, `ticket.py`, `helpers.py` | API REST |
| Pagos | `pagos.py` | Registrar pagos (requiere turno de caja) |

---

## 2. Flujos verificados

### 2.1 Venta manual (sin orden)
- **Crear**: Descuenta stock vía `InventarioService.registrar_movimiento` (SALIDA) con `id_venta`.
- **Actualizar**: Si cambian productos, devuelve los anteriores al inventario y descuenta los nuevos.
- **Costo (reporte utilidad)**: Se obtiene de `MovimientoInventario` donde `id_venta` y `tipo_movimiento=SALIDA`.

### 2.2 Venta desde orden
- **Crear**: No descuenta stock (ya se descontó al INICIAR la orden).
- **Vincular orden**: Copia ítems de orden a DetalleVenta; no mueve inventario.
- **Costo (reporte utilidad)**: Se obtiene de `MovimientoInventario` donde `referencia=orden.numero_orden` (movimientos creados al INICIAR).

### 2.3 Cancelación
- **Productos**: Reutilizable → devuelve stock (ENTRADA); Merma → `CancelacionProducto` (costo_total_mer).
- **Reporte utilidad**: Resta `perdidas_mer` (suma de `CancelacionProducto.costo_total_mer`).

### 2.4 Pagos y caja
- **Registrar pago**: Requiere turno abierto; suma a `Pago`; si total_pagado == total, venta pasa a PAGADA.
- **Cierre turno**: `esperado = sum(Pago.monto) - sum(PagoOrdenCompra.monto)` donde método=EFECTIVO.

---

## 3. Hallazgos y recomendaciones

### 3.1 Contabilidad / Cálculos

#### ✅ Coherente
- **Reporte utilidad**: `Utilidad = Ingresos - CMV - Pérdidas merma`. Fórmula correcta.
- **CMV (Costo Mercancía Vendida)**: Para ventas desde orden usa `referencia=numero_orden`; para manuales usa `id_venta`.
- **IVA**: Backend usa `settings.IVA_FACTOR`; frontend consume `/config` que devuelve `iva_porcentaje`. Misma base (config/env).

#### ⚠️ Posible inconsistencia: Total facturado en Dashboard
- **Situación**: `/ordenes-trabajo/estadisticas/dashboard` devuelve `total_facturado = sum(Pago.monto)` sin filtro de fecha.
- **Efecto**: El Dashboard muestra el total histórico de pagos, no "facturado hoy" ni "facturado este mes".
- **Recomendación**: Aclarar en la UI ("Total facturado (histórico)") o añadir filtro opcional por periodo si se desea "facturado hoy/mes".

#### ⚠️ Ventas con `id_orden` pero sin movimientos
- Si una orden se inició sin repuestos (solo servicios), no hay movimientos de inventario con `referencia=numero_orden`.
- El reporte de utilidad asignará costo=0 a esa venta. **Coherente** (no hay CMV en servicios puros).

### 3.2 Inventario

#### ✅ Coherente
- Venta manual: descuenta stock al crear y al actualizar (si cambian productos).
- Venta desde orden: stock descontado al INICIAR; la venta no toca inventario.
- Cancelación: devuelve stock según cantidad_reutilizable; merma se registra en `CancelacionProducto`.

#### ⚠️ Edición de venta con orden vinculada
- `actualizar_venta` solo ajusta inventario si `venta.id_orden is None` (venta manual).
- Si la venta tiene orden vinculada y se editan detalles, el stock **no** se ajusta. Esto es coherente porque los productos vienen de la orden, cuyo stock ya se descontó.

### 3.3 Caja y pagos

#### ✅ Coherente
- Pagos requieren turno abierto.
- `Pago` tiene `id_turno`; cierre de turno incluye pagos de ventas y resta pagos a proveedores en efectivo.

#### Sin observaciones adicionales.

### 3.4 IVA y configuración

- Backend: `IVA_FACTOR = 1 + IVA_PORCENTAJE/100` desde `.env`.
- Frontend: usa `config.iva_porcentaje` para mostrar y calcular totales en UI.
- Si `.env` cambia, el backend recalcula correctamente; el frontend toma `/config` al cargar. **Coherente** si `/config` se llama al inicio.

### 3.5 Integración con otros módulos

| Módulo | Integración |
|--------|-------------|
| Órdenes de trabajo | Crear venta desde orden, vincular/desvincular; cancelación de orden desvincula venta. |
| Inventario | Movimientos SALIDA/ENTRADA; reporte utilidad usa `costo_total` de movimientos. |
| Caja | Pagos ligados a turno; cierre calcula esperado incluyendo ventas. |
| Gastos | No hay vínculo directo; Gastos y Ventas son independientes (correcto). |
| Órdenes de compra | Pagos a proveedores se restan del efectivo esperado en cierre. |

---

## 4. Lo que falta o se puede mejorar

### 4.1 Funcionalidad

1. **Cuentas por cobrar**  
   Existe reporte y exportación. No hay alertas ni recordatorios automáticos. **Prioridad baja.**

2. **Estado PENDIENTE vs PAGADA**  
   La transición a PAGADA ocurre cuando `total_pagado == total`. No hay estado intermedio (ej. "PARCIAL"). **Opcional.**

3. **Venta desde orden en frontend**  
   El flujo "crear venta desde orden" existe en API (`POST /ventas/desde-orden/{orden_id}`), pero no se encontró un botón explícito en Ventas.jsx. Si el flujo principal es crear venta → vincular orden, está cubierto. Si se quiere crear directamente desde la orden, habría que exponerlo en la UI.

### 4.2 UX / Claridad

1. **Total facturado**  
   Añadir texto o tooltip que indique si es histórico o del periodo seleccionado.

2. **Validación de total vs pagado**  
   En `actualizar_venta` ya se valida que el total no sea menor que lo pagado. Bien implementado.

### 4.3 Robustez

1. **Decimal vs float**  
   Se usa `to_decimal`, `money_round` y `to_float_money` en cálculos monetarios. Coherente con buenas prácticas.

2. **Transacciones**  
   Las operaciones críticas usan `db.commit()` y `db.rollback()` en bloques try/except. Adecuado.

---

## 5. Resumen de recomendaciones priorizadas

| Prioridad | Recomendación |
|-----------|---------------|
| Alta | Ninguna crítica detectada. |
| Media | Aclarar en Dashboard si "Total facturado" es histórico o por periodo; o añadir filtro de fecha si se requiere. |
| Baja | Revisar si el flujo "crear venta desde orden" debe estar visible en la UI (por ejemplo, desde OrdenesTrabajo). |
| Baja | Documentar que `total_facturado` en estadísticas es la suma de todos los pagos (sin filtro de fecha). |

---

## 6. Conclusión

El módulo de ventas está correctamente implementado y alineado con inventario, caja, órdenes de trabajo y reporte de utilidad. No se encontraron errores que afecten el cálculo contable. Las mejoras sugeridas son sobre claridad de métricas (total facturado) y UX, no sobre corrección de lógica de negocio.
