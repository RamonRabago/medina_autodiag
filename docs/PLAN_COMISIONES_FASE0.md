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

## Siguiente fase (Fase 1)

- CRUD de configuración de comisiones
- UI en Configuración para editar % por empleado
- Campo vendedor en formularios de Venta y OT
