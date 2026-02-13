# Auditoría del módulo Vacaciones

**Fecha:** Febrero 2026

---

## Resumen ejecutivo

El módulo de Vacaciones está funcional y bien integrado con Asistencia. Se listan mejoras recomendadas y consideraciones menores.

---

## 1. Lo que funciona ✓

- **Fechas en hora local**: `parseFechaLocal`, `fechaAStr` y `generarFechasRango` evitan desfase UTC. Sin `toISOString().slice(0,10)` para fechas locales.
- **Saldos por empleado**: Se muestran desde `usuarios.dias_vacaciones_saldo`.
- **Toma con fechas** (`tomar-agendado`): Crea registros VACACION en Asistencia y reduce saldo.
- **Acreditación y ajuste**: Aumentan o ajustan el saldo vía `/movimientos`.
- **Historial de movimientos**: Lista filtrable por empleado.
- **Integración con Asistencia**: Al borrar/cambiar VACACION en Asistencia se actualiza el saldo.
- **Parseo de fechas**: `parseFechaLocal` y `fechaAStr` evitan desfase de zona horaria.

---

## 2. Mejoras recomendadas (aplicadas ✓)

### 2.1 Manejo de errores en `cargar()` ✓

**Implementado:** `setError()` cuando falla la carga, mensaje visible cuando el modal está cerrado.

---

### 2.2 Reset de `filtroUsuario` cuando el empleado deja de existir ✓

**Implementado:** `useEffect` que resetea `filtroUsuario` cuando el empleado filtrado no está en la lista.

---

### 2.3 Falta de documentación en el manual de ayuda

**Situación actual:** No hay entrada de Vacaciones en `manualContenido.js` / Ayuda.

**Propuesta:** Añadir sección de Vacaciones con:
- Cómo ver saldo por empleado
- Cómo tomar vacaciones (fechas inicio–fin)
- Cómo acreditar días anuales
- Cómo hacer ajustes manuales

---

### 2.4 Exportación de movimientos

**Situación actual:** No existe exportación a Excel de movimientos de vacaciones.

**Propuesta:** Endpoint `GET /exportaciones/vacaciones` con filtros por empleado y rango de fechas (similar a asistencia).

---

## 3. Consideraciones de diseño (bajo impacto)

### 3.1 Toma en días no laborables

**Situación actual:** Se pueden tomar vacaciones en días configurados como no laborables (p. ej. domingo de Demetrio).

**Consideración:** Depende de la política: si no se trabaja, puede no contar como vacación. Por ahora se mantiene el comportamiento actual (sí cuenta). Opcional: aviso cuando la fecha sea día no laborable.

---

### 3.2 Endpoint `/movimientos` con tipo TOMA

**Situación actual:** El backend permite `tipo=TOMA` en `/movimientos` (reduce saldo sin crear registros en Asistencia). El frontend solo usa `tomar-agendado` para tomas.

**Consideración:** El flujo principal está bien. El endpoint antiguo queda para uso por API o scripts; no requiere cambio.

---

### 3.3 Paginación de movimientos

**Situación actual:** Se cargan todos los movimientos sin límite.

**Consideración:** Con muchos años de historial puede haber lentitud. Más adelante se podría paginar por fecha o cantidad.

---

## 4. Checklist de funcionalidades

| Funcionalidad              | Estado |
|---------------------------|--------|
| Ver saldo por empleado    | ✓      |
| Toma con fechas           | ✓      |
| Acreditación anual        | ✓      |
| Ajuste manual             | ✓      |
| Historial movimientos     | ✓      |
| Filtro por empleado       | ✓      |
| Integración Asistencia    | ✓      |
| Zona horaria corregida    | ✓      |
| Manual de ayuda           | ✗      |
| Exportación Excel         | ✗      |
| Manejo de errores en carga| ✗      |
| Reset filtro empleado     | ✗      |

---

## 5. Próximos pasos sugeridos

1. Manejo de errores en `cargar()`.
2. `useEffect` para resetear `filtroUsuario` cuando el empleado ya no esté en la lista.
3. Añadir sección Vacaciones en el manual de ayuda.
4. (Opcional) Endpoint de exportación de movimientos de vacaciones.
