# Análisis del Módulo Configuración – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Frontend Configuracion.jsx (pestañas: categorías servicios/repuestos, bodegas, ubicaciones, estantes, niveles, filas, usuarios, festivos).

---

## 1. Resumen ejecutivo

La página Configuración centraliza múltiples catálogos:
- **Categorías** (servicios, repuestos)
- **Bodegas, ubicaciones, estantes, niveles, filas**
- **Usuarios** (solo ADMIN)
- **Festivos** (solo ADMIN)

Usa APIs: `/categorias-servicios/`, `/categorias-repuestos/`, `/bodegas/`, `/ubicaciones/`, `/estantes/`, `/niveles/`, `/filas/`, `/usuarios/`, `/festivos/`.

---

## 2. Errores y mejoras detectados

### E1. Frontend: esAdmin con rol potencialmente Enum

**Archivo:** `frontend/src/pages/Configuracion.jsx` — `user?.rol === 'ADMIN'`

**Situación:** Si `user.rol` viene como objeto con `.value`, la comparación falla.

**Recomendación:** Normalizar igual que en Prestamos, Auditoría, etc.

---

### E2. Frontend: cargar sin useCallback

**Archivo:** `frontend/src/pages/Configuracion.jsx`

**Situación:** `cargar` usa `esAdmin` internamente. `useEffect(() => { cargar() }, [])` no incluye dependencias. Si el rol cambia tras el login, no se recarga. Patrón distinto al de Caja, CuentasPorPagar, etc.

**Recomendación:** `useCallback` para `cargar` con `[esAdmin]` y `useEffect(() => { cargar() }, [cargar])`.

---

### E3. Frontend: u.rol y u.periodo_pago sin normalizar

**Archivo:** `frontend/src/pages/Configuracion.jsx` — tablas Usuarios y Usuarios-bodegas

**Situación:** `{u.rol}` y `u.periodo_pago === 'SEMANAL'` pueden fallar si la API devuelve objeto con `.value`.

**Recomendación:** Normalizar antes de mostrar y comparar.

---

### E4. Botón Actualizar

**Archivo:** `frontend/src/pages/Configuracion.jsx`

**Situación:** Solo se recarga al montar. No hay botón "Actualizar" explícito.

**Recomendación:** Añadir botón "↻ Actualizar" junto al título.

---

## 3. Mejoras opcionales (no aplicadas)

### M1. Festivos: manejo de errores

**Situación:** `api.get('/festivos/').catch(() => ({ data: [] }))` oculta errores (ver AUDITORIA_PROYECTO.md).

**Propuesta:** Usar `showError` en el catch. Prioridad baja.

---

### M2. Usuarios: formato de respuesta

**Situación:** Se asume `r8.data` como array. Algunas APIs devuelven `{ usuarios: [...] }`.

**Propuesta:** `r8?.data?.usuarios ?? (Array.isArray(r8?.data) ? r8.data : [])` para mayor robustez.

---

## 4. Resumen de correcciones a aplicar

| ID | Tipo   | Descripción                          |
|----|--------|--------------------------------------|
| E1 | Error  | Normalizar rol para esAdmin           |
| E2 | Mejora | useCallback para cargar               |
| E3 | Mejora | Normalizar u.rol y u.periodo_pago     |
| E4 | Mejora | Botón Actualizar                      |
