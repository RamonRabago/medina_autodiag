# CIERRE — Política de timezone America/Matamoros (Fases 1–3)

**Versión:** 1.0  
**Fecha:** 30 de junio de 2026  
**Estado:** ✅ **CERRADO EN PRODUCCIÓN**  
**Entorno producción:** `https://medinaautodiag.up.railway.app`  
**Commit:** `0ffaa3d` — `feat(timezone): política America/Matamoros fases 1-3`

**Referencias:**

- [TIMEZONE_POLICY.md](./TIMEZONE_POLICY.md) — política técnica vigente
- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)
- `app/config.py` — `TALLER_TIMEZONE`
- `app/utils/fechas.py` — utilidades centralizadas backend
- `frontend/src/utils/fechas.js` — utilidades centralizadas frontend

---

## Objetivo del cambio

Corregir el desfase horario (~5 h en verano CDT) que afectaba histórico de turnos, listados, filtros por día y exportaciones Excel, unificando la **política oficial de fechas** del taller bajo la zona `America/Matamoros`.

El problema no era un único bug de UI: coexistían convenciones distintas (UTC naive en BD, ISO sin `Z` en API, `func.date()` del servidor, parsers del navegador) que producían horas incorrectas según módulo y pantalla.

**Meta alcanzada:**

- Eventos de sistema legibles en hora Matamoros sin ambigüedad (`Z` en API).
- Filtros Desde/Hasta alineados al **día calendario local** del taller.
- Citas y `fecha_ingreso` OT preservan su semántica **wall-clock** (sin convertir citas a UTC).
- Utilidades reutilizables y tests de regresión por fase.

---

## Convención oficial America/Matamoros

**Zona:** `America/Matamoros` (`TALLER_TIMEZONE` en `.env`).

| Tipo de dato | Almacenamiento BD | Serialización API | Display frontend |
|--------------|-------------------|-------------------|------------------|
| **Eventos de sistema** (caja, pagos, ventas, auditoría, movimientos, notificaciones) | UTC naive | ISO 8601 **con `Z`** | `formatearFechaHora` → Matamoros |
| **Citas** `fecha_hora` | Local naive taller | ISO **sin `Z`** | `formatearFechaHoraLocalNaive` |
| **Citas** `creado_en` | UTC naive | ISO **con `Z`** | `formatearFechaHora` |
| **OT** `fecha_ingreso` (TZ-1, desde 2026-06-17) | Local naive taller | ISO **sin `Z`** | `formatearFechaIngresoOtLocal` |
| **OT** `fecha_ingreso` legacy | UTC naive (histórico Railway) | ISO sin `Z` | Conversión backend `ingreso_ot_a_local_naive` |
| **Solo fecha** (vencimientos, registro cuenta, promesas calendario) | `Date` | `YYYY-MM-DD` | `formatearFechaSolo` |

**Regla de oro:** no mezclar en un mismo campo eventos UTC con fechas wall-clock del taller.

---

## Resumen por fase

### Fase 1 — Caja / histórico de turnos

| Área | Cambio |
|------|--------|
| API caja | `fecha_apertura` / `fecha_cierre` / pagos con `isoformat_utc` (`Z`) |
| Filtros histórico | `aplicar_filtro_rango_taller` (día Matamoros → rango UTC en SQL) |
| Schema | `TurnoOut` serializa fechas con `Z` |
| Export caja | `formatear_taller` en celdas Excel |
| Frontend | `formatearFechaHora` con `timeZone: America/Matamoros` |

### Fase 2 — Eventos de sistema extendidos

| Módulo | Cambio |
|--------|--------|
| Ventas / pagos (ingresos-detalle) | API `Z`; filtros `condiciones_rango_taller` |
| Dashboard agregado | Ventas/cobrado del periodo con filtros Matamoros |
| Auditoría | API `Z`; filtros Matamoros |
| Movimientos inventario / kardex | Schema `Z`; filtros Matamoros |
| Exportaciones | Ventas, utilidad, auditoría, ajustes inventario, devoluciones |

### Fase 3 — Módulos pendientes + frontend citas

