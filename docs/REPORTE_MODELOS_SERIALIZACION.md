# Reporte: Modelos, Serialización y Atributos

**Fecha:** 2025-02-18  
**Alcance:** `app/models/`, `app/routers/`, `app/services/`

---

## 1. Columnas por modelo (activo, eliminado, serialización)

### Modelos CON columna `activo`

| Modelo | Columnas clave |
|--------|----------------|
| Bodega | id, nombre, descripcion, **activo**, creado_en |
| CategoriaServicio | id, nombre, descripcion, **activo**, creado_en |
| Ubicacion | id, id_bodega, codigo, nombre, **activo**, creado_en |
| Estante | id, id_ubicacion, codigo, nombre, **activo**, creado_en |
| Nivel | id, codigo, nombre, **activo**, creado_en |
| Fila | id, codigo, nombre, **activo**, creado_en |
| Usuario | id_usuario, nombre, email, **activo**, rol, ... |
| Repuesto | id_repuesto, codigo, nombre, **activo**, **eliminado**, ... |
| Proveedor | id_proveedor, nombre, **activo**, ... |
| Servicio | id, codigo, nombre, **activo**, ... |
| ConfiguracionComision | id, id_usuario, tipo_base, **activo**, ... |

### Modelos SIN columna `activo`

| Modelo | Columnas relevantes |
|--------|---------------------|
| **CategoriaRepuesto** | id_categoria, nombre, descripcion, creado_en |
| Festivo | id, fecha, nombre, anio |
| Cliente | id_cliente, nombre, telefono, email, ... |
| Vehiculo | id_vehiculo, id_cliente, marca, modelo, anio, ... |
| CatalogoVehiculo | id, anio, marca, modelo, version_trim, motor, vin |
| UsuarioBodega | id_usuario, id_bodega (PK compuesta) |
| AlertaInventario | id_alerta, **activa** (femenino, no activo) |
| Venta, DetalleVenta, OrdenTrabajo, OrdenCompra | (modelos transaccionales sin activo) |
| Pago, GastoOperativo, CajaTurno, CuentaPagarManual | (sin activo) |
| Cita, MovimientoInventario, Auditoria, PrestamoEmpleado | (sin activo) |

### Modelos CON columna `eliminado`

| Modelo | Notas |
|--------|-------|
| Repuesto | eliminado, fecha_eliminacion, motivo_eliminacion |

Otros modelos no usan soft-delete con columna `eliminado`.

---

## 2. configuracion_catalogos: verificación de serialización

| Modelo | Campos serializados | ¿Existen en modelo? |
|--------|--------------------|----------------------|
| Bodega | id, nombre, activo | ✓ |
| CategoriaServicio | id, nombre, descripcion, activo | ✓ |
| **CategoriaRepuesto** | id_categoria, nombre, descripcion | ✓ (activo omitido intencionalmente) |
| Ubicacion | id, codigo, nombre, id_bodega, activo | ✓ |
| Estante | id, codigo, nombre, id_ubicacion, activo | ✓ |
| Nivel | id, codigo, nombre, activo | ✓ |
| Fila | id, codigo, nombre, activo | ✓ |
| Usuario | id_usuario, nombre, email, rol, activo | ✓ |
| Festivo | id, fecha, nombre, anio | ✓ |

**CategoriaRepuesto** ya está corregido: no se serializa `activo` (líneas 53-56 en `configuracion_catalogos.py`).

---

## 3. Modelos sin `activo` usados con `.activo`

**No hay casos detectados.** CategoriaRepuesto fue el único candidato y ya está corregido.

---

## 4. Patrones peligrosos y posibles AttributeError

### 4.1 Uso seguro de `getattr` para atributos opcionales

- ` ventas_service.py` líneas 320, 500, 559: `getattr(rep, "eliminado", False)` ✓
- `exportaciones.py` línea 255: `getattr(r, "eliminado", False)` ✓
- `ordenes_compra.py` líneas 166, 775: `getattr(rep, "eliminado", False)` ✓

