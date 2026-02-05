# Análisis Minucioso del Proyecto Medina AutoDiag API

**Fecha:** 29 de enero de 2025  
**Objetivo:** Verificación exhaustiva de cálculos, reglas de negocio, validaciones y consistencia antes de continuar el desarrollo.

---

## 1. BUGS CRÍTICOS ENCONTRADOS

### 1.1 Modelo Pago – Columna duplicada `id_turno`
**Archivo:** `app/models/pago.py`  
**Problema:** La columna `id_turno` está definida dos veces (líneas 32-36 y 60-65). La segunda sobrescribe la primera. Además, la primera FK referencia `caja_turno.id_turno` pero la tabla real es `caja_turnos` (plural).  
**Impacto:** Posible error de FK, y la segunda definición tiene `nullable=True` cuando debería ser `nullable=False`.  
**Acción:** Eliminar la definición duplicada y dejar una sola con `ForeignKey("caja_turnos.id_turno")` y `nullable=False`.

### 1.2 Actualizar venta manual – No se maneja stock ✅ RESUELTO
**Archivo:** `app/routers/ventas.py` – `actualizar_venta`  
**Problema:** Al actualizar una venta manual, se borran y recrean los `DetalleVenta` pero no se devuelven al inventario los productos antiguos ni se descuenta stock de los nuevos productos.  
**Impacto:** Inventario incorrecto tras modificar una venta manual.  
**Solución implementada:**
1. Devolver stock de los `DetalleVenta` tipo PRODUCTO actuales (movimiento ENTRADA) antes de actualizar.
2. Validar que los nuevos productos existan, estén activos y tengan stock suficiente.
3. Después de guardar los nuevos detalles, descontar stock de los productos nuevos (movimiento SALIDA).
4. Solo aplica a ventas manuales (sin `id_orden` vinculado).

### 1.3 Agregar repuesto a orden – Stock no se descuenta ni se valida correctamente
**Archivo:** `app/routers/ordenes_trabajo.py` – `agregar_repuesto_a_orden`  
**Problema:** 
- La verificación de stock solo se hace cuando `orden.estado in ["COMPLETADA"]`, lo cual es poco útil (en COMPLETADA el trabajo ya terminó).
- Cuando se agrega un repuesto a una orden en `EN_PROCESO`, no se descuenta del inventario. El stock solo se descuenta al **iniciar** la orden, por lo que los repuestos añadidos después nunca se restan.  
**Impacto:** Stock inflado; repuestos usados en órdenes no se reflejan en inventario.  
**Acción:**
1. Verificar stock siempre que `cliente_proporciono_refacciones=False` (en PENDIENTE, EN_PROCESO, etc.).
2. Si la orden está EN_PROCESO y el cliente no provee refacciones, registrar movimiento SALIDA al agregar el repuesto.

### 1.4 Órdenes disponibles para vincular – Incluye ventas canceladas
**Archivo:** `app/routers/ventas.py` – `ordenes_disponibles_para_vincular`  
**Problema:** `ids_ocupados` incluye todas las ventas con `id_orden`, incluidas las CANCELADAS. Si una venta fue cancelada, la orden sigue considerándose “ocupada” y no puede vincularse a otra venta.  
**Acción:** Excluir ventas canceladas:  
`filter(Venta.id_orden.isnot(None), Venta.estado != "CANCELADA")`

---

## 2. PROBLEMAS DE LÓGICA / REGLAS DE NEGOCIO

### 2.1 Autorizar orden – Lógica cuando `autorizado=False` ✅ RESUELTO
**Archivo:** `app/routers/ordenes_trabajo.py` – `autorizar_orden_trabajo`  
**Problema:** Si `autorizado=False` (rechazo del cliente), se ponía `orden.estado = ESPERANDO_AUTORIZACION`. El orden ya estaba en ese estado, así que no había avance.  
**Solución implementada:** Rechazo definitivo → la orden pasa a `CANCELADA` con auditoría completa:
- `estado = CANCELADA`
- `motivo_cancelacion` = observaciones del request o "Rechazada por el cliente"
- `fecha_cancelacion`, `id_usuario_cancelacion` registrados