| Módulo | Cambio |
|--------|--------|
| Citas | `fecha_hora` sin `Z`; `creado_en` con `Z`; filtros `condiciones_rango_local_naive` |
| Órdenes de compra | Eventos UTC+`Z`; `fecha_estimada_entrega` calendario |
| Cuentas por pagar manuales | Fechas `Date`; pagos con `Z` |
| Devoluciones | Filtros Matamoros; movimiento con `Z` |
| Dashboard `ordenes_hoy` | `ingreso_ot_en_dia_taller` (TZ-1 + legacy) |
| Notificaciones | `fecha_creacion` / `fecha_resolucion` con `Z` |
| Catálogos OT facturado | Filtros Pago/Venta Matamoros |
| Frontend citas | `formatearFechaHoraLocalNaive`, `localNaiveAFechaHoraForm` |

**Nota:** `fecha_ingreso` OT en serialización **no se modificó** en este commit; solo se ajustó la lógica de conteo `ordenes_hoy`.

---

## Commit y despliegue

| Campo | Valor |
|-------|-------|
| **SHA** | `0ffaa3d` |
| **Rama** | `main` |
| **Push** | `848c674..0ffaa3d` → `origin/main` ✅ |
| **Deploy Railway** | ✅ (502 transitorio ~30–90 s durante redeploy; luego estable) |
| **Health** | `GET /health` → `200 {"status":"healthy","database":"connected"}` |

---

## Evidencia de pruebas (pre-push)

### Tests backend — 28/28 PASS

```bash
pytest tests/test_timezone_utilidades.py \
       tests/test_timezone_caja.py \
       tests/test_timezone_fase2.py \
       tests/test_timezone_fase3.py \
       tests/test_tz1_fecha_ingreso.py -q
```

| Suite | Tests | Resultado |
|-------|-------|-----------|
| `test_timezone_utilidades.py` | 7 | ✅ |
| `test_timezone_caja.py` | 2 | ✅ |
| `test_timezone_fase2.py` | 4 | ✅ |
| `test_timezone_fase3.py` | 5 | ✅ |
| `test_tz1_fecha_ingreso.py` | 10 | ✅ |

### Build frontend

```bash
cd frontend && npm run build
```

✅ Sin errores de compilación.

### Exportaciones Excel (validación script, rollback transaccional)

| Export | UTC seed | Celda Matamoros | Resultado |
|--------|----------|-----------------|-----------|
| Caja | 13:39 UTC | `2026-06-30 08:39` | ✅ |
| Ventas | 15:00 UTC | `2026-06-30 10:00` | ✅ |
| Auditoría | 13:39:35 UTC | `2026-06-30 08:39:35` | ✅ |
| Ajustes inventario | 13:39 UTC | `2026-06-30 08:39` | ✅ |

---

## Smoke producción (post-push)

**Fecha smoke:** 30 de junio de 2026  
**Usuario:** admin producción (`rrabago@medinaautodiag.com`)

### API

| Check | Resultado |
|-------|-----------|
| Caja histórico `fecha_cierre` | `2026-06-30T13:39:35Z` ✅ |
| Citas `fecha_hora` | `2026-02-21T08:00:00` sin `Z` ✅ |
| Citas `fecha_hora` | `2026-02-21T16:30:00` sin `Z` ✅ |
| Dashboard `/api/dashboard` `ordenes_hoy` | `0` (dato real prod) ✅ |
| Export caja hoy | `200`, `.xlsx` válido (`PK`) ✅ |

### UI (browser)

| Pantalla | Observación | Resultado |
|----------|-------------|-----------|
| Dashboard | Carga OK; Órdenes hoy: 0; turno abierto visible | ✅ |
| Caja | Apertura: `30/6/2026, 8:38:42 a.m.` (hora local) | ✅ |
| Caja histórico | Sección y filtros Desde/Hasta visibles | ✅ |
| Citas listado | API `08:00` → UI `21/02/26, 8:00 a.m.` | ✅ |
| Citas listado | API `16:30` → UI `21/02/26, 4:30 p.m.` | ✅ |
| Citas `08:30` | Sin cita existente; `08:00` confirma wall-clock | ✅ parcial |
| Export caja | API devuelve Excel; no abierto en Excel desktop | ✅ API |

### Mutaciones prod no ejecutadas a propósito

Para evitar datos de prueba en producción, **no** se ejecutó:

