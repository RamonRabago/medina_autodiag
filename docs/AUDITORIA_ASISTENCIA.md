# Auditoría del módulo Asistencia

**Fecha:** Febrero 2026

---

## Resumen ejecutivo

El módulo de Asistencia está funcionalmente completo. A continuación se listan mejoras recomendadas, deudas técnicas menores y consideraciones de diseño.

---

## 1. Corregido recientemente ✓

- `dias_semana_trabaja`: se prioriza la configuración sobre registros existentes; se muestra "No trabaja" aunque exista un registro inconsistente.
- Inconsistencias de fecha/zona horaria: uso de `parseFechaLocal` para evitar desfase UTC.
- `colSpan` dinámico en la tabla.
- Uso consistente de `desdeRango`/`hastaRango` en prellenar y exportar.
- Validación de entrada en `parseFechaLocal`.
- Reset de `filtroEmpleado` cuando el empleado deja de ser visible.

---

## 2. Mejoras recomendadas (prioridad media)

### 2.1 Resumen del período: excluir TRABAJO en días no laborables

**Situación actual:** El resumen cuenta todos los registros TRABAJO, incluidos días configurados como no laborables (`dias_semana_trabaja`).

**Propuesta:** Al calcular días de trabajo y horas, ignorar registros TRABAJO en días en que el empleado no trabaja según su configuración. Así el resumen refleja mejor la realidad aunque queden registros antiguos pendientes de borrar.

**Impacto:** Cambio en el `useMemo` de `resumenSemana` para pasar `trabajaEseDia(u, fecha)` y no sumar TRABAJO cuando sea falso.

---

### 2.2 Código muerto: `diasDeSemana`

La función `diasDeSemana(lunes)` en Asistencia.jsx (líneas 37–45) no se usa. Se puede eliminar.

---

### 2.3 Manejo de errores en `cargar()`

**Situación actual:** `Promise.all(...).catch(() => {})` oculta errores de la API.

**Propuesta:** Mostrar un mensaje al usuario cuando falle la carga (por ejemplo `setError('Error al cargar datos')` o toast).

---

### 2.4 Dependencias del `useMemo` de `resumenSemana`

**Situación actual:** Dependencias: `[asistencia, usuariosFiltrados, usuarios, rangoIni, rangoFin]`.

**Consideración:** El bucle inicial usa `usuariosVisibles`; al cambiar `incluirRegistroManual`, `usuariosVisibles` cambia vía `usuariosFiltrados` (cuando `filtroEmpleado` está vacío). Las dependencias actuales cubren el caso. Para mayor claridad, se podría añadir `usuariosVisibles` explícitamente.

---

## 3. Consideraciones de diseño (bajo impacto)

### 3.1 Overtime en días no laborables

**Situación actual:** En días no laborables solo se puede borrar registros; no se permite añadir, por ejemplo, TRABAJO de horas extra un domingo.

**Consideración:** Es una restricción deliberada: primero se corrige la configuración; si hay excepciones reales, podría añadirse un botón "Agregar (excepción)" o similar.

---

### 3.2 Prellenar festivos y `dias_semana_trabaja`

**Situación actual:** El prellenado crea FESTIVO para todos los empleados activos en los festivos del rango, sin considerar `dias_semana_trabaja`.

**Consideración:** Los festivos suelen aplicarse a todos; marcar un domingo festivo para quien no trabaja domingos es coherente como registro. No requiere cambio.

---

### 3.3 Vacaciones desde Asistencia

**Situación actual:** La toma de vacaciones se hace desde Vacaciones, no desde Asistencia.

**Consideración:** Flujo válido. Si se requiere, se podría añadir un atajo en Asistencia (p. ej. “Tomar vacaciones”) que abra el modal o navegue a Vacaciones.

---

## 4. Backend

### 4.1 Exportación asistencia: parámetros opcionales

**Situación actual:** `fecha_desde` y `fecha_hasta` son opcionales; si no se envían, la consulta devuelve registros sin filtrar por fechas (hasta el `limit`).

**Propuesta:** Requerir fechas en este endpoint para evitar descargas masivas por error.

---

### 4.2 Prellenar festivos: nombres de variables

En el endpoint `prellenar-festivos`, las variables `lun` y `dom` se usan aunque el rango pueda ser de hasta 31 días. Sería más claro usar `fecha_min` / `fecha_max` o `desde` / `hasta`.

---

## 5. Nómina

El servicio de nómina suma todos los registros de asistencia con tipo pagado sin comprobar `dias_semana_trabaja`. Es coherente: se paga lo registrado; si hay registros incorrectos, se corrigen en Asistencia (p. ej. con “Borrar registro”).

---

## 6. Vacaciones.jsx: posible bug de zona horaria

`generarFechasRango(inicio, fin)` usa `new Date(inicio)` y `new Date(fin)` con strings "YYYY-MM-DD". Eso puede producir el mismo desfase de zona horaria que ya se corrigió en Asistencia. Se recomienda usar una función similar a `parseFechaLocal`.

---

## 7. Checklist de funcionalidades

| Funcionalidad                         | Estado  |
|--------------------------------------|---------|
| Tabla empleados × días                | ✓       |
| Selector de tipo por celda           | ✓       |
| Modal detalle (horas, turno, bono)   | ✓       |
| Días no laborables (No trabaja)      | ✓       |
| Borrar registros inconsistentes      | ✓       |
| Prellenar festivos                   | ✓       |
| Exportar Excel                       | ✓       |
| Resumen del período                  | ✓       |
| Rango flexible (1 sem, 2 sem, mes)   | ✓       |
| Navegación mensual (◀ ▶)            | ✓       |
| Filtro por empleado                  | ✓       |
| Incluir registro manual              | ✓       |
| Integración vacaciones (saldo)       | ✓       |
| Integración nómina                   | ✓       |
| Permisos e incapacidades             | ✓       |

---

## 8. Próximos pasos sugeridos

1. Eliminar `diasDeSemana` (código muerto).
2. Añadir manejo de errores en `cargar()`.
3. Opcional: excluir TRABAJO en días no laborables del resumen.
4. Opcional: corregir `generarFechasRango` en Vacaciones.jsx para evitar desfase de zona horaria.
5. Opcional: exigir `fecha_desde` y `fecha_hasta` en el endpoint de exportación de asistencia.
