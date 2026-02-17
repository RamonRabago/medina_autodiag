# Análisis del módulo Dashboard

**Fecha:** Febrero 2026

---

## 1. Resumen ejecutivo

El Dashboard muestra métricas clave según el rol del usuario. ADMIN y CAJA ven el panel completo; TÉCNICO ve solo Clientes y Órdenes. El análisis identifica 1 bug relevante, varias mejoras posibles y confirma que la mayoría de integraciones funcionan correctamente.

---

## 2. APIs consumidas

| API | Rol | Uso |
|-----|-----|-----|
| GET /clientes/ | Todos | Total clientes |
| GET /ordenes-trabajo/ | Todos | Total órdenes |
| GET /ordenes-trabajo/estadisticas/dashboard | ADMIN, CAJA | Ventas del periodo, cobrado, órdenes hoy, urgentes, por estado |
| GET /inventario/reportes/dashboard | ADMIN, CAJA | Valor inventario, productos activos, stock bajo/sin stock, alertas |
| GET /ordenes-compra/alertas | ADMIN, CAJA | Órdenes sin recibir, vencidas |
| GET /ordenes-compra/cuentas-por-pagar | ADMIN, CAJA | Saldo OC a proveedores |
| GET /cuentas-pagar-manuales | ADMIN, CAJA | Saldo cuentas manuales |
| GET /caja/turno-actual | ADMIN, CAJA | Estado turno caja |
| GET /gastos/resumen | ADMIN, CAJA | Total gastos del mes |
| GET /ventas/reportes/utilidad | ADMIN, CAJA | Utilidad neta |
| GET /citas/dashboard/proximas | ADMIN, CAJA | Citas próximas |
| GET /devoluciones/ | ADMIN, CAJA | Devoluciones del mes |
| GET /admin/dashboard/resumen | ADMIN | Alertas pendientes/críticas |

---

## 3. Bug identificado

### 3.1 Gastos y utilidad no respetan el período seleccionado

**Problema:** El selector "Ventas del periodo" permite elegir: Este mes, Mes pasado, Este año, Acumulado. Sin embargo:

- **Ventas del periodo** y **Cobrado** sí usan las fechas del período (vía `paramsFacturado` en estadísticas dashboard).
- **Gastos del mes** y **Utilidad neta del mes** siempre usan `mesInicio` y `mesFin` del mes actual, independientemente del selector.

**Impacto:** Si el usuario selecciona "Mes pasado" o "Este año", las tarjetas de Gastos y Utilidad siguen mostrando datos del mes en curso, lo cual es inconsistente.

**Solución recomendada:** Usar `getRangoPeriodo(periodoFacturado)` también para las llamadas a `/gastos/resumen` y `/ventas/reportes/utilidad`. Cuando `periodo === 'acumulado'`, pasar sin fechas (o fechas muy amplias) para obtener todo el histórico.

**Archivos a modificar:** `frontend/src/pages/Dashboard.jsx` líneas 52-54.

**Estado:** ✅ Corregido (feb 2026). Gastos y Utilidad usan `paramsGastosUtilidad` derivado de `getRangoPeriodo(periodoFacturado)`. Etiquetas dinámicas según período.

---

## 4. Comportamiento del período "Acumulado"

- `getRangoPeriodo('acumulado')` devuelve `fecha_desde: null, fecha_hasta: null`.
- `paramsFacturado` queda `{}` (objeto vacío).
- La API de estadísticas dashboard recibe sin filtros de fecha → devuelve datos de todo el tiempo. ✓ Correcto.
- Las etiquetas "Suma total de ventas" y "Suma de todos los pagos recibidos" son coherentes.

---

## 5. Posibles mejoras (no críticas)

### 5.1 Evitar doble carga cuando user es null

- **Situación:** El `useEffect` corre con `user?.rol` en las dependencias. Si `user` es `null` al inicio (auth aún cargando), se disparan solo 2 requests (clientes, ordenes). Luego, cuando `user` se carga, se vuelve a ejecutar con el conjunto completo.
- **Mejora:** Incluir `loading` del AuthContext y no ejecutar el fetch principal hasta `!authLoading`. Así se evita una primera ronda de requests innecesaria.

### 5.2 Indicar qué APIs fallaron

- **Situación:** Si alguna API falla, se muestra "Algunos datos no están disponibles (N APIs no respondieron)".
- **Mejora:** Opcionalmente, mostrar cuáles fallaron (ej. en un tooltip o lista colapsable) para facilitar el diagnóstico.

### 5.3 Devoluciones del mes vs período

- La tarjeta "Devoluciones del mes" usa siempre el mes actual. Es coherente con el nombre. Si en el futuro se unifica el criterio de período, habría que añadir filtro por `periodoFacturado`.

---

## 6. Verificación de integraciones

| Integración | Estado | Notas |
|-------------|--------|-------|
| Valor inventario | ✓ | Usa `valor_compra` del objeto (corregido previamente) |
| Utilidad neta | ✓ | `total_utilidad_neta` o `total_utilidad` |
| Cuentas por pagar | ✓ | Suma OC + manuales correctamente |
| Citas próximas | ✓ | `citas` array, `cliente_nombre`, `fecha_hora` |
| Órdenes por estado | ✓ | Maneja `estado` como string o objeto (Enum) |
| Gastos resumen | ✓ | `total_gastos` |
| Turno caja | ✓ | `estado`, `monto_apertura` |
| Alertas OC | ✓ | `ordenes_sin_recibir`, `ordenes_vencidas` |

---

## 7. Roles y visibilidad

| Rol | Tarjetas visibles |
|-----|-------------------|
| ADMIN | Todo (incl. alertas admin) |
| CAJA | Todo excepto alertas admin |
| TECNICO, EMPLEADO | Solo Clientes y Órdenes de trabajo |

---

## 8. Recomendaciones priorizadas

| Prioridad | Acción |
|-----------|--------|
| Alta | Corregir bug: Gastos y Utilidad deben usar el período seleccionado |
| Media | Considerar no ejecutar fetch hasta `!authLoading` |
| Baja | Mejorar mensaje de errores indicando APIs fallidas |
