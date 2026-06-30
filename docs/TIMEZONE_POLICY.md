# Política de zonas horarias — Medina AutoDiag

**Zona oficial del negocio:** `America/Matamoros` (Matamoros, Tamaulipas, México).

**Configuración:** `TALLER_TIMEZONE` / `TIMEZONE` en `.env` (default `America/Matamoros`).

---

## Diagnóstico (junio 2026)

### Síntoma

En **Histórico de turnos** (y otros módulos) se mostraba hora ~5 h adelantada respecto a la hora real del taller (ej. `1:39 p.m.` cuando en Matamoros eran `8:39 a.m.`).

### Causa raíz

| Capa | Comportamiento incorrecto |
|------|---------------------------|
| **Base de datos** | `caja_turnos.fecha_apertura/cierre` con `func.now()` → UTC naive (correcto para almacenar) |
| **API caja** | Devolvía datetime **sin sufijo `Z`** → el cliente no sabía que era UTC |
| **Frontend** | `formatearFechaHora` parseaba ISO naive como **hora del navegador**, no UTC ni Matamoros |
| **Filtros Desde/Hasta** | `func.date(fecha_cierre)` en SQL extraía fecha en TZ del servidor BD, no en Matamoros |
| **Export Excel** | `strftime` directo sobre UTC naive → hora UTC en la celda |

### Convenciones coexistiendo (no unificar en una sola)

| Tipo de dato | Almacenamiento BD | Serialización API | Display frontend |
|--------------|-------------------|-------------------|------------------|
| **Eventos de sistema** (caja, pagos, ventas, auditoría, movimientos) | UTC naive | ISO 8601 **con `Z`** | `formatearFechaHora` → America/Matamoros |
| **fecha_ingreso OT** (TZ-1, desde 2026-06-17) | Local naive taller | ISO **sin `Z`** | `formatearFechaIngresoOtLocal` |
| **fecha_ingreso OT legacy** | UTC naive (Railway) | ISO sin `Z` | Conversión en backend `ingreso_ot_a_local_naive` |
| **Citas** `fecha_hora` | Local naive taller | ISO **sin `Z`** | `formatearFechaHora` solo si se migra; preferir wall-clock parser |
| **Citas** `creado_en` | UTC naive | ISO **con `Z`** | `formatearFechaHora` |

---

## Arquitectura objetivo

```
[Usuario Matamoros]  ← display America/Matamoros
        ↑
   frontend/utils/fechas.js  (TALLER_TIMEZONE, formatearFechaHora)
        ↑ ISO + Z
   app/utils/fechas.py  (isoformat_utc, rango día taller)
        ↑ UTC naive
   PostgreSQL / Railway
```

### Reglas obligatorias

1. **Nunca** mostrar timestamps de eventos sin convertir desde UTC a Matamoros.
2. **Nunca** usar `new Date(isoSinZ)` para eventos de sistema sin añadir `Z`.
3. **No** mezclar timezone del navegador con timezone del negocio en pantallas críticas.
4. Filtros por día calendario: **00:00:00 – 23:59:59.999** en Matamoros → convertir a UTC para `WHERE`.
5. Nuevos campos de evento real: preferir UTC en BD + `Z` en API.

---

## Utilidades centralizadas

### Backend — `app/utils/fechas.py`

| Función | Uso |
|---------|-----|
| `taller_tz()` | `ZoneInfo` del taller |
| `isoformat_utc(dt)` | Serializar evento UTC → `"…Z"` |
| `isoformat_fecha_ingreso_ot(dt)` | OT TZ-1 → sin `Z` |
| `utc_naive_a_taller_naive(dt)` | UTC → local naive (exportaciones) |
| `formatear_taller(dt)` | Cadena `YYYY-MM-DD HH:MM` en Matamoros |
| `inicio_dia_taller_utc` / `fin_dia_taller_utc` | Límites de día para filtros SQL |
| `condiciones_rango_local_naive` | Filtros citas (día wall-clock) |
| `isoformat_local_naive_taller` | Serializar citas `fecha_hora` (sin Z) |
| `ingreso_ot_en_dia_taller` | SQL `ordenes_hoy` TZ-1 + legacy |
| `condiciones_rango_fecha_solo` | Filtros columnas `Date` (YYYY-MM-DD) |
| `hoy_taller()` | Fecha calendario hoy en Matamoros |

