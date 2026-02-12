# Auditoría contable – MedinaAutoDiag

Revisión exhaustiva de la lógica contable en ingresos, egresos, caja y reportes.

---

## 1. Flujos de dinero

### 1.1 INGRESOS (entrada de efectivo)

| Fuente | Modelo | Condición | Uso |
|--------|--------|-----------|-----|
| Pagos de ventas | `Pago` | `Venta.estado != CANCELADA` | total_facturado, ingresos-detalle, cierre caja |

- **total_facturado** (Dashboard): `sum(Pago.monto)` donde `Venta.estado != CANCELADA`, filtrado por `Pago.fecha`.
- **ingresos-detalle** (VentasIngresos): Mismo criterio.
- **Cierre turno**: `sum(Pago.monto)` del turno, sin filtrar por estado de venta (se asume que el efectivo físico ya entró).

**Consistencia:** correcta. Los reportes excluyen ventas canceladas; en caja se cuentan todos los pagos del turno.

---

### 1.2 EGRESOS (salida de efectivo)

| Fuente | Modelo | Vinculación turno | Uso |
|--------|--------|-------------------|-----|
| Gastos operativos | `GastoOperativo` | `id_turno` (opcional) | Dashboard, cierre caja, detalle turno |
| Pagos a proveedores | `PagoOrdenCompra` | `id_turno` solo si `metodo=EFECTIVO` | Cierre caja, cuentas por pagar |

- **Gastos**: Si hay turno abierto, se vincula. Si no, `id_turno = NULL` (cuenta igual en total del periodo, no en cierre).
- **Pagos proveedores**: Solo pagos en efectivo tienen `id_turno`; tarjeta/transferencia no salen de caja.

**Consistencia:** correcta. Solo egresos en efectivo vinculados al turno se consideran en cierre.

---

## 2. Cierre de turno de caja

### Fórmula actual (después del ajuste)

```
esperado = monto_apertura
         + sum(Pago.monto) del turno
         - sum(PagoOrdenCompra.monto) donde metodo=EFECTIVO y id_turno=X
         - sum(GastoOperativo.monto) del turno

diferencia = monto_contado - esperado
```

**Archivo:** `app/services/caja_service.py`

**Estado:** correcto. Incluye apertura, ingresos, pagos a proveedores en efectivo y gastos operativos.

---

### Consideración sobre métodos de pago

- `Pago` incluye EFECTIVO, TARJETA, TRANSFERENCIA.
- El efectivo físico en caja solo aumenta con pagos en EFECTIVO.
- Si el negocio deposita todo junto (efectivo + comprobantes de tarjeta/transferencia) y cierra por “total a depositar”, la fórmula actual es coherente.
- Si se cierra solo efectivo físico, habría que cambiar a:  
  `sum(Pago.monto)` donde `Pago.metodo = 'EFECTIVO'`.

---

## 3. Inconsistencias detectadas

### 3.1 Cierre forzado de turno (ADMIN)

**Archivo:** `app/routers/caja.py` → `cerrar_turno_forzado`

- No usa `caja_service.cerrar_turno`.
- No calcula ni guarda `diferencia`.
- Solo actualiza `monto_cierre`, `fecha_cierre`, `estado`.

**Recomendación:** Que el cierre forzado use la misma lógica de cálculo de esperado y diferencia (o al menos calcule `diferencia = monto_cierre - esperado`), para mantener trazabilidad y alertas.

---

### 3.2 Venta cancelada con pagos previos

- Al cancelar una venta, los registros de `Pago` no se eliminan ni se reversan.
- No existe flujo de devolución de dinero.
- En reportes: se excluyen ventas canceladas (total_facturado, ingresos-detalle).
- En caja: se cuentan todos los pagos del turno.

**Implicación:** Si se cobra y luego se cancela la venta, el efectivo sigue en caja y en reportes no se considera ingreso “válido”. Es coherente si no hay devolución de dinero y la decisión es no incluir ventas canceladas en ingresos.

---

### 3.3 Reporte de utilidad

**Fórmula actual:**  
`Utilidad = total_ingresos (Venta.total) - costo_productos - pérdidas_merma`

- No resta gastos operativos.
- Representa utilidad bruta, no neta.

**Opcional:** Para utilidad neta:  
`Utilidad_neta = Utilidad_bruta - total_gastos_periodo`

---

## 4. Resumen por módulo

| Módulo | Qué mide | Estado |
|--------|----------|--------|
| **Dashboard total_facturado** | Suma de pagos recibidos (excl. canceladas) por periodo | OK |
| **Dashboard total_gastos_mes** | Suma de gastos operativos por mes | OK |
| **VentasIngresos** | Detalle de pagos (ingresos) por periodo | OK |
| **Gastos** | CRUD + resumen por periodo | OK |
| **Caja cierre** | Efectivo esperado = apertura + ingresos - egresos (proveedores + gastos) | OK (corregido) |
| **Caja cierre forzado** | Usa mismo servicio que cierre normal (esperado, diferencia, alertas) | OK |
| **Cuentas por pagar** | Saldo pendiente órdenes de compra | OK |
| **Reporte utilidad** | Ingresos - costo - merma (bruta) | OK; opcional: restar gastos |

---

## 5. Recomendaciones

1. ~~**Alta prioridad:** Ajustar `cerrar_turno_forzado` para que use la misma lógica de cálculo que el cierre normal.~~ ✅ Implementado.
2. **Media prioridad:** Evaluar si el esperado debe basarse solo en pagos en EFECTIVO, según el procedimiento real de cierre.
3. **Baja prioridad:** Incluir gastos operativos en el reporte de utilidad si se quiere utilidad neta.

---

*Documento generado como parte de la auditoría contable del sistema.*
