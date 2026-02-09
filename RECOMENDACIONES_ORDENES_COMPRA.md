# Análisis y Recomendaciones: Módulo Órdenes de Compra

**Fecha:** 30/01/2026  
**Objetivo:** Verificar completitud, consistencia con Inventario, y sugerir mejoras desde programación y administración de negocios.

---

## 1. Estado actual del módulo

### 1.1 Flujo implementado

```
BORRADOR → Enviar (email) → ENVIADA → Subir cotización → Autorizar → AUTORIZADA 
  → Fecha promesa → Recibir mercancía → RECIBIDA / RECIBIDA_PARCIAL 
  → Registrar pagos → Cuentas por pagar (saldo pendiente)
```

- **Inventario:** Al recibir, se crea movimiento ENTRADA por cada ítem (referencia `OC-{id}`).
- **Costo promedio ponderado:** Se actualiza `precio_compra` del repuesto.
- **Repuestos nuevos:** Se crean en inventario con código "PDTE EDITAR-N" si no traen código.
- **Cuentas por pagar:** Saldo = total recibido − pagos registrados.
- **Dashboard:** Alertas de órdenes sin recibir y vencidas.

### 1.2 Módulos relacionados

| Módulo | Relación con OC |
|--------|-----------------|
| **Inventario** | Entradas por recepción; Kardex con comprobantes |
| **Proveedores** | Proveedor por OC; no muestra saldo pendiente por proveedor |
| **Cuentas por pagar** | Lista OC con saldo; registrar pago |
| **Dashboard** | Alertas OC sin recibir / vencidas |
| **Caja** | Turnos; no incluye pagos a proveedores |
| **Gastos** | Gastos operativos; no incluye pagos OC |
| **EntradaInventario** | Entrada manual; flujo paralelo a OC |

---

## 2. Lo que está bien

1. Flujo BORRADOR → ENVIADA → AUTORIZADA → RECIBIDA con validaciones coherentes.
2. Uso correcto de `Decimal` y conversiones monetarias.
3. Integración con inventario: movimiento ENTRADA, costo promedio ponderado.
4. Cuentas por pagar con cálculo correcto de saldo.
5. Alertas en Dashboard de órdenes pendientes y vencidas.
6. Comprobantes y evidencia de cancelación.
7. Auditoría de acciones relevantes.

---

## 3. Posibles mejoras

### 3.1 Trazabilidad Inventario ↔ OC (prioridad media)

**Situación:** El movimiento de inventario usa `referencia="OC-{id}"` pero no tiene FK a la orden.

**Sugerencia:** Añadir `id_orden_compra` opcional en `movimientos_inventario` para:

- Consultas directas OC → movimientos.
- Reportes de compras por OC sin parsear texto.

**Alternativa:** Mantener solo referencia; requiere migración y cambios en reportes.

---

### 3.2 Proveedor en movimientos de recepción (prioridad media)

**Situación:** En `recibir_mercancia` no se envía `id_proveedor` al crear el movimiento.

**Sugerencia:** Pasar `id_proveedor=oc.id_proveedor` en `MovimientoInventarioCreate` para:

- Trazabilidad en Kardex y reportes.
- Estadísticas de compras por proveedor.

**Cambio:** Una línea en `ordenes_compra.py` al crear el movimiento.

---

### 3.3 Dashboard – Saldo pendiente a proveedores (prioridad alta)

**Situación:** Hay alertas de órdenes sin recibir, pero no saldo total a proveedores.

**Sugerencia:** Tarjeta en Dashboard:

- **"Saldo pendiente proveedores"** con total de cuentas por pagar.
- Enlace a Cuentas por pagar.

**Beneficio:** Visión rápida del pasivo con proveedores.

---

### 3.4 Proveedores – Saldo por proveedor (prioridad media)

**Situación:** La lista de proveedores no muestra saldo pendiente ni historial de OC.

**Sugerencia:**

- Columna opcional "Saldo pendiente" en listado.
- O enlace "Ver cuentas por pagar" filtrado por proveedor.

**Beneficio:** Identificar rápidamente qué proveedores tienen saldo pendiente.

---

### 3.5 Caja y pagos a proveedores (prioridad media-alta)

