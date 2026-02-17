# Análisis del Módulo de Vacaciones – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelo, router, schemas, frontend, integración con asistencia.

---

## 1. Resumen ejecutivo

El módulo de vacaciones gestiona saldos y movimientos de días de vacaciones:
- Tipos: TOMA, ACREDITACION, AJUSTE
- Toma agendada: crea registros VACACION en Asistencia y reduce saldo
- Integración bidireccional con Asistencia (registro manual VACACION también descuenta)

Se han identificado **errores** y **mejoras**.

---

## 2. Errores detectados

### E1. Comparación de rol sin compatibilidad con Enum

**Archivo:** `app/routers/vacaciones.py` — `listar_movimientos`, línea 146

```python
if current_user.rol in ("TECNICO", "EMPLEADO"):
```

**Impacto:** Si `current_user.rol` es un Enum de SQLAlchemy, la comparación con tupla de strings puede fallar.

**Recomendación:** Usar el mismo patrón que en asistencia/notificaciones:
```python
rol = getattr(current_user.rol, "value", None) or str(current_user.rol)
if rol in ("TECNICO", "EMPLEADO"):
```

---

### E2. Normalizar tipo en frontend

**Archivo:** `frontend/src/pages/Vacaciones.jsx` — tabla de movimientos

**Situación:** Se usa `m.tipo === 'TOMA'` para el signo y estilos. Si la API devuelve `tipo` como objeto (ej. `{value: "TOMA"}`), la comparación fallaría.

**Recomendación:** Normalizar como en Asistencia:
```javascript
const tipoStr = typeof m.tipo === 'string' ? m.tipo : m.tipo?.value || ''
const signo = tipoStr === 'TOMA' ? '-' : '+'
```

---

## 3. Mejoras propuestas

### M1. useCallback para cargar

**Archivo:** `frontend/src/pages/Vacaciones.jsx`, línea 54

**Situación:** `useEffect(() => { cargar() }, [])` — `cargar` no está en dependencias. Patrón inconsistente con otros módulos.

**Recomendación:** Envolver `cargar` en `useCallback` y usarlo en el effect.

---

### M2. Botón Actualizar

**Situación:** No hay botón para recargar datos sin navegar. El usuario debe salir y volver.

**Propuesta:** Añadir botón "↻ Actualizar" como en Asistencia y Notificaciones.

---

### M3. Filtrar movimientos por API

**Situación:** ADMIN/CAJA carga todos los movimientos y filtra en el frontend. Con muchos registros puede ser lento.

**Propuesta:** Pasar `id_usuario` como query param cuando `filtroUsuario` está activo para reducir payload. Mejora futura.

---

### M4. Exportación Excel (documentado)

**Archivo:** `docs/AUDITORIA_VACACIONES.md`

**Situación:** No existe exportación de movimientos de vacaciones.

**Propuesta:** Endpoint `GET /exportaciones/vacaciones` con filtros por empleado y rango de fechas. Mejora futura.

---

## 4. Resumen de correcciones aplicadas

| ID | Tipo | Descripción | Estado |
|----|------|-------------|--------|
| E1 | Error | Rol seguro en listar_movimientos | ✅ Aplicado |
| E2 | Mejora | Normalizar tipo en tabla de movimientos | ✅ Aplicado |
| M1 | Mejora | useCallback para cargar | ✅ Aplicado |
| M2 | Mejora | Botón Actualizar | ✅ Aplicado |

M3 (filtrar por API) y M4 (exportación Excel) quedan como mejoras futuras documentadas.
