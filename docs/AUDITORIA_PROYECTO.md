# Auditoría general del proyecto Medina AutoDiag

**Fecha:** Febrero 2026

---

## 1. Estado de correcciones recientes ✓

### Fechas
- **Frontend**: Util compartido `utils/fechas.js` con `parseFechaLocal`, `fechaAStr`, `hoyStr`. Integrado en 18 páginas.
- **OrdenesCompra**: Ya tenía `formatFechaLocal` con `+ 'T12:00:00'` como workaround (correcto).
- **Backend**: Python usa `date` y `datetime` correctamente; no hay parsing de strings "YYYY-MM-DD" que cause desfase.

---

## 2. Hallazgos pendientes

### 2.1 Manejo de errores en carga (frontend)

**Páginas que usan `.catch(() => {})` y ocultan fallos:**

| Página           | Ubicación       | Impacto                     |
|------------------|-----------------|-----------------------------|
| Configuracion    | cargar datos    | Usuario no ve si falla API  |
| Ventas           | api.get('/config') | IVA por defecto silencioso  |
| RepuestoForm     | carga repuesto/proveedores | Form incompleto          |
| OrdenesTrabajo   | config, servicios | Listas vacías sin aviso  |

**Recomendación:** Igual que en Asistencia/Vacaciones, usar `setError()` en el catch para mostrar mensaje al usuario.

---

### 2.2 Reset de filtro cuando el empleado desaparece

| Página    | Filtro         | ¿Reset cuando usuario deja de existir? |
|-----------|----------------|----------------------------------------|
| Asistencia| filtroEmpleado | ✓ Sí (useEffect)                        |
| Vacaciones| filtroUsuario  | ✓ Sí (useEffect)                        |
| Prestamos | filtroUsuario  | ✗ No                                    |

**Recomendación:** Añadir `useEffect` en Prestamos para resetear `filtroUsuario` cuando el empleado filtrado no esté en la lista.

---

### 2.3 Visualización de fechas solo-día desde API

**Situación:** Cuando el API devuelve `"YYYY-MM-DD"` (solo fecha, sin hora), `new Date("2024-12-01")` se interpreta como medianoche UTC. En México (UTC-6), eso es 6pm del día anterior. Al usar `toLocaleDateString()` puede mostrarse el día incorrecto.

**Páginas afectadas:** Ventas, Clientes, Vehiculos, Caja, CuentasPorPagar, EditarOrdenCompra, OrdenesCompra, Inventario, Kardex, InventarioAlertas, Gastos, Auditoria, Citas, Notificaciones, Devoluciones, VentasIngresos.

**Patrón actual:** `new Date(v.fecha).toLocaleDateString()` o similar.

**Solución:** Crear util `formatearFechaDisplay(isoStr)` que use `parseFechaLocal` para strings "YYYY-MM-DD" y luego formatee, o usar el truco de OrdenesCompra: `new Date(s + 'T12:00:00')` para evitar medianoche UTC.

**Prioridad:** Media (solo visible en fechas límite según zona horaria).

---

### 2.4 Archivo temporal con credenciales

**Archivo:** `temporal_corregir_usuario.py` en la raíz del proyecto.

- Contiene `email` y `password` hardcodeados.
- Parece un script de emergencia para corregir un usuario admin.
- **Riesgo:** Si se sube a un repo público o se ejecuta por error.

**Recomendación:** Mover a `scripts/` con nombre explícito, usar variables de entorno para credenciales, o eliminarlo si ya no se usa. Añadir a `.gitignore` si es temporal.

---

### 2.5 Validación de parseFloat/parseInt

En varios formularios se usa `parseFloat(form.campo)` o `parseInt(form.campo)` sin comprobar `NaN`.

**Ejemplo:** Si el usuario escribe "abc" en un campo numérico, se envía `NaN` al API.

**Recomendación:** Validar antes de enviar (ej. `isNaN(parseFloat(val))`) y mostrar error al usuario.

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

### 3.2 Tests fallidos (pre-existentes)
- `test_root_returns_online` y `test_config_returns_iva`: esperan JSON pero reciben respuesta vacía o HTML.
- No están relacionados con los cambios de fechas.

---

## 4. Resumen de prioridades

| Prioridad | Item                              | Esfuerzo |
|-----------|-----------------------------------|----------|
| Alta      | Manejo de errores en carga (4 páginas) | Bajo     |
| Media     | Reset filtroUsuario en Prestamos       | Bajo     |
| Media     | Util formatearFechaDisplay para listas | Medio    |
| Baja      | Revisar temporal_corregir_usuario.py   | Bajo     |
| Baja      | Validación NaN en inputs numéricos    | Medio    |

---

## 5. Checklist de consistencia

| Módulo      | Fechas util | Errores carga | Reset filtro |
|-------------|-------------|---------------|--------------|
| Asistencia  | ✓           | ✓             | ✓            |
| Vacaciones  | ✓           | ✓             | ✓            |
| Prestamos   | ✓           | ✗             | ✗            |
| Configuracion | ✓        | ✗             | N/A          |
| Gastos      | ✓           | Parcial       | N/A          |
| Ventas      | N/A         | ✗             | N/A          |
| OrdenesTrabajo | N/A      | ✗             | N/A          |
| RepuestoForm   | N/A      | ✗             | N/A          |
