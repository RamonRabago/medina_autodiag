# Auditoría: Campos faltantes en endpoints (información no persistida/visible)

## Problema identificado

En el endpoint `/configuracion/catalogos` se construían respuestas manualmente con diccionarios que **omitían campos** existentes en los modelos. Esto provocaba:

1. **Tabla**: mostrar "-" en columnas (ej. descripción)
2. **Modal editar**: formulario con campos vacíos al cargar datos guardados
3. ** percepción del usuario**: "no se guarda" (aunque sí se guarda en BD; solo no se devuelve ni muestra)

## Correcciones aplicadas

### Bodegas
- **Antes**: `id`, `nombre`, `activo` (sin `descripcion`)
- **Después**: `id`, `nombre`, `descripcion`, `activo`

### Ubicaciones
- **Antes**: `id`, `codigo`, `nombre`, `id_bodega`, `activo` (sin `descripcion`, sin `bodega_nombre`)
- **Después**: `id`, `codigo`, `nombre`, `id_bodega`, `descripcion`, `activo`, `bodega_nombre`
- Se usa `joinedload(Ubicacion.bodega)` para resolver el nombre de la bodega sin N+1.

### Estantes
- **Antes**: `id`, `codigo`, `nombre`, `id_ubicacion`, `activo` (sin `descripcion`, sin `bodega_nombre`, sin `ubicacion_nombre`)
- **Después**: `id`, `codigo`, `nombre`, `id_ubicacion`, `descripcion`, `activo`, `bodega_nombre`, `ubicacion_nombre`
- Se usa `joinedload(Estante.ubicacion).joinedload(Ubicacion.bodega)` para los nombres derivados.

## Entidades ya correctas (no requirieron cambios)

- **categorias_servicios**: incluye `descripcion`
- **categorias_repuestos**: incluye `descripcion`
- **niveles, filas**: no tienen campo `descripcion` en el modelo
- **usuarios**: incluye salario_base, bono_puntualidad, periodo_pago
- **festivos**: incluye todos los campos usados

## Endpoints que usan ORM/Schemas (no manuales)

Los routers individuales (`/bodegas/`, `/ubicaciones/`, `/estantes/`, etc.) usan schemas Pydantic con `from_attributes=True`, por lo que devuelven todos los campos del modelo. No presentan este problema.

## Recomendación futura

Al agregar nuevos catálogos o endpoints que devuelvan listas con diccionarios manuales, verificar que se incluyan todos los campos que el frontend muestra o edita.
