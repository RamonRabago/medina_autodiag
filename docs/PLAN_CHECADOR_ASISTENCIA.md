# Plan: Checador y Asistencia (Etapa 2 Nómina)

**Fecha:** Febrero 2026  
**Estado:** Plan aprobado – pendiente implementación

---

## 1. Reglas definidas por el usuario

| Tema | Decisión |
|------|----------|
| **Bono puntualidad** | Admin decide caso por caso si lo pierde o no (no automático por falta) |
| **Horas/días/horarios** | Flexibles por empleado, configurables |
| **Periodo pago** | Semanal |
| **Periodo a registrar** | Semanal |
| **Granularidad** | Día por día |
| **Festivos** | Admin los define manualmente |
| **Vacaciones** | Saldo por empleado |
| **Permisos** | Admin define al registrar: con goce o sin goce |
| **Incapacidades** | Admin define datos según trato con empleado (flexible) |

---

## 2. Configuración por empleado (ampliar Usuario)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `horas_por_dia` | Numeric(4,2) | Ej: 8 |
| `dias_por_semana` | Integer | Ej: 5 o 6 |
| `dias_vacaciones_saldo` | Numeric(5,2) | Días de vacaciones disponibles |
| `horario_inicio` | Time (opcional) | Ej: 08:00 |
| `horario_fin` | Time (opcional) | Ej: 17:00 |
| `dias_semana_trabaja` | Text/JSON (opcional) | Ej: "1,2,3,4,5" (lun-vie) |

*Nota: Ya existen salario_base, periodo_pago, bono_puntualidad*

**Nota de horario real del negocio:** Lun–Vie 7:50–18:00, Sáb 7:50–17:00. El sistema usa un solo par entrada/salida por empleado; se deja 7:50–18:00. La diferencia del sábado (1 h menos) tiene impacto mínimo en nómina.

---

## 3. Catálogo de días festivos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | |
| `fecha` | Date | Ej: 2025-12-25 |
| `nombre` | String | Ej: "Navidad" |
| `anio` | Integer | Para filtrar por año |

---

## 4. Registro de asistencia día por día

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | PK | |
| `id_usuario` | FK | Empleado |
| `fecha` | Date | Día específico |
| `tipo` | Enum | TRABAJO, FESTIVO, VACACION, PERMISO_CON_GOCE, PERMISO_SIN_GOCE, INCAPACIDAD, FALTA |
| `horas_trabajadas` | Numeric(4,2) | Si TRABAJO parcial; 0 si fue turno completo |
| `turno_completo` | Boolean | true = cumplió horario completo |
| `aplica_bono_puntualidad` | Boolean | Admin decide: ¿aplica bono este día? |
| `observaciones` | Text | Notas |
| `id_referencia` | FK (opcional) | Si es permiso/vacación, link a solicitud |

---

## 5. Vacaciones – saldo y movimientos

| Tabla | Campos clave |
|-------|--------------|
| **Usuario** | `dias_vacaciones_saldo` (actual) |
| **Movimiento vacaciones** | id_usuario, fecha, tipo (TOMA/ACREDITACION/AJUSTE), dias, periodo, observaciones |

---

## 6. Permisos especiales

Se registran como días en **asistencia** con:
- `tipo = PERMISO_CON_GOCE` o `PERMISO_SIN_GOCE`
- `observaciones` con motivo
- Admin define al momento de capturar

---

## 7. Incapacidades

Se registran como días en **asistencia** con:
- `tipo = INCAPACIDAD`
- `horas_trabajadas` o `turno_completo` según el caso
- `observaciones` con detalles
- Admin define cada caso según trato con empleado

---

## 8. Pantallas / flujos

1. **Configuración → Usuarios**  
   - Añadir: horas_por_dia, dias_por_semana, días_vacaciones_saldo, horario (opcional)

2. **Configuración → Festivos** (nueva pestaña o sección)  
   - CRUD de festivos por año

3. **Asistencia** (nueva página)  
   - Seleccionar semana (inicio-fin)
   - Lista de empleados con días de esa semana
   - Por cada día: selector de tipo (trabajo, festivo, vacación, permiso, incapacidad, falta)
   - Campos adicionales: horas, turno completo, aplica bono, observaciones

4. **Vacaciones** (sección o modal)  
   - Ver saldo por empleado
   - Registrar toma de vacaciones (reduce saldo)
   - Acreditación anual (aumenta saldo)

---

## 9. Integración con nómina (Etapa 4)

Al calcular nómina semanal:
- Sumar días/horas según tipo (trabajo, festivo, vacación, permiso con goce, incapacidad según regla)
- Salario proporcional = (días pagados / días esperados) × salario_base
- Bono puntualidad: solo si admin marcó `aplica_bono_puntualidad` en los días del periodo
- Restar descuentos por préstamos

---

## 10. Orden de implementación sugerido

| Fase | Contenido | Estado |
|------|-----------|--------|
| 1 | Campos en Usuario: horas_por_dia, dias_por_semana, dias_vacaciones_saldo | ✓ Hecho |
| 2 | Modelo y CRUD Festivos | ✓ Hecho |
| 3 | Modelo Asistencia (registro día por día) | ✓ Hecho |
| 4 | Pantalla Asistencia: captura semanal | ✓ Hecho |
| 5 | Saldo vacaciones: movimientos y UI | ✓ Hecho |
| 6 | Integración Etapa 4 (cálculo nómina) | ✓ Hecho |

---

## 11. Tipos de día (resumen)

| Tipo | Descripción | ¿Cuenta como pagado? |
|------|-------------|----------------------|
| TRABAJO | Día laboral normal | Sí (horas o turno completo) |
| FESTIVO | Día festivo | Sí (según configuración) |
| VACACION | Día de vacaciones | Sí, descuenta del saldo |
| PERMISO_CON_GOCE | Permiso pagado | Sí |
| PERMISO_SIN_GOCE | Permiso sin pago | No |
| INCAPACIDAD | Enfermedad/accidente | Admin define |
| FALTA | Falta injustificada | No |
