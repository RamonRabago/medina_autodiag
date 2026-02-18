# Análisis: Comisiones y Coherencia del Módulo

**Fecha:** 2026-02-18  
**Alcance:** comisiones, configuracion_comision, scripts, exportaciones, auditoría, ventas.

---

## 1. Flujo general (OK)

| Componente | Función | Estado |
|-------------|---------|--------|
| `pagos.py` | Al liquidar venta → PAGADA, llama `calcular_y_registrar_comisiones()` | ✅ |
| `comisiones_service.py` | Calcula y registra en `comisiones_devengadas` | ✅ |
| `ventas_service.cancelar_venta` | Elimina registros de comisión al cancelar | ✅ |
| `exportaciones.py` | Exporta comisiones a Excel (filtro por rol) | ✅ |
| `ventas/reportes.py` | Reporte comisiones por período | ✅ |
| `prestamos_empleados.py` | `mi-resumen` incluye `comisiones_periodo` | ✅ |

---

## 2. Errores o incoherencias detectados

### 2.1 🔴 Bug crítico: `actualizar_venta` pierde `id_orden_origen` en detalles

**Archivo:** `app/services/ventas_service.py` (líneas 575-586)

Al actualizar una venta vinculada a orden de trabajo, se borran los `DetalleVenta` y se recrean desde `data.detalles`. Los nuevos detalles **no incluyen `id_orden_origen`**.

**Consecuencia:** SERVICIO/PRODUCTO que venían de OT (MANO_OBRA/PARTES → técnico) pasan a SERVICIOS_VENTA/PRODUCTOS_VENTA (vendedor). El técnico pierde la comisión y el vendedor la cobraría.

**Solución:** Al recrear detalles, si `venta.id_orden` existe, asignar `id_orden_origen=venta.id_orden` en cada DetalleVenta nuevo.

```python
# En actualizar_venta, al crear DetalleVenta:
id_ord = getattr(venta, "id_orden", None) if venta else None
db.add(DetalleVenta(
    ...
    id_orden_origen=id_ord,  # preservar para ventas con OT vinculada
))
```

---

### 2.2 Inconsistencia docstring vs código: vigencia de configuraciones

**Archivo:** `app/routers/configuracion_comisiones.py` (líneas 88-90, 108-109)

**Docstring:** "se cierra primero (vigencia_hasta = vigencia_desde - 1 día)"  
**Código:** `v.vigencia_hasta = vigencia_desde` (sin restar 1 día)

Hay superposición el mismo día: ambas configs son válidas. El `order_by(vigencia_desde.desc())` en `_obtener_porcentaje` hace que se tome la nueva. **Funciona pero es frágil**.

**Recomendación:** Aplicar `vigencia_hasta = vigencia_desde - timedelta(days=1)` para evitar ambigüedad.

---

### 2.3 Auditoría: sin enlace para CONFIGURACION_COMISION

**Archivo:** `frontend/src/pages/Auditoria.jsx`

`enlaceReferencia()` no tiene caso para `CONFIGURACION_COMISION`. Los registros de auditoría de comisiones no muestran link a la sección de configuración.

**Solución sugerida:**
```javascript
if (mod === 'CONFIGURACION_COMISION' && id) return { to: '/configuracion?tab=comisiones', label: 'Ver configuración comisiones' }
```

---

### 2.4 Exportación auditoría: descripción cruda

**Archivo:** `app/routers/exportaciones.py` (línea 881)

La columna "Descripción" exporta `r.descripcion` tal cual (str del dict). Para CONFIGURACION_COMISION ya usamos `empleado` en lugar de `id_usuario`, así que el Excel mostrará texto legible. Sin cambio urgente.

---

## 3. Coherencia entre módulos

### 3.1 Tipos base (OK)

- `ConfiguracionComision`: MANO_OBRA, PARTES, SERVICIOS_VENTA, PRODUCTOS_VENTA  
- `ComisionDevengada`: mismos valores (`TIPOS_BASE_CD`)  
- `comisiones_service._obtener_tipo_base`: mapea correctamente.

### 3.2 Usuarios que cobran (OK)

- MANO_OBRA, PARTES → `orden.tecnico_id`
- SERVICIOS_VENTA, PRODUCTOS_VENTA → `venta.id_vendedor`
- `id_vendedor` se asigna por defecto al crear venta manual o desde OT.

### 3.3 Vigencia (atención)

- `_obtener_porcentaje` usa `vigencia_desde <= fecha` y `(vigencia_hasta IS NULL OR vigencia_hasta >= fecha)`.
- Coincide con la lógica actual de abrir/cerrar configuraciones.

---

## 4. Scripts y pruebas

| Script | Estado |
|--------|--------|
| `scripts/test_comisiones_nomina.py` | ✅ Cubre imports, mapeo tipo_base, rutas, fórmula |
| `scripts/ejecutar_todas_pruebas.py` | ✅ Incluye test_comisiones_nomina |
| `tests/test_comisiones_nomina.py` | ✅ Pytest: tipo_base, quien_cobra, fórmula, rutas |

**Posible mejora:** Añadir test de integración que:
- Cree venta PAGADA con detalle SERVICIO + id_orden_origen
- Verifique que `ComisionDevengada` tiene tipo_base=MANO_OBRA y monto correcto  
(requiere DB y fixtures).

---

## 5. Posibles mejoras (no urgentes)

1. **Validación al crear config:** Impedir `vigencia_desde` anterior a hoy si se desea solo fechas futuras (opcional según negocio).
2. **Reporte comisiones:** Incluir desglose por tipo_base (MANO_OBRA, PARTES, etc.) además del total por empleado.
3. **Frontend Configuracion comisiones:** Mostrar también configuraciones históricas (solo vigentes por defecto) con toggle "Incluir históricas".

---

## 6. Resumen de acciones recomendadas

| Prioridad | Acción | Estado |
|-----------|--------|--------|
| ~~Alta~~ | Corregir `actualizar_venta` para preservar `id_orden_origen` en detalles | ✅ Hecho |
| ~~Media~~ | Ajustar `vigencia_hasta = vigencia_desde - 1 día` al cerrar config previa | ✅ Hecho |
| ~~Baja~~ | Añadir enlace CONFIGURACION_COMISION en Auditoría.jsx | ✅ Hecho |
| Opcional | Tests de integración de comisiones con DB | Pendiente |
