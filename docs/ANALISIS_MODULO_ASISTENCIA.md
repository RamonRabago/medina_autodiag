# Análisis del Módulo de Asistencia – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Modelo, router, schemas, exportaciones, frontend, integración con vacaciones y festivos.

---

## 1. Resumen ejecutivo

El módulo de asistencia registra día por día el tipo de asistencia de cada empleado:
- Tipos: TRABAJO, FESTIVO, VACACION, PERMISO_CON_GOCE, PERMISO_SIN_GOCE, INCAPACIDAD, FALTA
- Integración con vacaciones (descuenta/devolución de saldo al usar VACACION)
- Prellenado de festivos para empleados activos

Se han identificado **errores** y **mejoras**.

---

## 2. Errores detectados

### E1. Fechas como string en filtro de exportación

**Archivo:** `app/routers/exportaciones.py` — `exportar_asistencia`, líneas 1020-1022

```python
query = db.query(Asistencia).filter(
    Asistencia.fecha >= fecha_desde,
    Asistencia.fecha <= fecha_hasta,
)
```

**Impacto:** Se compara `Asistencia.fecha` (columna `Date`) con strings `fecha_desde` y `fecha_hasta`. Puede fallar o comportarse de forma inconsistente según el motor SQL.

**Recomendación:** Parsear explícitamente a `date`:
```python
fd = datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date()
fh = datetime.strptime(fecha_hasta[:10], "%Y-%m-%d").date()
query = db.query(Asistencia).filter(
    Asistencia.fecha >= fd,
    Asistencia.fecha <= fh,
)
```

---

### E2. Comparación de rol sin compatibilidad con Enum

**Archivo:** `app/routers/asistencia.py` — `listar_asistencia`, línea 101

```python
if current_user.rol in ("TECNICO", "EMPLEADO"):
```

**Impacto:** Si `current_user.rol` es un Enum de SQLAlchemy, la comparación con tupla de strings puede fallar (el Enum no es igual al string).

**Recomendación:** Usar el mismo patrón que en `exportar_asistencia`:
```python
rol = getattr(current_user.rol, "value", None) or str(current_user.rol)
if rol in ("TECNICO", "EMPLEADO"):
```

---

### E3. Falta de control de acceso en obtener_asistencia

**Archivo:** `app/routers/asistencia.py` — `obtener_asistencia`, líneas 188-198

**Situación:** TECNICO y EMPLEADO pueden obtener cualquier registro de asistencia por ID (`GET /asistencia/{id_asistencia}`) sin verificar que pertenezca al usuario actual.

**Impacto:** Un empleado podría consultar asistencia de otros empleados si conoce el ID (fuga de información).

**Recomendación:** Añadir filtro por `id_usuario` cuando el rol es TECNICO o EMPLEADO:
```python
if rol in ("TECNICO", "EMPLEADO"):
    if a.id_usuario != current_user.id_usuario:
        raise HTTPException(status_code=404, detail="Registro de asistencia no encontrado")
```

---

## 3. Mejoras propuestas

### M1. Normalizar tipo en frontend

**Archivo:** `frontend/src/pages/Asistencia.jsx`

**Situación:** Al cargar el modal de detalle (`abrirDetalle`), se usa `a?.tipo ?? 'TRABAJO'`. Si la API devuelve `tipo` como objeto (ej. `{value: "TRABAJO"}`) en lugar de string, el select no mostraría el valor correcto. El `resumenSemana` ya maneja ambos casos con `typeof r.tipo === 'string' ? r.tipo : r.tipo?.value || ''`.

**Recomendación:** Aplicar el mismo patrón en `abrirDetalle` y en el `value` del select de celdas (`reg?.tipo`).

---

### M2. useCallback para cargar en useEffect

**Archivo:** `frontend/src/pages/Asistencia.jsx`, línea 137

**Situación:** `cargar` se usa en el `useEffect` pero no está en el array de dependencias. ESLint lo señala; además, si `cargar` cambiara, el efecto no se re-ejecutaría correctamente.

**Recomendación:** Envolver `cargar` con `useCallback` y las dependencias adecuadas (`desdeRango`, `hastaRango`, `filtroEmpleado`).

---

### M3. Prellenar festivos y dias_semana_trabaja

**Documentación:** `docs/AUDITORIA_ASISTENCIA.md`

**Situación:** El prellenado crea FESTIVO para todos los empleados activos en festivos del rango, sin considerar `dias_semana_trabaja`. Un empleado que trabaja solo Lun–Vie seguiría recibiendo FESTIVO en sábado/domingo.

**Propuesta:** Mejora futura: filtrar empleados por `dias_semana_trabaja` al prellenar, o documentar explícitamente que es intencional (festivos son días no laborables para todos).

---

### M4. Botón Actualizar

**Situación:** El módulo no tiene un botón explícito "Actualizar" para recargar datos. El usuario debe cambiar fechas o filtro para recargar.

**Propuesta:** Añadir un botón "Actualizar" que llame a `cargar()` (como en Notificaciones).

---

## 4. Resumen de correcciones aplicadas

| ID | Tipo | Descripción | Estado |
|----|------|-------------|--------|
| E1 | Error | Parsear fecha_desde/fecha_hasta a date en exportar_asistencia | ✅ Aplicado |
| E2 | Error | Rol seguro con getattr(..., "value", None) en listar_asistencia | ✅ Aplicado |
| E3 | Error | Verificar id_usuario en obtener_asistencia para TECNICO/EMPLEADO | ✅ Aplicado |
| M1 | Mejora | Normalizar tipo (string/objeto) en abrirDetalle y select de celdas | ✅ Aplicado |
| M2 | Mejora | useCallback para cargar en Asistencia.jsx | ✅ Aplicado |
| M4 | Mejora | Botón Actualizar para recargar datos | ✅ Aplicado |

M3 (prellenar festivos por dias_semana_trabaja) queda como mejora futura documentada.
