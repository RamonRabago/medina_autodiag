# Análisis del Módulo de Ventas (actualizado)

**Fecha:** Febrero 2026

---

## 1. Resumen ejecutivo

El módulo de ventas está bien integrado con órdenes de trabajo, inventario, caja y pagos. La lógica de negocio es coherente. Se identifican mejoras de permisos, UX y robustez. El bug de PAGADA con saldo pendiente ya fue corregido (auto-ajuste a PENDIENTE al editar).

---

## 2. Estructura del módulo

| Componente | Ubicación | Rol |
|------------|-----------|-----|
| Modelos | `venta.py`, `detalle_venta.py`, `pago.py` | Venta, DetalleVenta, Pago |
| Servicio | `ventas_service.py` | Crear, actualizar, cancelar, vincular, auto PENDIENTE |
| Routers | `ventas/crud.py`, `acciones.py`, `reportes.py`, `ticket.py` | API REST |
| Pagos | `pagos.py` | Registrar pagos (requiere turno caja del usuario) |

---

## 3. Hallazgos y recomendaciones

### 3.1 Permisos: Crear venta manual

**Situación:** `POST /ventas/` (crear venta manual) solo permite roles **ADMIN** y **EMPLEADO**. **CAJA** y **TECNICO** no pueden crear.

**Impacto:** El botón "Nueva venta" se muestra a todos los usuarios (incl. CAJA). Si CAJA intenta crear una venta manual, recibe 403.

**Recomendación:** Incluir CAJA en `crear_venta` si en el negocio la caja registra ventas manuales (contraventa, refacciones sueltas). Alternativa: ocultar "Nueva venta" para CAJA/TECNICO en el frontend.

**Archivo:** `app/routers/ventas/crud.py` línea 173.

---

### 3.2 Pagos: Turno del usuario actual

**Situación:** Para registrar un pago, el turno de caja debe estar abierto **y** pertenecer al usuario actual (`CajaTurno.id_usuario == current_user.id_usuario`).

**Impacto:** Si el usuario A abre el turno y el usuario B (CAJA) intenta registrar un pago, recibe "No puedes registrar pagos sin un turno de caja abierto". En equipos con varios cajeros, solo quien abrió puede cobrar.

**Recomendación:** Valorar si el turno debe ser compartido (cualquier CAJA puede cobrar) o si es intencional que solo quien abre cobre. Si es compartido, relajar la condición a "existe turno ABIERTO" sin filtrar por usuario.

**Archivo:** `app/routers/pagos.py` líneas 29-32.

---

### 3.3 VentasIngresos: TECNICO sin acceso

**Situación:** VentasIngresos (`/ventas/ingresos`) solo permite ADMIN, CAJA, EMPLEADO. **TECNICO** no puede ver la página.

**Impacto:** Coherente si los técnicos no necesitan ver detalle de ingresos. El listado de ventas sí permite TECNICO.

---

### 3.4 Reportes: Fechas vacías

**Situación:** En la pestaña Reportes, si no se seleccionan fechas, `filtrosReportes` tiene `fecha_desde` y `fecha_hasta` vacíos. Las APIs de reportes aceptan params opcionales; sin fechas devuelven todo el histórico.

**Impacto:** Puede ser lento con muchos datos. Considerar valores por defecto (ej. mes actual) o aviso al usuario.

---

### 3.5 Cancelación: productos con cantidad decimal

**Situación:** En `actualizarProductoCancelacion`, se usa `aEntero` para `cantidad_reutilizable` y `cantidad_mer`. Si el producto tiene `cantidad` decimal (ej. 2.5 L), el redondeo a entero podría no coincidir.

**Verificación:** El schema `DetalleVentaCreate` permite `cantidad: Decimal` con decimales. La cancelación usa `aEntero` en el frontend. El backend espera `cantidad_reutilizable` y `cantidad_mer` como Decimal. Revisar si hay productos con cantidad decimal en ventas.

---

### 3.6 Desvincular orden: no refresca lista

**Situación:** Tras `desvincularOrden`, se actualiza `ventaDetalle` pero no se llama `cargar()`. La lista de ventas no se refresca.

**Impacto:** Bajo. El detalle sí se actualiza.

---

### 3.7 Crear venta: sin feedback de éxito

**Situación:** En `handleSubmit` (crear venta), tras éxito no hay `showSuccess`. El usuario no recibe confirmación explícita.

**Recomendación:** Añadir `showSuccess('Venta creada')` tras crear correctamente.

---

## 4. Verificación de flujos

| Flujo | Estado |
|-------|--------|
| Crear venta manual | ✓ Descuenta stock |
| Crear venta desde orden | ✓ No toca inventario (ya descontado) |
| Editar venta PAGADA con saldo | ✓ Auto PENDIENTE (corregido) |
| Vincular/desvincular orden | ✓ |
| Cancelar con productos | ✓ Reutilizable/Merma |
| Registrar pago | ✓ Requiere turno, actualiza estado |
| Reporte utilidad | ✓ Fórmula correcta |
| Ticket PDF | ✓ Sin ENTREGA, sin PAGADO COMPROBANTE |

---

## 5. Mejoras priorizadas

| Prioridad | Acción |
|-----------|--------|
| Media | Incluir CAJA en crear_venta o ocultar botón para CAJA/TECNICO |
| Media | Añadir showSuccess al crear venta |
| Baja | Valorar turno compartido para pagos (varios cajeros) |
| Baja | Fechas por defecto en reportes (mes actual) |
| Baja | Refrescar lista tras desvincular orden |

---

## 6. Conclusión

El módulo es sólido. Las mejoras son sobre permisos, UX y casos de uso multi-usuario. No se detectaron errores críticos de cálculo o integridad de datos.