### 2.2 Corte diario de caja – Filtro por turno ✅ RESUELTO
**Archivo:** `app/routers/caja.py` – `corte_diario`  
**Problema:** Se filtran pagos por `id_usuario` y rango de fechas, pero no por `id_turno`. Si el cajero tuvo varios turnos en el día, podrían mezclarse pagos de distintos turnos.  
**Solución implementada:** Se filtra por `Pago.id_turno == turno.id_turno` para pagos y `GastoOperativo.id_turno == turno.id_turno` para gastos. El corte muestra únicamente los datos del turno actual abierto del cajero.

### 2.3 Estadísticas dashboard órdenes (✅ RESUELTO) – “Total facturado”
**Archivo:** `app/routers/ordenes_trabajo.py` – `obtener_estadisticas_dashboard`  
**Problema:** `total_facturado` suma el total de órdenes COMPLETADA y ENTREGADA. Eso refleja trabajo realizado, no ventas facturadas. Lo realmente facturado está en `Venta`.  
**Solución implementada:** `total_facturado` ahora suma `Venta.total` de ventas vinculadas a órdenes (no canceladas). Refleja lo realmente cobrado/facturado.

---

## 3. VALIDACIONES FALTANTES

### 3.1 Orden de trabajo
- **Fecha promesa vs fecha ingreso:** No se valida que `fecha_promesa >= fecha_ingreso`.
- **Descuento vs total:** No se valida que `descuento <= (subtotal_servicios + subtotal_repuestos)`.
- **Eliminar orden:** No se verifica si existe venta vinculada antes de eliminar una orden cancelada (puede dejar ventas huérfanas).

### 3.2 Ventas
- **Actualizar venta:** No se valida que los repuestos en los nuevos detalles existan y estén activos.
- **Total < total pagado:** En `actualizar_venta` ya existe validación correcta para evitar que el total sea menor que lo pagado.

### 3.3 Órdenes de compra
- **Cancelar OC en RECIBIDA/RECIBIDA_PARCIAL:** Actualmente no está permitido; si se decide permitir, habría que definir qué pasa con la mercancía y los pagos.
- **Recibir más de lo solicitado:** Se valida correctamente que no se reciba más de lo pendiente.

### 3.4 Inventario
- **Ajuste de inventario:** El motivo tiene `min_length=10`; está bien para auditoría.
- **Stock negativo:** `InventarioService` ya valida y evita stock negativo en SALIDA/AJUSTE-/MERMA.

---

## 4. CÁLCULOS VERIFICADOS

| Módulo        | Cálculo                    | Estado | Notas                                                                 |
|---------------|----------------------------|--------|-----------------------------------------------------------------------|
| Orden trabajo | Subtotal detalle           | OK     | `(precio × cantidad) - descuento` en `calcular_subtotal()`            |
| Orden trabajo | Total orden                | OK     | `(sub_servicios + sub_repuestos) - descuento` en `calcular_total()`   |
| Venta         | Subtotal línea             | OK     | `cantidad × precio_unitario` con `money_round`                        |
| Venta         | IVA (8%)                   | OK     | `IVA_FACTOR = 1.08` desde `config.py`                                |
| Reporte utilidad | Ingresos - CMV          | OK     | Usa movimientos SALIDA y `costo_total`                                |
| Cuentas pagar | Total a pagar OC           | OK     | `cantidad_recibida × precio_real_o_estimado`                          |
| Cuentas cobrar| Saldo venta                | OK     | `total - SUM(pagos)`                                                  |
| Inventario    | CPP (costo promedio)       | OK     | En `InventarioService.registrar_movimiento` para ENTRADA              |

---

## 5. MÓDULOS INCOMPLETOS O EN DESARROLLO

| Módulo           | Estado                  | Comentarios                                                       |
|------------------|-------------------------|-------------------------------------------------------------------|
| Órdenes de compra (frontend) | En desarrollo | Página muestra “Módulo en desarrollo”; sin CRUD ni cancelación   |
| ESA estado       | Parcial                 | Estado ESPERANDO_REPUESTOS definido pero no hay flujo explícito  |

