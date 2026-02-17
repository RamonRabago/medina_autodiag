# Análisis del Módulo de Ayuda – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Página Ayuda (Ayuda.jsx), contenido del manual (manualContenido.js).

---

## 1. Resumen ejecutivo

El módulo de Ayuda muestra el manual de usuario en formato markdown con:
- Índice navegable por secciones
- Búsqueda por título y contenido
- Sincronización con hash (#seccion-id) en la URL

Se han identificado **errores** y **mejoras**.

---

## 2. Errores detectados

### E1. Estados de Citas desactualizados en el manual

**Archivo:** `frontend/src/content/manualContenido.js` — sección citas

**Situación:** El manual lista estados "Programada, Confirmada, En taller, Completada, Cancelada, No asistió". Los estados reales del modelo son: **CONFIRMADA, SI_ASISTIO, NO_ASISTIO, CANCELADA**.

**Impacto:** Confusión del usuario. No existen "Programada", "En taller" ni "Completada".

**Recomendación:** Actualizar a los estados reales del sistema.

---

### E2. Referencia a archivo docs interno

**Archivo:** `frontend/src/content/manualContenido.js` — sección asistencia

**Situación:** El manual dice "Ver guía completa en **docs/ASISTENCIA_PERMISOS_INCAPACIDADES.md**". El usuario final no tiene acceso a ese archivo.

**Recomendación:** Cambiar por texto útil: "Consulta la guía de permisos e incapacidades en la documentación interna" o eliminar la referencia.

---

## 3. Mejoras propuestas

### M1. Scroll al cambiar de sección

**Archivo:** `frontend/src/pages/Ayuda.jsx`

**Situación:** Al cambiar de sección, si el artículo tiene scroll previo, la vista puede quedar mal posicionada. Al mostrar una sección nueva (especialmente si la anterior era larga), conviene hacer scroll al inicio del contenido.

**Recomendación:** Usar `ref` en el `article` y llamar `scrollTop = 0` al cambiar `seccionActiva`, o hacer scroll al `section` activo.

---

### M2. Vacaciones: clarificar quién puede tomar

**Archivo:** `frontend/src/content/manualContenido.js` — sección vacaciones

**Situación:** El manual indica "Haz clic en Tomar vacaciones" sin aclarar que solo ADMIN/CAJA pueden tomar vacaciones por otros. TECNICO/EMPLEADO solo ven su saldo y movimientos; no tienen botón para tomar vacaciones.

**Recomendación:** Añadir nota: "Solo administradores pueden tomar o acreditar vacaciones. Los empleados ven su saldo y movimientos."

---

### M3. Notificaciones: "Marcar resuelta"

**Archivo:** `frontend/src/content/manualContenido.js` — sección notificaciones

**Situación:** El manual dice "Marcar como leída". En el sistema los botones dicen "Marcar resuelta". Pequeña inconsistencia terminológica.

**Recomendación:** Cambiar a "Marcar resuelta" para alinear con la UI.

---

### M4. getHash fuera del componente

**Situación:** `getHash()` está definido dentro del componente pero no usa estado ni props. Puede extraerse como función pura fuera del componente.

**Propuesta:** Mejora menor de legibilidad.

---

## 4. Resumen de correcciones aplicadas

| ID | Tipo | Descripción | Estado |
|----|------|-------------|--------|
| E1 | Error | Estados de citas correctos en manual | ✅ Aplicado |
| E2 | Mejora | Referencia docs/ASISTENCIA (ya no presente) | — |
| M1 | Mejora | Scroll al inicio al cambiar sección | ✅ Aplicado |
| M2 | Mejora | Clarificar permisos en Vacaciones | ✅ Aplicado |
| M3 | Mejora | "Marcar resuelta" en Notificaciones | ✅ Aplicado |
| M4 | Mejora | getHash fuera del componente | ✅ Aplicado |
