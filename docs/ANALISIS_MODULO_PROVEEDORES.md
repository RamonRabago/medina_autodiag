# Análisis del Módulo de Proveedores – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelo, router, schemas, integración con inventario, órdenes de compra y frontend.

---

## 1. Resumen ejecutivo

El módulo de proveedores es relativamente simple y cubre:
- CRUD completo (crear, listar, obtener, actualizar)
- Soft delete mediante `activo=False` (desactivar / reactivar)
- Validación de teléfono (formato México), email y RFC
- Integración con: repuestos, órdenes de compra, movimientos de inventario, cuentas por pagar manuales

Se han identificado varios **errores potenciales** y **mejoras**.

---

## 2. Errores detectados

### 2.1 Críticos

#### E1. Proveedor no validado en entrada masiva

**Archivo:** `app/routers/movimientos_inventario.py` — `entrada_masiva`

**Situación:** El parámetro `id_proveedor` (Query) se pasa directamente al movimiento sin comprobar que:
- Exista en la base de datos
- Esté activo (`activo=True`)

**Impacto:** Si se envía un `id_proveedor` inexistente o inactivo, se registrarán movimientos con un proveedor inválido (posible violación FK o datos inconsistentes).

**Recomendación:** Validar antes del bucle:
```python
if id_proveedor:
    prov = db.query(Proveedor).filter(
        Proveedor.id_proveedor == id_proveedor,
        Proveedor.activo == True
    ).first()
    if not prov:
        raise HTTPException(400, detail="Proveedor no encontrado o inactivo")
```

---

### 2.2 Medios

#### E2. RFC vacío en `ProveedorUpdate`

**Archivo:** `app/schemas/proveedor.py`

**Situación:** El validador de RFC retorna `v` cuando está vacío (`if v:` → `return v`). Si el frontend envía `rfc: ""`, se devuelve `""` y el `Field(min_length=12)` falla.

**Recomendación:** Normalizar cadenas vacías a `None` en ambos validadores (Create y Update):
```python
if not v or not str(v).strip():
    return None
```

---

#### E3. Sugerencia de compra incluye proveedores inactivos

**Archivo:** `app/routers/inventario_reportes.py` — `listar_sugerencia_compra`

**Situación:** Se agrupan repuestos por `id_proveedor` sin filtrar por `Proveedor.activo`. Si un repuesto tiene stock bajo y su proveedor está inactivo, se sugiere comprar a un proveedor que no se debería usar.

**Recomendación:** Filtrar repuestos cuyo proveedor esté activo, o excluir explícitamente proveedores inactivos:
```python
query = query.join(Proveedor, Repuesto.id_proveedor == Proveedor.id_proveedor)
query = query.filter(or_(Repuesto.id_proveedor.is_(None), Proveedor.activo == True))
```

---

#### E4. Búsqueda con `telefono`/`email` NULL

**Archivo:** `app/routers/proveedores.py` — `listar_proveedores`

**Situación:** El filtro usa `Proveedor.telefono.like(term)` y `Proveedor.email.like(term)`. En SQL, `NULL LIKE '%x%'` es NULL, por tanto esos registros no aparecen. Esto es coherente, pero puede sorprender si se espera que la búsqueda también encuentre por `contacto` o `direccion`.

**Recomendación:** Opcionalmente extender la búsqueda a `contacto` y `direccion` para mejorar la UX.

---

### 2.3 Menores

#### E5. Sin restricción de unicidad en RFC

**Archivo:** `app/models/proveedor.py`

**Situación:** No hay `unique=True` en `rfc`. Pueden existir varios proveedores con el mismo RFC.

**Recomendación:** Evaluar si el negocio exige RFC único. Si sí, añadir índice único y validación en el router.

---

#### E6. Sin restricción de unicidad en nombre

**Situación:** No hay unicidad en `nombre`. Puede ser intencional (mismo nombre, distintas sucursales).

**Recomendación:** Documentar la decisión de negocio. Si se quiere evitar duplicados, añadir validación o índice único.

---

## 3. Mejoras propuestas

### 3.1 Backend

#### M1. Validar proveedor activo antes de desactivar

**Situación:** No se comprueba si el proveedor tiene órdenes de compra pendientes (BORRADOR, ENVIADA, RECIBIDA_PARCIAL) antes de desactivar.

**Propuesta:** Opcionalmente advertir o bloquear la desactivación si hay órdenes abiertas, según la política de negocio.