### 4.2 Acceso directo a atributos en serialización

| Ubicación | Modelo | Campo | ¿Existe? |
|-----------|--------|-------|----------|
| ventas/reportes.py:80 | Query (DetalleVenta agregado) | r.monto | ✓ (alias de `func.sum(subtotal)`) |
| inventario_reportes:432 | Repuesto | producto.nombre | ✓ |
| inventario_reportes:493 | Query (Repuesto) | venta.nombre | ✓ (variable es resultado de query con Repuesto.nombre) |
| caja.py:296 | GastoOperativo | g.categoria | ✓ (Enum) |

### 4.3 Nomenclatura inconsistente: `activa` vs `activo`

- **AlertaInventario** usa `activa` (femenino).
- El código usa correctamente `AlertaInventario.activa` y `a.activa` en notificaciones, inventario_reportes, dashboard_agregado.

---

## 5. Otros posibles AttributeError

### 5.1 DetalleRepuestoOrden vs DetalleOrdenCompra

- **DetalleRepuestoOrden** (OrdenTrabajo): `orden_trabajo_id`, `repuesto_id`, `descripcion_libre`, `cliente_provee`.
- **DetalleOrdenCompra** (OrdenCompra): `id_orden_compra`, `id_repuesto`, `nombre_nuevo`, `cantidad_recibida`.

En `ordenes_compra.py:153` se usa `orden.detalles_repuesto` con `OrdenTrabajo`, que es correcto (DetalleRepuestoOrden tiene `cliente_provee`).

### 5.2 Venta: `id_orden` vs relación

- Modelo Venta tiene `id_orden` (FK a ordenes_trabajo).
- Uso en `orden.cliente`, `venta.id_orden` está correcto.

### 5.3 GastoOperativo.categoria

- `categoria` es Enum ("RENTA", "SERVICIOS", etc.). El acceso `g.categoria` es válido; en Excel puede necesitar `.value` si se usa como string (en caja.py:296 se usa directamente; verificar si Excel espera string).

---

## 6. Recomendaciones

### 6.1 Mantener consistencia en configuracion_catalogos

- CategoriaRepuesto: mantener sin `activo` en la serialización.
- Opcional: documentar en el modelo que no tiene `activo` para evitar que se agregue en el futuro.

### 6.2 Considerar agregar `activo` a CategoriaRepuesto (opcional)

Si el negocio requiere desactivar categorías sin borrarlas:

```python
# categoria_repuesto.py
activo = Column(Boolean, default=True, nullable=False)
```

Y migración correspondiente. La serialización actual no lo requiere.

### 6.3 Uso defensivo en serializaciones dinámicas

Para construcciones como `{"activo": obj.activo}` donde el modelo puede variar:

```python
activo = getattr(obj, "activo", None)  # None si no existe
```

Solo necesario si se reutiliza la misma función con modelos heterogéneos.

### 6.4 Estandarizar `activo` vs `activa`

- AlertaInventario usa `activa` por diseño (nombre de columna).
- Mantener como está; no cambiar sin migración de BD. Documentar la diferencia.

### 6.5 Tests de serialización

Añadir tests que:

1. Verifiquen que `GET /configuracion/catalogos` devuelve JSON sin AttributeError.
2. Verifiquen que cada modelo serializado en ese endpoint tiene los campos usados.

---

## 7. Resumen ejecutivo

| ítem | estado |
|------|--------|
| Modelos sin `activo` usados con `.activo` | **0** (CategoriaRepuesto ya corregido) |
| AttributeError por campos inexistentes | **0** detectados |
| configuracion_catalogos (Festivo, Usuario, etc.) | **OK** - todos los campos existen |
| Uso de `getattr` para `eliminado` | **Correcto** donde se usa |

**Conclusión:** No hay errores críticos de serialización. CategoriaRepuesto ya se trata correctamente sin `activo`. Se recomiendan tests de integración y documentar la excepción de AlertaInventario (`activa` vs `activo`).
