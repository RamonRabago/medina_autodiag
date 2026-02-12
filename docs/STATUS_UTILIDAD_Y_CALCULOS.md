# Status: Cálculos de utilidad y flujos de dinero

**Fecha:** Febrero 2026  
**Objetivo:** Verificar que los cálculos para ver la utilidad real del negocio se aplican correctamente.

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Reporte utilidad** | ✅ Correcto | Ingresos - CMV - Merma - Gastos = Utilidad neta |
| **Costo de ventas (CMV)** | ✅ Correcto | MovimientoInventario.costo_total en SALIDAs |
| **Cierre de caja** | ✅ Correcto | Apertura + cobros - pagos OC - pagos manuales - gastos |
| **Dashboard total facturado** | ✅ Correcto | Suma de pagos recibidos (no venta.total) |
| **Dashboard valor inventario** | ⚠️ **Bug** | Muestra $0 (ver sección 5) |
| **Utilidad en Dashboard** | ❌ No existe | No hay tarjeta de utilidad neta en el inicio |

---

## 2. Fórmula de utilidad (implementada)

```
Utilidad bruta = Total ventas (Venta.total) - Costo CMV - Pérdidas por merma
Utilidad neta  = Utilidad bruta - Gastos operativos
```

**Dónde verla:** Ventas → pestaña Reportes → filtros por fecha → "Reporte de utilidad"

**Export:** Botón "Exportar utilidad a Excel" → `/exportaciones/utilidad`

**Costo (CMV):**
- Ventas con orden: suma `MovimientoInventario.costo_total` donde `referencia = orden.numero_orden` (salidas por esa orden)
- Ventas manuales: suma `MovimientoInventario.costo_total` donde `id_venta = venta.id_venta`
- Si `cliente_proporciono_refacciones = true`: costo = 0

**Pérdidas merma:** Suma de `CancelacionProducto.costo_total_mer` de ventas canceladas en el período.

**Gastos:** Suma de `GastoOperativo.monto` en el período.

---

## 3. Lo que funciona bien

### 3.1 Costo en movimientos de inventario

- Al registrar SALIDA (venta o orden), `InventarioService.registrar_movimiento` calcula:
  - `precio_unitario = movimiento.precio_unitario or repuesto.precio_compra`
  - `costo_total = precio_unitario * cantidad`
- El CMV usa el costo promedio ponderado del inventario (precio_compra del repuesto).

### 3.2 Cierre de turno de caja

```
esperado = monto_apertura
         + sum(Pago.monto) donde metodo=EFECTIVO
         - sum(PagoOrdenCompra.monto) efectivo del turno
         - sum(PagoCuentaPagarManual.monto) efectivo del turno
         - sum(GastoOperativo.monto) del turno

diferencia = monto_contado - esperado
```

El cierre forzado (ADMIN) usa la misma lógica.

### 3.3 Total facturado (Dashboard)

- Es la suma de **pagos recibidos** (`Pago.monto`), no el total de ventas.
- Filtrado por fecha del pago y excluye ventas canceladas.
- Coherente para "efectivo que entró en caja".

### 3.4 Gastos operativos

- Se restan en utilidad neta.
- Se incluyen en cierre de caja cuando tienen `id_turno`.
- Dashboard muestra total del mes.

---

## 4. Servicios (mano de obra)

- Los **servicios** no tienen costo en inventario (no consumen productos).
- En utilidad: la parte de servicios de una venta tiene costo = 0.
- **Implicación:** Si quieres trackear costo de mano de obra (salarios, comisiones), no está implementado. La utilidad actual solo considera costo de productos vendidos.

---

## 5. Bug: Valor inventario en Dashboard

**Problema:** El Dashboard muestra "$0" en "Valor inventario".

**Causa:** El API `/inventario/reportes/dashboard` devuelve:
```json
{
  "metricas": {
    "valor_inventario": {
      "valor_compra": 12345.67,
      "valor_venta": 15000.00,
      "utilidad_potencial": 2654.33,
      "total_productos": 50,
      "total_unidades": 200
    },
    ...
  }
}
```

El frontend usa `Number(stats.inventario?.valor_inventario)`. Como `valor_inventario` es un objeto, `Number({...})` = NaN → se muestra 0.

**Solución:** Usar `stats.inventario?.valor_inventario?.valor_venta` (o `valor_compra` según criterio).

---

## 6. Lo que falta

| Ítem | Prioridad | Descripción |
|------|-----------|-------------|
| **Valor inventario en Dashboard** | Alta | Corregir referencia al objeto (ver sección 5) |
| **Utilidad en Dashboard** | Media | Añadir tarjeta con utilidad neta del mes (requiere endpoint o reutilizar lógica) |
| **Costo de servicios** | Baja | Si se quiere incluir mano de obra en CMV, requiere modelo y flujo nuevo |
| **Total ventas vs total cobrado** | Baja | Dashboard muestra "pagos recibidos"; opcional: mostrar también "ventas del periodo" (facturado) |

---

## 7. Archivos clave

| Archivo | Función |
|---------|---------|
| `app/routers/ventas/reportes.py` | `reporte_utilidad` – cálculo por ventas |
| `app/routers/exportaciones.py` | `exportar_utilidad` – Excel |
| `app/services/caja_service.py` | `cerrar_turno` – esperado y diferencia |
| `app/services/inventario_service.py` | `registrar_movimiento` – costo_total en SALIDAs |
| `app/routers/inventario_reportes.py` | `dashboard_inventario` – valor inventario |
| `frontend/src/pages/Dashboard.jsx` | Tarjetas del inicio |
| `frontend/src/pages/Ventas.jsx` | Reporte de utilidad, export |

---

## 8. Recomendaciones

1. **Corregir bug valor inventario** en Dashboard (1 línea en `Dashboard.jsx`).
2. **Opcional:** Añadir tarjeta "Utilidad del mes" en Dashboard (llamar a `/ventas/reportes/utilidad` con fechas del mes).
3. Documentar para el usuario que "Total facturado" = pagos recibidos, no ventas pendientes de cobro.