### Frontend — `frontend/src/utils/fechas.js`

| Función | Uso |
|---------|-----|
| `TALLER_TIMEZONE` | `'America/Matamoros'` |
| `formatearFechaHora(iso)` | Eventos con `Z` (caja, pagos, ventas…) |
| `formatearFechaIngresoOtLocal(iso)` | fecha_ingreso OT TZ-1 |
| `formatearFechaHoraLocalNaive(iso)` | Citas `fecha_hora` (wall-clock, sin Z) |
| `formatearHoraLocalNaive(iso)` | Solo hora de cita local naive |
| `localNaiveAFechaHoraForm(iso)` | Split fecha/hora para formulario cita |
| `formatearFechaSolo(str)` | Solo fecha, sin desfase de día |
| `parseFechaLocal` / `fechaAStr` / `hoyStr` | Inputs `type="date"` en calendario local |

---

## Fase 1 — Implementado (Histórico de turnos)

- [x] `TurnoOut` serializa `fecha_apertura` / `fecha_cierre` con `Z`
- [x] `GET /caja/historico-turnos` — ISO UTC + filtros por día Matamoros
- [x] `GET /caja/turno/{id}` — fechas de turno y pagos con `Z`
- [x] `GET /exportaciones/caja` — horas en Matamoros + mismos filtros
- [x] `formatearFechaHora` — `timeZone: America/Matamoros`

---

## Módulos afectados — roadmap por fases

| Fase | Módulo | Estado | Notas |
|------|--------|--------|-------|
| 1 | Caja / Histórico turnos | ✅ Corregido | Esta entrega |
| 2 | Pagos (ingresos-detalle), Ventas listado/detalle | ✅ Corregido | Fase 2 |
| 2 | Dashboard agregado (facturado, ventas periodo, utilidad) | ✅ Corregido | Filtros Matamoros; `ordenes_hoy` sin tocar (TZ-1) |
| 2 | Auditoría listado | ✅ Corregido | |
| 2 | Movimientos inventario / Kardex | ✅ Corregido | Schema + export ajustes |
| 2 | Exportaciones ventas, utilidad, auditoría, inventario | ✅ Corregido | |
| 3 | Citas | ✅ Corregido | Local naive sin Z; filtros wall-clock Matamoros |
| 3 | Órdenes de compra | ✅ Corregido | Eventos UTC+Z; promesa YYYY-MM-DD |
| 3 | Cuentas por pagar manuales | ✅ Corregido | Date calendario; pagos con Z |
| 3 | Devoluciones | ✅ Corregido | Filtros Matamoros; movimiento con Z |
| 3 | Dashboard `ordenes_hoy` | ✅ Corregido | `ingreso_ot_en_dia_taller` (TZ-1+legacy) |
| 3 | Notificaciones alertas | ✅ Corregido | `fecha_creacion` con Z |
| 3 | Catálogos OT facturado | ✅ Corregido | Filtros Pago/Venta Matamoros |

---

## Pruebas

```bash
# Utilidades TZ
pytest tests/test_timezone_utilidades.py tests/test_timezone_caja.py -q

# Fase 2
pytest tests/test_timezone_fase2.py -q

# Fase 3
pytest tests/test_timezone_fase3.py -q

# Regresión TZ-1 OT
pytest tests/test_tz1_fecha_ingreso.py -q
```

### Casos manuales (smoke)

1. Abrir y cerrar turno → Histórico muestra hora igual al reloj de Matamoros (±1 min).
2. Filtro Desde/Hasta un solo día → incluye turnos cerrados ese día local.
3. Exportar Excel → columnas Fecha cierre/apertura en hora Matamoros.
4. OT nueva → fecha_ingreso sigue sin `Z` y coincide con hora local.

---

## Referencias

- `app/config.py` — `TALLER_TIMEZONE`
- `tests/test_tz1_fecha_ingreso.py` — convención OT
- `tests/test_timezone_utilidades.py` — rangos y formato
- `tests/test_timezone_caja.py` — contrato API caja
