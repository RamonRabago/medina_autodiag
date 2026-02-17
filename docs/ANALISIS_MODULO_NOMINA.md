# Análisis del Módulo de Nómina – Medina Autodiag

**Fecha:** 2025-02-17  
**Alcance:** Servicio de cálculo, endpoint mi-resumen (prestamos_empleados), frontend MiNomina, integración con asistencia y préstamos.

---

## 1. Resumen ejecutivo

El módulo de nómina agrega:
- **Servicio** `nomina_service.py`: cálculo de salario proporcional, bono puntualidad según asistencia
- **Endpoint** `GET /prestamos-empleados/me/mi-resumen`: nómina del periodo + préstamos activos
- **Frontend** `MiNomina.jsx`: recibo, selector de periodo, imprimir

Periodos soportados: SEMANAL, QUINCENAL, MENSUAL según `usuario.periodo_pago`.

---

## 2. Errores detectados

### E1. Comparación de estado sin compatibilidad con Enum

**Archivo:** `app/routers/prestamos_empleados.py` — `aplicar_descuento`, línea 222

```python
if prestamo.estado != "ACTIVO":
```

**Impacto:** Si `prestamo.estado` es un Enum de SQLAlchemy, la comparación con string puede fallar.

**Recomendación:** Normalizar antes de comparar:
```python
estado_str = getattr(prestamo.estado, "value", None) or str(prestamo.estado)
if estado_str != "ACTIVO":
```

---

### E2. Uso de formatearFecha local en lugar de utilidad compartida

**Archivo:** `frontend/src/pages/MiNomina.jsx`

**Situación:** Existe `formatearFecha` local duplicando lógica de zona horaria (T12:00:00 para fechas). El proyecto tiene `formatearFechaSolo` en `utils/fechas.js` que ya maneja estos casos.

**Recomendación:** Usar `formatearFechaSolo` de utils para consistencia.

---

## 3. Mejoras propuestas

### M1. Normalizar tipo_periodo en frontend

**Situación:** `PERIODOS[resumen.tipo_periodo]` y `PERIODOS[p.periodo_descuento]` pueden fallar si la API devuelve objeto en lugar de string (ej. `{value: "SEMANAL"}`).

**Recomendación:** Normalizar de forma defensiva:
```javascript
const tipoStr = typeof resumen.tipo_periodo === 'string' ? resumen.tipo_periodo : resumen.tipo_periodo?.value || 'SEMANAL'
```

---

### M2. días_esperados según dias_por_semana

**Archivo:** `app/services/nomina_service.py`

**Situación:** Para QUINCENAL usa 10 fijo; para MENSUAL usa 22 fijo. No considera `usuario.dias_por_semana`.

**Propuesta:** QUINCENAL = 2 × (dias_por_semana or 5); MENSUAL ≈ 4.4 × (dias_por_semana or 5). Mejora futura, bajo impacto.

---

### M3. showWarning en lugar de showError para popups

**Archivo:** `frontend/src/pages/MiNomina.jsx` — `imprimirRecibo`

**Situación:** `showError('Permite ventanas emergentes...')` es más un aviso que un error. `showWarning` sería más apropiado.

**Propuesta:** Usar `showWarning` para mensajes informativos.

---

## 4. Resumen de correcciones aplicadas

| ID | Tipo | Descripción | Estado |
|----|------|-------------|--------|
| E1 | Error | Estado seguro en aplicar_descuento | ✅ Aplicado |
| E2 | Mejora | Usar formatearFechaSolo de utils | ✅ Aplicado |
| M1 | Mejora | Normalizar tipo_periodo/periodo_descuento en frontend | ✅ Aplicado |
| M3 | Mejora | showWarning para aviso de popups | ✅ Aplicado |

M2 (días esperados por dias_por_semana) queda como mejora futura. El frontend ya tiene useCallback y botón Actualizar.
