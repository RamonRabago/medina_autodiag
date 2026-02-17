# Análisis del Módulo de Órdenes de Compra – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelos, router, schemas, integración con inventario, pagos y frontend.

---

## 1. Resumen ejecutivo

El módulo de órdenes de compra está bien estructurado y cubre el flujo completo:
- Crear OC (directa o desde orden de trabajo)
- Estados: BORRADOR → ENVIADA → AUTORIZADA → RECIBIDA / RECIBIDA_PARCIAL
- Recepción de mercancía con entrada a inventario
- Cuentas por pagar y pagos
- Cancelación con auditoría

Se han identificado **errores** y **mejoras** a partir de la revisión del código y del `ANALISIS_ORDENES_COMPRA.md` existente.

---

## 2. Errores detectados

### 2.1 Críticos

#### E1. Proveedor inactivo al actualizar orden en BORRADOR

**Archivo:** `app/routers/ordenes_compra.py` — `actualizar_orden`, líneas 492-497

**Situación:** En BORRADOR se permite cambiar `id_proveedor`. Se valida que el proveedor exista, pero no que esté activo.

**Impacto:** Se puede asignar un proveedor desactivado a la orden.

**Corrección:**
```python
if v is not None:
    prov = db.query(Proveedor).filter(Proveedor.id_proveedor == v).first()
    if not prov:
        raise HTTPException(404, detail="Proveedor no encontrado")
    if not prov.activo:
        raise HTTPException(400, detail="Proveedor inactivo")
    oc.id_proveedor = v
```

---

#### E2. Repuesto inactivo en crear/agregar items

**Archivo:** `app/routers/ordenes_compra.py` — `crear_orden` y `agregar_items`

**Situación:** Se valida que el repuesto exista y no esté eliminado, pero no que esté activo (`activo=True`).

**Impacto:** Se pueden añadir repuestos desactivados a órdenes de compra.

**Recomendación:** Añadir validación:
```python
if not rep.activo:
    raise HTTPException(400, detail=f"El repuesto '{rep.nombre}' está inactivo")
```

---

### 2.2 Medios

#### E3. Error de renderizado React por `detail` (ya documentado)

**Archivos:** `frontend/src/pages/NuevaOrdenCompra.jsx`, `EditarOrdenCompra.jsx`

**Situación:** Si la API devuelve un array de errores de validación Pydantic, asignar `detail` a `error` y renderizarlo puede provocar: `Objects are not valid as a React child`.

**Recomendación:** Normalizar el mensaje, por ejemplo:
```javascript
const d = err.response?.data?.detail
const msg = typeof d === 'string' ? d : (Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : 'Error al procesar')
setError(msg)
```

---

#### E4. Comparación de precios en recepción

**Archivo:** `app/routers/ordenes_compra.py` — `recibir_mercancia`

**Situación:** El código ya usa `abs(precio_dec - estimado_dec) >= Decimal("0.01")` para decidir si se guarda `precio_unitario_real`. Comportamiento correcto.

---

#### E5. Filtro redundante en cuentas-por-pagar

**Archivo:** `app/routers/ordenes_compra.py` — `listar_cuentas_por_pagar`, líneas 348-356

**Situación:** Se filtra por `OrdenCompra.estado.in_([RECIBIDA, RECIBIDA_PARCIAL])` y además `OrdenCompra.estado != CANCELADA`. La segunda condición es redundante.

**Recomendación:** Eliminar la condición `!= CANCELADA` para simplificar la consulta.

---

### 2.3 Menores

#### E6. Requisito de fecha estimada para recibir

**Archivo:** `app/routers/ordenes_compra.py` — `recibir_mercancia`

**Situación:** Si la orden está AUTORIZADA y no tiene `fecha_estimada_entrega`, se impide recibir mercancía.

**Impacto:** Flujos donde no se usa fecha promesa quedan bloqueados.

**Recomendación:** Valorar si la fecha es obligatoria o solo recomendada. Si es recomendada, cambiar a advertencia en lugar de bloqueo.

---

#### E7. Posible condición de carrera al crear repuesto “PDTE EDITAR”

**Archivo:** `app/routers/ordenes_compra.py` — `recibir_mercancia`

**Situación:** Si `codigo_nuevo` viene vacío, se genera un código tipo "PDTE EDITAR" o "PDTE EDITAR-N" comprobando existencia en un bucle. No se usa bloqueo de fila.

**Impacto:** Dos recepciones simultáneas podrían generar códigos duplicados en condiciones muy concretas.

**Recomendación:** Para mayor robustez, usar `with_for_update()` o un lock al generar el código. Prioridad baja.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Validar proveedor activo en `actualizar_orden`

Ver E1; la validación debe extenderse al cambio de proveedor en BORRADOR.

---

#### M2. Transacción en `recibir_mercancia`

