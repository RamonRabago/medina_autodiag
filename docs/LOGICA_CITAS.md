# Lógica del Módulo de Citas

## 1. Flujo actual

### 1.1 Ciclo de vida de una cita

```
CREAR → CONFIRMADA → SI_ASISTIO
                  ↘ NO_ASISTIO
                  ↘ CANCELADA (con motivo)
```

- **CONFIRMADA**: Estado inicial al crear (el cliente ya confirmó al agendar).
- **SI_ASISTIO**: El cliente asistió y se atendió (puede vincularse a Orden de trabajo).
- **NO_ASISTIO**: El cliente no se presentó.
- **CANCELADA**: El cliente avisó que no podrá; se requiere motivo de cancelación.

### 1.2 Datos de una cita

| Campo        | Obligatorio | Descripción                                      |
|-------------|-------------|--------------------------------------------------|
| id_cliente  | Sí          | Cliente de la cita                               |
| id_vehiculo | No          | Vehículo (debe pertenecer al cliente)            |
| fecha_hora  | Sí          | Fecha y hora de la cita                          |
| tipo        | Sí          | REVISION, MANTENIMIENTO, REPARACION, DIAGNOSTICO, OTRO |
| motivo      | No          | Motivo breve (ej. "Revisión de frenos")          |
| notas       | No          | Notas adicionales                                |
| id_orden    | No          | Orden de trabajo vinculada (cuando se convierte) |

### 1.3 Flujo en la interfaz

1. **Listado**: Tabla con filtros (cliente, estado, fecha desde/hasta).
2. **Nueva cita**: Modal con formulario → POST /citas/.
3. **Ver detalle**: Modal con datos y acciones (Confirmar, Marcar realizada, Cancelar, Editar, Eliminar).
4. **Editar**: Mismo modal de nueva cita con datos precargados → PUT /citas/{id}.
5. **Eliminar**: Solo desde el modal de detalle (requiere confirmación).

---

## 2. Optimizaciones recomendadas

### 2.1 UX (prioridad alta)

| Mejora | Descripción |
|--------|-------------|
| **Botón Eliminar en la tabla** | Añadir "Eliminar" en la columna Acciones para borrar sin abrir el modal. |
| **Ordenar por fecha ascendente por defecto** | Mostrar primero las citas más próximas (hoy, mañana) en lugar de las más recientes. Opción: "Próximas" vs "Todas". |
| **Vista calendario opcional** | Mostrar citas en calendario semanal/mensual para planificación visual. |

### 2.2 Lógica de negocio

| Mejora | Descripción |
|--------|-------------|
| **Validar solapamiento** | Evitar citas a la misma hora para el mismo cliente/vehículo si se desea. |
| **Vinculación con Orden** | Al crear una orden desde una cita REALIZADA, actualizar id_orden automáticamente. |
| **Recordatorios** | (Futuro) Notificaciones antes de la cita (email/SMS). |

### 2.3 Backend

| Mejora | Descripción |
|--------|-------------|
| **Usar catálogos API** | El frontend define tipos/estados hardcodeados; usar GET /citas/catalogos/estados y GET /citas/catalogos/tipos. |
| **Optimizar count** | Si hay muchas citas, el `query.count()` puede ser lento; considerar paginación eficiente. |

### 2.4 Simplificaciones

| Mejora | Descripción |
|--------|-------------|
| **Ocultar botones según estado** | No mostrar "Confirmar" si ya está CONFIRMADA; ocultar "Marcar realizada" si ya está REALIZADA. |
| **Confirmación antes de Eliminar** | Mantener el `confirm()` actual; opcional: modal de confirmación más visible. |

---

## 3. Resumen de prioridades

1. **Inmediato**: Botón Eliminar en la tabla; ordenar por fecha ascendente (próximas primero).
2. **Corto plazo**: Usar catálogos API; ocultar botones irrelevantes según estado.
3. **Mediano plazo**: Validar solapamiento; vinculación automática con Orden.
