# Plan Comisiones - Fase 0 (Completada)

**Fecha:** 2026-02-18

## Objetivo

Tener los fundamentos de datos para el sistema de comisiones: campo vendedor y tabla de configuración.

## Cambios realizados

### 1. id_vendedor en Venta y OrdenTrabajo

- **Venta**: `id_vendedor` FK a usuarios, nullable.
  - Quien cobra comisión por la venta (vendedor).
  - Por defecto al crear: `id_usuario` (quien registra) si no se especifica.

- **OrdenTrabajo**: `id_vendedor` FK a usuarios, nullable.
  - Quien hizo seguimiento y cobra al concretar la venta.
  - Al crear venta desde OT: se hereda el vendedor de la OT si existe.

### 2. Tabla configuracion_comision

| Campo         | Tipo    | Descripción                                      |
|---------------|---------|--------------------------------------------------|
| id            | PK      | Identificador                                    |
| id_usuario    | FK      | Empleado configurado                             |
| tipo_base     | Enum    | MANO_OBRA, PARTES, SERVICIOS_VENTA, PRODUCTOS_VENTA |
| porcentaje    | Decimal | % 0–100                                          |
| vigencia_desde| Date    | Inicio de vigencia                               |
| vigencia_hasta| Date    | Fin (null = vigente)                             |
| activo        | Boolean | Si se usa en el cálculo                          |

### 3. API actualizada

- **VentaCreate / VentaUpdate**: `id_vendedor` opcional.
- **OrdenTrabajoCreate / OrdenTrabajoBase**: `id_vendedor` opcional.
- **OrdenTrabajoUpdate**: `id_vendedor` opcional.
- Respuestas: `id_vendedor` en venta; `id_vendedor` y `vendedor` (nombre) en orden.

### 4. Migraciones

- `x4y5z6a7b8c9`: add id_vendedor a ventas y ordenes_trabajo
- `y5z6a7b8c9d0`: add configuracion_comision

## Fase 1 (Completada — 2026-02-18)

- ✅ CRUD de configuración de comisiones: GET, POST, PUT `/configuracion/comisiones`
- ✅ UI en Configuración tab "Comisiones": tabla, modal nueva config, modal cambiar %
- ✅ Campo vendedor en formularios de Venta (crear/editar) y OT (NuevaOrdenTrabajo paso 2, OrdenesTrabajo editar)

## Fase 2 (Completada — 2026-02-18)

- ✅ Tabla `comisiones_devengadas`: id_usuario, id_venta, tipo_base, base_monto, porcentaje, monto_comision, fecha_venta.
- ✅ Cálculo al pagar: cuando una venta pasa a PAGADA (pagos.py), se llama `calcular_y_registrar_comisiones()`.
- ✅ Mapeo tipo: SERVICIO+id_orden_origen→MANO_OBRA (técnico), PRODUCTO+id_orden_origen→PARTES (técnico), SERVICIO sin orden→SERVICIOS_VENTA (vendedor), PRODUCTO sin orden→PRODUCTOS_VENTA (vendedor).
- ✅ API `GET /ventas/reportes/comisiones`: por fecha_desde, fecha_hasta, id_usuario. Rol ADMIN, CAJA.
- ✅ UI: bloque "Comisiones devengadas" en Ventas → Reportes (solo ADMIN/CAJA).