**Situación:** Se crean repuestos nuevos y se registran movimientos en el mismo flujo. Si falla algo intermedio, podría quedar inconsistencia.

**Propuesta:** Envolver el flujo en una transacción y hacer rollback en caso de error.

---

#### M3. Endpoint para estadísticas de OC por proveedor

**Propuesta:** Endpoint tipo `GET /ordenes-compra/estadisticas-proveedor/{id_proveedor}` con total comprado, OC pendientes, saldo, etc.

---

#### M4. Paginación en cuentas-por-pagar

**Situación:** `listar_cuentas_por_pagar` carga todas las órdenes con saldo y luego filtra/ordena en memoria.

**Impacto:** Con muchos registros puede haber problemas de rendimiento.

**Propuesta:** Añadir paginación o límite configurable.

---

### 3.2 Frontend

#### M5. Precio estimado para repuestos “nuevos”

**Archivo:** `NuevaOrdenCompra.jsx`

**Situación:** Para items “nuevo” no se permite ingresar precio estimado; el total es engañoso.

**Propuesta:** Añadir campo de precio opcional para items “nuevo”.

---

#### M6. Normalizar mensajes de error de validación

Aplicar la lógica de E3 en todas las páginas que muestran errores de la API.

---

### 3.3 Documentación

#### M7. Documentar flujo de estados

Documentar claramente las transiciones:
- BORRADOR → ENVIADA (enviar al proveedor)
- ENVIADA → AUTORIZADA (cotización subida)
- AUTORIZADA/RECIBIDA_PARCIAL → recepción parcial/total
- Cancelación solo en BORRADOR, AUTORIZADA, ENVIADA

---

## 4. Flujos verificados

| Flujo | Estado | Detalle |
|-------|--------|---------|
| Crear OC directa | ✅ | Valida proveedor activo, repuestos, vehículo catálogo |
| Crear OC desde orden de trabajo | ✅ | Excluye repuestos con `cliente_provee` |
| Enviar orden | ✅ | Cambia a ENVIADA, envía email si hay configuración |
| Autorizar orden | ✅ | Exige comprobante, cambia a AUTORIZADA |
| Recibir mercancía | ✅ | Crea repuestos nuevos, registra ENTRADA en inventario |
| Registrar pago | ✅ | Valida saldo, vincula turno de caja si efectivo |
| Cancelar orden | ✅ | Solo BORRADOR, AUTORIZADA, ENVIADA |
| Cuentas por pagar | ✅ | Aging por antigüedad |

---

## 5. Integración con otros módulos

| Módulo | Punto de integración |
|--------|----------------------|
| Proveedores | OC requiere proveedor activo al crear; falta validar al actualizar (E1) |
| Repuestos | Validación de existencia y eliminado; falta validar activo (E2) |
| Inventario | `InventarioService.registrar_movimiento` en recepción |
| Caja | `PagoOrdenCompra.id_turno` cuando el pago es en efectivo |
| Órdenes de trabajo | Generación de OC desde OT |
| Auditoría | `registrar_auditoria` en crear, autorizar, recibir, pagar, cancelar |

---

## 6. Checklist de implementación sugerido

**Prioridad alta:**
- [x] E1: Validar proveedor activo al actualizar orden en BORRADOR (corregido)
- [x] E2: Validar repuesto activo al crear/agregar items (corregido; también en generar_oc_desde_orden_trabajo)
- [ ] E3: Normalizar `detail` en NuevaOrdenCompra y EditarOrdenCompra

**Prioridad media:**
- [ ] E5: Eliminar filtro redundante en cuentas-por-pagar
- [ ] M2: Revisar uso de transacciones en `recibir_mercancia`
- [ ] M5: Precio estimado para repuestos nuevos en frontend

**Prioridad baja:**
- [ ] E6: Revisar obligatoriedad de fecha estimada
- [ ] E7: Evaluar lock al generar código "PDTE EDITAR"
- [ ] M4: Paginación en cuentas-por-pagar

---

## 7. Archivos revisados

| Archivo | Rol principal |
|---------|----------------|
| `app/models/orden_compra.py` | OrdenCompra, DetalleOrdenCompra |
| `app/models/pago_orden_compra.py` | PagoOrdenCompra |
| `app/routers/ordenes_compra.py` | Router principal |
| `app/schemas/orden_compra.py` | Schemas Pydantic |
| `frontend/src/pages/OrdenesCompra.jsx` | Listado y acciones |
| `frontend/src/pages/NuevaOrdenCompra.jsx` | Crear OC |
| `frontend/src/pages/EditarOrdenCompra.jsx` | Editar OC |
| `app/services/inventario_service.py` | Entrada de inventario |
| `ANALISIS_ORDENES_COMPRA.md` | Análisis previo (tipos, Decimal) |