---

#### M2. Normalizar strings vacíos a None en actualización

**Situación:** Al actualizar, campos opcionales como `telefono: ""` se guardan como cadena vacía en vez de `NULL`.

**Propuesta:** En el router, antes de `setattr`, normalizar `""` a `None` en campos opcionales para mantener consistencia.

---

#### M3. Endpoint para ver repuestos/órdenes de un proveedor

**Propuesta:** Añadir p.ej. `GET /proveedores/{id}/resumen` con:
- Cantidad de repuestos asignados
- Cantidad de órdenes de compra
- Saldo pendiente (cuentas por pagar)

Ayuda a evaluar el impacto antes de desactivar.

---

### 3.2 Frontend

#### M4. Opción "Ver todos" (activos e inactivos)

**Archivo:** `frontend/src/pages/Proveedores.jsx`

**Situación:** Solo se puede alternar entre activos o inactivos. No existe vista combinada.

**Propuesta:** Añadir un tercer estado (p.ej. "Todos") que envíe `activo` sin valor o `activo=null` al backend.

---

#### M5. Indicador de uso del proveedor

**Propuesta:** Mostrar si el proveedor tiene repuestos u órdenes asociadas (por ejemplo, badge o indicador en la tabla).

---

### 3.3 Seguridad y auditoría

#### M6. Logging de cambios sensibles

**Situación:** Se registran creación, actualización y desactivación en logs.

**Propuesta:** Incluir en logs campos sensibles que cambien (email, teléfono) para auditoría, respetando políticas de privacidad.

---

## 4. Flujos verificados

| Flujo | Estado | Detalle |
|-------|--------|---------|
| Crear proveedor | ✅ | Validaciones (teléfono, email, RFC) aplicadas |
| Listar proveedores | ✅ | Paginación y filtros correctos |
| Obtener por ID | ✅ | Comportamiento esperado |
| Actualizar proveedor | ✅ | `exclude_unset=True` usado correctamente |
| Desactivar | ✅ | Solo `activo=False`, sin borrado físico |
| Reactivar | ✅ | Comprueba que no esté ya activo |
| Órdenes de compra | ✅ | Exige proveedor activo al crear |
| Repuestos | ✅ | Valida existencia de proveedor al crear |
| Cuentas por pagar | ✅ | Valida proveedor si se asocia |
| Entrada masiva | ⚠️ | No valida `id_proveedor` (ver E1) |

---

## 5. Dependencias del modelo

| Modelo | Relación | Comportamiento al desactivar |
|--------|----------|------------------------------|
| Repuesto | FK `id_proveedor` | Repuestos conservan la referencia |
| OrdenCompra | FK `id_proveedor` | No se permite crear órdenes nuevas a proveedor inactivo |
| MovimientoInventario | FK `id_proveedor` | Solo referencia, sin validación en entrada masiva |
| CuentaPagarManual | FK `id_proveedor` ON DELETE SET NULL | Si se hiciera hard delete, se pondría NULL |

---

## 6. Checklist de implementación sugerido

**Prioridad alta:**
- [x] E1: Validar `id_proveedor` en entrada masiva (corregido)
- [ ] E2: Normalizar RFC vacío a None en schemas
- [ ] E3: Filtrar proveedores inactivos en sugerencia de compra

**Prioridad media:**
- [ ] E4: Ampliar búsqueda a contacto/dirección
- [ ] M2: Normalizar strings vacíos en actualización

**Prioridad baja:**
- [ ] E5/E6: Evaluar unicidad RFC/nombre
- [ ] M3: Endpoint de resumen por proveedor
- [ ] M4: Opción "Ver todos" en frontend

---

## 7. Archivos revisados

| Archivo | Rol principal |
|---------|----------------|
| `app/models/proveedor.py` | Modelo Proveedor |
| `app/routers/proveedores.py` | CRUD y endpoints |
| `app/schemas/proveedor.py` | Validación Pydantic |
| `frontend/src/pages/Proveedores.jsx` | Vista de proveedores |
| `app/routers/ordenes_compra.py` | Uso en órdenes de compra |
| `app/routers/repuestos.py` | Uso en repuestos |
| `app/routers/inventario_reportes.py` | Sugerencia de compra |
| `app/routers/movimientos_inventario.py` | Entrada masiva |
| `app/routers/cuentas_pagar_manuales.py` | Cuentas por pagar |
| `app/utils/validators.py` | Validación de teléfono y email |
