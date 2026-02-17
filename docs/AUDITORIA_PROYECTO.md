# Auditoría general del proyecto Medina AutoDiag

**Fecha:** Febrero 2026  
**Última revisión:** Febrero 2026

---

## 1. Estado de correcciones recientes ✓

### Fechas
- **Frontend**: Util compartido `utils/fechas.js` con `parseFechaLocal`, `fechaAStr`, `hoyStr`. Integrado en 18 páginas.
- **OrdenesCompra**: Ya tenía `formatFechaLocal` con `+ 'T12:00:00'` como workaround (correcto).
- **Backend**: Python usa `date` y `datetime` correctamente; no hay parsing de strings "YYYY-MM-DD" que cause desfase.

---

## 2. Hallazgos pendientes

### 2.1 Manejo de errores en carga (frontend) ✅ PARCIALMENTE CORREGIDO

**Estado actual:**

| Página           | api.get('/config') | Carga principal          |
|------------------|--------------------|--------------------------|
| Ventas           | ✓ setErrorConfig   | ✓ setErrorCargar          |
| OrdenesTrabajo   | ✓ setErrorConfig + reintento | ✓ setErrorCargar |
| RepuestoForm     | ✓ showError        | ✓ setError                |
| NuevaOrdenTrabajo| ✓ showError        | N/A (Promise.allSettled)  |
| Configuracion    | N/A                | ✓ setError (festivos: catch silencioso, baja prioridad) |

**Pendiente (baja prioridad):** Configuracion — `api.get('/festivos/').catch(() => ({ data: [] }))` oculta fallo de festivos. Resto de carga usa setError.

---

### 2.2 Reset de filtro cuando el empleado desaparece ✅ CORREGIDO

| Página    | Filtro         | ¿Reset cuando usuario deja de existir? |
|-----------|----------------|----------------------------------------|
| Asistencia| filtroEmpleado | ✓ Sí (useEffect)                        |
| Vacaciones| filtroUsuario  | ✓ Sí (useEffect)                        |
| Prestamos | filtroUsuario  | ✓ Sí (useEffect líneas 51-55)           |

---

### 2.3 Visualización de fechas solo-día desde API

**Situación:** Cuando el API devuelve `"YYYY-MM-DD"` (solo fecha, sin hora), `new Date("2024-12-01")` se interpreta como medianoche UTC. En México (UTC-6), eso es 6pm del día anterior. Al usar `toLocaleDateString()` puede mostrarse el día incorrecto.

**Páginas afectadas:** Ventas, Clientes, Vehiculos, Caja, CuentasPorPagar, EditarOrdenCompra, OrdenesCompra, Inventario, Kardex, InventarioAlertas, Gastos, Auditoria, Citas, Notificaciones, Devoluciones, VentasIngresos.

**Patrón actual:** `new Date(v.fecha).toLocaleDateString()` o similar.

**Solución:** Crear util `formatearFechaDisplay(isoStr)` que use `parseFechaLocal` para strings "YYYY-MM-DD" y luego formatee, o usar el truco de OrdenesCompra: `new Date(s + 'T12:00:00')` para evitar medianoche UTC.

**Prioridad:** Media (solo visible en fechas límite según zona horaria).

---

### 2.4 Archivo temporal con credenciales ✅ MITIGADO

- `.gitignore` incluye `temporal_*.py`, por lo que no se versionan.
- Si se crea un script de emergencia, usar variables de entorno para credenciales.

---

### 2.5 Validación de parseFloat/parseInt ✅ PARCIALMENTE CORREGIDO

- **RepuestoForm, Clientes, Vehiculos:** Usan `numeros.js` (aNumero, aEntero, esNumeroValido). Validación de año 1900-2030 en vehículos.
- **Pendiente:** Revisar Citas, Asistencia, MiNomina, UsuarioForm si algún input numérico llega sin validar.

---

### 2.6 colSpan fijo en tablas

En Asistencia se corrigió para usar `dias.length + 1`. Otras tablas usan `colSpan={7}`, `colSpan={5}`, etc. fijos. Si el número de columnas cambia (p. ej. columnas dinámicas), podría desalinearse.

**Estado:** La mayoría de tablas tienen columnas fijas; el riesgo es bajo. Solo relevante si se añaden columnas dinámicas en el futuro.

---

## 3. Backend

### 3.1 Configuración de seguridad ✓
- `SECRET_KEY` validada en producción (longitud mínima, no valor por defecto).
- Passwords con hash (bcrypt).
- JWT para autenticación.
- Variables sensibles vía `os.getenv`.

### 3.2 Tests ✓
- Los 18 tests pasan. `test_root_returns_online` y `test_config_returns_iva` OK.

---

## 4. Resumen de prioridades

| Prioridad | Item                              | Estado                |
|-----------|-----------------------------------|-----------------------|
| ~~Alta~~  | Manejo de errores en carga        | ✅ Corregido          |
| ~~Media~~ | Reset filtroUsuario en Prestamos  | ✅ Ya estaba hecho   |
| Media     | Util formatearFechaDisplay (2.3)  | Pendiente             |
| ~~Baja~~  | temporal_corregir_usuario.py      | ✅ .gitignore + script |
| Baja      | Validación NaN en más formularios | Parcial (ver 2.5)     |

---

## 5. Checklist de consistencia

| Módulo        | Fechas util | Errores carga | Reset filtro |
|---------------|-------------|---------------|--------------|
| Asistencia    | ✓           | ✓             | ✓            |
| Vacaciones    | ✓           | ✓             | ✓            |
| Prestamos     | ✓           | ✓             | ✓            |
| Configuracion | ✓           | Parcial (festivos) | N/A     |
| Gastos        | ✓           | Parcial       | N/A          |
| Ventas        | ✓           | ✓             | N/A          |
| OrdenesTrabajo| ✓           | ✓             | N/A          |
| RepuestoForm  | ✓           | ✓             | N/A          |