---

## 6. CONSISTENCIA Y FLUJOS

### 6.1 Flujo orden → venta → pago
- Stock se descuenta al **iniciar** la orden (correcto).
- La venta desde orden copia total y detalles (correcto).
- Al cancelar venta se devuelve stock (correcto).
- Pagos requieren turno abierto (correcto).

### 6.2 Flujo cancelación
- **Orden:** Registra motivo, fecha, usuario (OK).
- **Venta:** Registra motivo, fecha, usuario (OK).
- **OC:** Registra motivo, fecha, usuario (OK).
- Cancelar orden no cancela automáticamente la venta asociada; solo se impide cancelar órdenes ENTREGADAS (correcto por diseño).

### 6.3 Roles
- ADMIN, CAJA, TECNICO, EMPLEADO definidos de forma consistente.
- `crear_venta` (manual) permite ADMIN y EMPLEADO pero no CAJA; `crear_venta_desde_orden` sí incluye CAJA (posible decisión de negocio).

---

## 7. RESUMEN DE ACCIONES PRIORITARIAS

| # | Prioridad  | Acción                                              | Archivo(s)                    |
|---|------------|-----------------------------------------------------|-------------------------------|
| 1 | Crítica    | Corregir modelo Pago (eliminar `id_turno` duplicado)| `app/models/pago.py`          |
| 2 | Crítica    | Manejar stock en `actualizar_venta`                 | `app/routers/ventas.py`       |
| 3 | Crítica    | Validar y descontar stock en `agregar_repuesto_a_orden` | `app/routers/ordenes_trabajo.py` |
| 4 | Alta       | Excluir ventas canceladas en `ordenes_disponibles`  | `app/routers/ventas.py`       |
| 5 | Media      | Usar `id_turno` en corte diario de caja             | `app/routers/caja.py`         |
| 6 | Media      | ~~Definir flujo para orden rechazada~~ ✅ Rechazo → CANCELADA | `app/routers/ordenes_trabajo.py` |
| 7 | Baja       | Validar `fecha_promesa >= fecha_ingreso`            | Creación/actualización orden  |
| 8 | Baja       | Revisar que el total no sea menor que descuento     | Orden de trabajo              |

---

## 8. DOBLE VERIFICACIÓN POR MÓDULO

### Órdenes de trabajo
- Crear, listar, obtener: OK.
- Actualizar (PENDIENTE): OK, incluye servicios/repuestos.
- Iniciar: descuenta stock, asigna técnico, transición de estado correcta.
- Finalizar: transición correcta, sin doble descuento.
- Entregar: transición correcta.
- Cancelar: auditoría y devolución de repuestos (cuando aplica) correctas.
- Agregar/quitar servicios: recálculo de totales OK.
- Agregar/quitar repuestos: **BUG** en stock (ver 1.3).
- Autorizar: rechazo pasa a CANCELADA con auditoría (ver 2.1, resuelto).
- Eliminar (solo CANCELADA): OK; falta validar ventas vinculadas.

### Ventas
- Listar, obtener, crear manual, crear desde orden: OK.
- Actualizar: **BUG** con stock (ver 1.2).
- Cancelar: devolución de stock y auditoría OK.
- Vincular orden: OK; ordenes_disponibles con bug (ver 1.4).
- Reportes: productos más vendidos, clientes frecuentes, cuentas por cobrar, utilidad: OK.
- Ticket PDF: OK.

### Órdenes de compra
- CRUD, enviar, recibir, pagar, cancelar: OK.
- Auditoría de cancelación: OK.
- Cuentas por pagar: OK.

### Inventario
- Registrar movimiento, ajuste, alertas, valor inventario: OK.

### Caja
- Abrir/cerrar turno, corte diario, historial: OK.
- Corte diario: recomendar filtrar por `id_turno` (ver 2.2).

### Pagos
- Requiere turno abierto: OK.
- Modelo Pago: **BUG** por columna duplicada (ver 1.1).

---

*Documento generado como parte de la verificación del proyecto antes de continuar el desarrollo.*