**Situación:** Los pagos de OC se registran en `pagos_orden_compra` pero no en Caja.

**Impacto:** 

- Caja no refleja egresos por pagos a proveedores.
- Dificulta cuadre de efectivo por turno.
- Impacta flujo de caja real.

**Sugerencia (fase 1 – ligera):**

- Si el método es EFECTIVO y hay turno abierto, vincular el pago al turno (ej. `id_turno` en `PagoOrdenCompra` o tabla de movimientos de caja).
- En el cierre de turno, incluir pagos a proveedores como egresos.

**Sugerencia (fase 2 – más completa):**

- Modelo de movimientos de caja: ingresos (ventas) y egresos (gastos, pagos proveedores).
- Integración de PagoOrdenCompra con movimientos de caja cuando el método sea EFECTIVO.

---

### 3.6 Gastos vs pagos OC (prioridad baja)

**Situación:** Gastos operativos (renta, servicios) y pagos OC son conceptos distintos y están bien separados.

**Opcional:** Un reporte "Egresos del mes" que combine:

- Gastos operativos.
- Pagos a proveedores (OC).

Para una visión unificada de egresos sin mezclar conceptos.

---

### 3.7 EntradaInventario vs OC (prioridad baja)

**Situación:** Entrada manual (EntradaInventario) y recepción por OC son flujos separados. No hay duplicación si se usan bien.

**Recomendación:**

- Mantener ambos flujos.
- En la UI, aclarar que EntradaInventario es para compras directas (sin OC).
- Opcional: en EntradaInventario, permitir seleccionar OC pendiente de recibir para “recibir” desde ahí, evitando dos pantallas para el mismo caso (solo si simplifica el uso real).

---

### 3.8 Reportes y exportaciones (prioridad media)

**Sugerencias:**

- Exportar órdenes de compra (listado completo con filtros).
- Reporte "Compras por periodo" (OC recibidas, totales por proveedor).
- Reporte "Historial de pagos a proveedores" por periodo.

---

### 3.9 Validaciones adicionales (prioridad baja)

- Al desactivar proveedor: avisar si tiene OC pendientes o saldo por pagar.
- Al eliminar/desactivar repuesto: revisar si está en OC BORRADOR/ENVIADA.
- Límite de monto en pagos (ej. no superar el saldo en más de X).

---

## 4. Impacto en otros módulos

| Cambio | Módulos afectados |
|--------|-------------------|
| `id_orden_compra` en movimientos | Inventario, reportes, Kardex |
| `id_proveedor` en movimientos OC | Inventario, reportes |
| Saldo pendiente en Dashboard | Dashboard, API cuentas-por-pagar |
| Saldo por proveedor | Proveedores, API cuentas-por-pagar |
| Caja + pagos OC | Caja, PagoOrdenCompra, reportes caja |
| Exportar OC | Exportaciones, frontend OC |

---

## 5. Priorización sugerida

| # | Mejora | Esfuerzo | Impacto |
|---|--------|----------|---------|
| 1 | Saldo pendiente proveedores en Dashboard | Bajo | Alto |
| 2 | `id_proveedor` en movimientos de recepción | Muy bajo | Medio |
| 3 | Saldo por proveedor en Proveedores | Medio | Medio |
| 4 | Integración Caja – pagos OC (EFECTIVO) | Medio-Alto | Alto |
| 5 | `id_orden_compra` en movimientos | Medio (migración) | Medio |
| 6 | Exportar listado OC | Bajo | Medio |
| 7 | Reporte compras por periodo | Medio | Medio |
| 8 | Validación proveedor con OC/saldo | Bajo | Bajo |

---

## 6. Conclusión

El módulo de Órdenes de Compra está bien diseñado y alineado con Inventario. Las principales oportunidades son:

1. **Dashboard:** Incluir saldo pendiente a proveedores.
2. **Trazabilidad:** Pasar `id_proveedor` en movimientos de recepción.
3. **Proveedores:** Mostrar saldo pendiente por proveedor.
4. **Caja:** Integrar pagos en efectivo a proveedores para un mejor control de flujo de caja.
5. **Reportes:** Añadir exportación de OC y reporte de compras por periodo.

Implementar en este orden maximiza el beneficio con el menor esfuerzo.
