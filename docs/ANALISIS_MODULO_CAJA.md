# Análisis del Módulo de Caja – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Router caja, servicio cierre turno, exportaciones, frontend Caja.jsx, integración con pagos y gastos.

---

## 1. Resumen ejecutivo

El módulo de Caja gestiona turnos de caja:
- Abrir/cerrar turno con montos de apertura y cierre
- Corte diario: efectivo esperado, cobros por método, gastos, pagos proveedores
- Histórico de turnos con filtro por fechas
- Cierre forzado (ADMIN) para turnos de otros usuarios
- Alertas de diferencia y turnos largos

---

## 2. Errores detectados

### E1. Comparación de rol sin compatibilidad con Enum

**Archivo:** `app/routers/caja.py` — `detalle_turno`, línea 225

```python
if current_user.rol == "CAJA" and turno.id_usuario != current_user.id_usuario:
```

**Impacto:** Si `current_user.rol` es Enum, la comparación directa puede fallar.

**Recomendación:** `rol = getattr(current_user.rol, "value", None) or str(current_user.rol)` y `if rol == "CAJA"`.

---

### E2. Fechas como string en filtros

**Archivos:** 
- `app/routers/caja.py` — `historico_turnos`, líneas 186-188
- `app/routers/exportaciones.py` — `exportar_turnos_caja`, líneas 1090-1092

**Situación:** Se compara `func.date(CajaTurno.fecha_cierre)` con strings `fecha_desde` y `fecha_hasta`.

**Recomendación:** Parsear a `date` con `datetime.strptime(fecha_desde[:10], "%Y-%m-%d").date()` antes del filtro.

---

### E3. Normalizar nivel en alertas (frontend)

**Archivo:** `frontend/src/pages/Caja.jsx`

**Situación:** `nivelClass(a.nivel)` usa `a.nivel` directamente. Si la API devuelve objeto con `.value`, la comparación fallaría.

**Recomendación:** Normalizar: `const nivelStr = typeof a.nivel === 'string' ? a.nivel : a.nivel?.value || ''`

---

## 3. Mejoras propuestas

### M1. cerrar-forzado con Body en lugar de Query

**Situación:** `monto_cierre` y `motivo` se reciben como query params. Para consistencia con otros endpoints de cierre, podría usarse un Body Pydantic (opcional, bajo impacto).

---

### M2. Pagos de cuentas manuales en corte

**Archivo:** `app/services/caja_service.py`, `app/routers/caja.py`

**Situación:** El servicio `cerrar_turno` ya incluye `PagoCuentaPagarManual` en el cálculo de efectivo esperado. El endpoint `corte_diario` solo suma `PagoOrdenCompra` para pagos proveedores. Las cuentas manuales pagadas en efectivo también salen de caja y deberían restarse del efectivo esperado en `corte_diario` para coherencia con el cierre.

**Verificación:** Revisar si corte_diario y detalle_turno consideran pagos a cuentas manuales. El servicio de cierre sí lo hace. El corte_diario devuelve `total_pagos_proveedores` (solo PagoOrdenCompra). Falta sumar pagos a cuentas manuales en efectivo para que el "efectivo esperado" del corte coincida con el del cierre. **Posible error de coherencia.**

---

## 4. Resumen de correcciones a aplicar

| ID | Tipo | Descripción |
|----|------|-------------|
| E1 | Error | Rol seguro en detalle_turno |
| E2 | Error | Parsear fechas en historico_turnos y exportar_turnos_caja |
| E3 | Mejora | Normalizar nivel en alertas (frontend) |

M1 y M2 quedan como mejoras futuras o verificación manual.