- Crear cita nueva a las 08:30
- Editar cita y verificar conservación de hora
- Abrir/cerrar turno nuevo
- Abrir físicamente el Excel de export caja en desktop

Estos casos quedan como smoke opcional en ventana de mantenimiento.

---

## Pendientes — Fase 4 (no abierta)

| # | Ítem | Archivo / ámbito | Acción propuesta |
|---|------|------------------|------------------|
| 1 | Filtros con `func.date()` en eventos UTC | `app/routers/inventario_reportes.py` | Migrar a `condiciones_rango_taller` |
| 2 | `fecha_movimiento` sin `Z` en reporte in-app | `app/routers/inventario_reportes.py` | Usar `isoformat_utc` o schema con serializer |
| 3 | Pipeline CI GitHub | GitHub Actions | Verificar con `gh auth login` en máquina con acceso |

**Alcance Fase 4:** reporte in-app de ajustes de inventario. El kardex principal (`/api/inventario/movimientos/`) y export Excel de ajustes **sí** quedaron corregidos en Fases 2–3.

---

## Reglas obligatorias para futuros módulos

Al agregar o modificar campos de fecha/hora, aplicar **sin excepción**:

1. **Eventos de sistema** (caja, pagos, ventas, auditoría, movimientos, notificaciones, exports de eventos):  
   - BD: UTC naive  
   - API: ISO con **`Z`** (`isoformat_utc`)  
   - Frontend: `formatearFechaHora`  
   - Filtros día: `condiciones_rango_taller` o `aplicar_filtro_rango_taller` — **nunca** `func.date()` en columnas UTC

2. **Citas `fecha_hora`:**  
   - BD: local naive Matamoros  
   - API: ISO **sin `Z`** (`isoformat_local_naive_taller`)  
   - Frontend: `formatearFechaHoraLocalNaive` / `localNaiveAFechaHoraForm`  
   - **Prohibido** `formatearFechaHora` o `new Date(iso)` directo en `fecha_hora`

3. **Fechas calendario** (vencimiento, registro, promesa solo día):  
   - BD: `Date`  
   - API: `YYYY-MM-DD`  
   - Filtros: `condiciones_rango_fecha_solo`  
   - Frontend: `formatearFechaSolo`

4. **OT `fecha_ingreso` (TZ-1):**  
   - BD: local naive taller  
   - API: ISO **sin `Z`** (`isoformat_fecha_ingreso_ot`)  
   - Frontend: `formatearFechaIngresoOtLocal`  
   - Conteos por día: `ingreso_ot_en_dia_taller` (TZ-1 + legacy UTC)

**PRE-CHECK obligatorio** antes de tocar fechas en módulos nuevos: leer [TIMEZONE_POLICY.md](./TIMEZONE_POLICY.md) y reutilizar utilidades de `app/utils/fechas.py` / `frontend/src/utils/fechas.js`.

---

## Archivos principales del entregable

| Área | Archivos |
|------|----------|
| Utilidades | `app/utils/fechas.py`, `frontend/src/utils/fechas.js` |
| Documentación | `docs/TIMEZONE_POLICY.md` |
| Tests | `tests/test_timezone_*.py`, `tests/test_tz1_fecha_ingreso.py` |
| Routers F1–3 | `caja.py`, `ventas/`, `dashboard_agregado.py`, `auditoria.py`, `movimientos_inventario.py`, `exportaciones.py`, `citas.py`, `ordenes_compra.py`, `cuentas_pagar_manuales.py`, `devoluciones.py`, `notificaciones.py`, `ordenes_trabajo/catalogos.py` |
| Frontend citas | `Citas.jsx`, `Dashboard.jsx`, `Clientes.jsx`, `CitaOperativaCard.jsx` |

---

## Cierre

| Criterio | Estado |
|----------|--------|
| Política documentada | ✅ `TIMEZONE_POLICY.md` |
| Tests automatizados | ✅ 28 tests |
| Deploy producción | ✅ `0ffaa3d` en Railway |
| Smoke prod lectura | ✅ API + UI |
| Bugs nuevos detectados | Ninguno |
| Fase 4 | 🔲 Pendiente (inventario_reportes + gh CI) |

**Timezone Fases 1–3: CERRADO.**
