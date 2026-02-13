# Permisos e Incapacidades en Asistencia

Guía de uso de los tipos **Permiso con goce**, **Permiso sin goce** e **Incapacidad** en el módulo de Asistencia.

---

## Ubicación

- **Página**: Asistencia
- **Acceso**: Configuración del día en la grilla (selector de tipo o botón "Detalle"/"+ Agregar")

---

## Tipos disponibles

| Tipo | Descripción | Impacto en nómina |
|------|-------------|-------------------|
| **Permiso c/goce** | Permiso autorizado, se paga el día | ✅ Cuenta como día pagado |
| **Permiso s/goce** | Permiso sin pago | ❌ No se paga |
| **Incapacidad** | Enfermedad o accidente (con dictamen) | ✅ Cuenta como día pagado* |

\* El admin decide caso por caso si aplica bono puntualidad y si cuenta completo o parcial.

---

## 1. Permiso con goce (PERMISO_CON_GOCE)

**Cuándo usar:** Ausencias autorizadas que se pagan (cita médica, trámite personal, asuntos familiares aprobados, etc.).

**Cómo registrar:**
1. En Asistencia, selecciona el día y el empleado.
2. Tipo: **Permiso c/goce**
3. **Turno completo**: marca si fue el día entero; si fue medio día, desmarca y pon las horas en "Horas trabajadas".
4. **Aplica bono puntualidad**: marca si corresponde (según política).
5. **Observaciones**: indica el motivo, ej. *"Cita médica", "Trámite personal", "Asunto familiar"*.

**Ejemplo:** Empleado sale 2 horas para cita → Tipo Permiso c/goce, turno completo: No, horas: 6, observaciones: "Cita médica".

---

## 2. Permiso sin goce (PERMISO_SIN_GOCE)

**Cuándo usar:** Ausencias autorizadas que **no** se pagan (permiso personal sin goce de sueldo, salida sin justificación laboral, etc.).

**Cómo registrar:**
1. Tipo: **Permiso s/goce**
2. **Horas trabajadas / turno completo**: igual que permisos con goce, según si fue día completo o parcial.
3. **Aplica bono puntualidad**: decide si aplica (por ejemplo, si hay ausencias injustificadas se suele descontar).
4. **Observaciones**: motivo del permiso.

**Impacto:** El día no entra en el cálculo del salario proporcional.

---

## 3. Incapacidad (INCAPACIDAD)

**Cuándo usar:** Días cubiertos por incapacidad médica (enfermedad, accidente) con dictamen del IMSS o médico particular.

**Cómo registrar:**
1. Tipo: **Incapacidad**
2. **Turno completo**: si la incapacidad es de día completo, marca. Si trabajó parte del día, desmarca y pon las horas trabajadas.
3. **Aplica bono puntualidad**: decide según política (en algunos casos se pierde por incapacidad).
4. **Observaciones**: datos relevantes, ej. *"IMSS 3 días", "Accidente laboral", "Enfermedad general 5 días"*.

**Impacto:** Cuenta como día pagado en nómina (según trato con el empleado). El admin define caso por caso si aplica bono.

---

## Campos comunes en el modal

| Campo | Uso |
|-------|-----|
| **Tipo** | Permiso c/goce, Permiso s/goce o Incapacidad |
| **Horas trabajadas** | Si no es turno completo, indica las horas trabajadas |
| **Turno completo** | Marca si fue el día entero |
| **Aplica bono puntualidad** | Define si suma al bono de puntualidad |
| **Observaciones** | Motivo y detalles (recomendado en permisos e incapacidades) |

---

## Recomendaciones

1. **Observaciones**: Usa este campo siempre para dejar trazabilidad.
2. **Permisos parciales**: Si el empleado faltó medio día, usa "Horas trabajadas" con las horas que sí trabajó.
3. **Incapacidad IMSS**: Puedes referenciar el folio o días autorizados en observaciones.
4. **Bono puntualidad**: En incapacidades, se suele aplicar; en permisos sin goce, depende de la política.

---

## Impacto en nómina (resumen)

- **Permiso c/goce** e **Incapacidad**: se incluyen en días pagados.
- **Permiso sin goce**: no se incluye en días pagados.
- El **bono puntualidad** se calcula según el checkbox "Aplica bono puntualidad" de cada registro.
