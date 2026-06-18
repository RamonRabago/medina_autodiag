# CHECKLIST P6.0 — Multi-sucursal Foundation

**Versión del documento:** 1.0  
**Fecha:** Junio 2026  
**ADR:** [ADR_P6_0_MULTI_SUCURSAL.md](./ADR_P6_0_MULTI_SUCURSAL.md)  
**Plan:** [PLAN_P6_0_IMPLEMENTACION.md](./PLAN_P6_0_IMPLEMENTACION.md)  
**Estado:** ⬜ **NO INICIADO** — usar el día que se autorice implementación

**Leyenda:**

- `[ ]` — Pendiente
- `[PASS]` — Verificado OK
- `[FAIL]` — No cumple; bloquear cierre

---

## 1. Pre-implementación

| # | Verificación | Resultado |
|---|--------------|-----------|
| 1.1 | ADR P6.0 leído y vigente | [ ] |
| 1.2 | PLAN P6_0_IMPLEMENTACION leído | [ ] |
| 1.3 | PRE-CHECK arquitectónico V2 completado y reportado | [ ] |
| 1.4 | Autorización explícita del usuario para implementar P6.0 | [ ] |
| 1.5 | Confirmado: **no** filtrar listados en P6.0 | [ ] |
| 1.6 | Confirmado: clientes y vehículos **globales** | [ ] |
| 1.7 | Confirmado: **Sucursal ≠ Bodega** comunicado al equipo | [ ] |
| 1.8 | Lista de usuarios Mante vs Matamoros preparada | [ ] |
| 1.9 | `TALLER_TIMEZONE=America/Matamoros` sin cambios planeados | [ ] |
| 1.10 | Rama de trabajo creada; sin mezclar docs + código en un commit | [ ] |

---

## 2. Migraciones

| # | Verificación | Resultado |
|---|--------------|-----------|
| 2.1 | Migración `sucursales` creada (id, codigo, nombre, activa, created_at) | [ ] |
| 2.2 | Seed `MAT` (Matamoros) y `MTE` (Cd. Mante) | [ ] |
| 2.3 | Columnas `sucursal_id` nullable en: usuarios, ordenes_trabajo, ventas, pagos, caja_turnos, citas | [ ] |
| 2.4 | Backfill: todas las filas existentes → `sucursal_id = 1` (MAT) | [ ] |
| 2.5 | Query verificación: 0 NULL en cada tabla antes de NOT NULL | [ ] |
| 2.6 | Migración NOT NULL + FK + índices aplicada | [ ] |
| 2.7 | `alembic upgrade head` OK en local/staging | [ ] |
| 2.8 | `alembic current` = head en producción post-deploy | [ ] |
| 2.9 | Sin migración en `repuestos`, `bodegas`, `movimientos_inventario` | [ ] |

---

## 3. Backend

| # | Verificación | Resultado |
|---|--------------|-----------|
| 3.1 | Modelo `Sucursal` registrado | [ ] |
| 3.2 | Helper `sucursal_context` (resolver + aplicar) | [ ] |
| 3.3 | Stamp OT: POST `/ordenes-trabajo/`, `/recepcion-rapida` | [ ] |
| 3.4 | Stamp OT: cita → OT (`recepcion_ot_service`) | [ ] |
| 3.5 | Stamp `ventas` en creación manual y desde OT | [ ] |
| 3.6 | Stamp `pagos.sucursal_id` al registrar pago | [ ] |
| 3.7 | Stamp `caja_turnos` al abrir turno | [ ] |
| 3.8 | Stamp `citas` al crear | [ ] |
| 3.9 | Cliente **no** puede enviar `sucursal_id` en body (ignorado/rechazado) | [ ] |
| 3.10 | Responses opcionales incluyen `sucursal_id` o `sucursal_codigo` en detalle | [ ] |
| 3.11 | **Sin** filtro por sucursal en listados GET (P6.0) | [ ] |
| 3.12 | `GET /api/sucursales` (lista activas) si se implementó | [ ] |
| 3.13 | `python -c "from app.main import app"` OK | [ ] |
| 3.14 | Tests integración stamp PASS | [ ] |

---

## 4. Frontend

| # | Verificación | Resultado |
|---|--------------|-----------|
| 4.1 | `AuthContext` almacena sucursal (id/codigo/nombre) | [ ] |
| 4.2 | Login carga sucursal desde JWT o `/me` | [ ] |
| 4.3 | **Sin** selector de sucursal en UI (P6.0) | [ ] |
| 4.4 | Listados (Órdenes, Mi Taller, Caja) sin filtro sucursal | [ ] |
| 4.5 | `npm run build` PASS | [ ] |
| 4.6 | Sin regresión visual en flujos P1–P5.1 críticos | [ ] |

---

## 5. JWT

| # | Verificación | Resultado |
|---|--------------|-----------|
| 5.1 | Token incluye `sucursal_id` (o equivalente vía `/me`) | [ ] |
| 5.2 | Login usuario MAT → sucursal 1 / codigo MAT | [ ] |
| 5.3 | Login usuario MTE → sucursal 2 / codigo MTE | [ ] |
| 5.4 | Backend resuelve sucursal desde BD si claim ausente (defensa) | [ ] |
| 5.5 | Usuario inactivo / sin sucursal → error claro | [ ] |

---

## 6. Producción

| # | Verificación | Resultado |
|---|--------------|-----------|
| 6.1 | Push autorizado; `build_rev` desplegado coincide con commit P6.0 | [ ] |
| 6.2 | `GET /health` → 200 | [ ] |
| 6.3 | `alembic current` = head | [ ] |
| 6.4 | Usuarios Mante con `sucursal_id=2` en BD | [ ] |
| 6.5 | Resto usuarios con `sucursal_id=1` (MAT) | [ ] |
| 6.6 | Sin incidentes en operación Matamoros durante deploy | [ ] |
| 6.7 | `TALLER_TIMEZONE` sin cambios no planificados | [ ] |

---

## 7. Smoke tests

| # | Escenario | Resultado |
|---|-----------|-----------|
| 7.1 | **S1** Usuario MAT: recepción rápida → OT con `sucursal_id=1` en BD y API | [ ] |
| 7.2 | **S2** Usuario MTE: recepción rápida → OT con `sucursal_id=2` | [ ] |
| 7.3 | **S3** Venta desde OT: `venta.sucursal_id` = OT | [ ] |
| 7.4 | **S4** Pago: `pago.sucursal_id` = venta | [ ] |
| 7.5 | **S5** Turno caja: `caja_turnos.sucursal_id` = usuario | [ ] |
| 7.6 | **S6** Cita nueva: `citas.sucursal_id` = usuario | [ ] |
| 7.7 | **S7** Mi Taller / listado OT muestra ambas sucursales (sin filtro) | [ ] |
| 7.8 | **S8** TZ-1: fecha_ingreso coherente API / Modal / PDF | [ ] |
| 7.9 | OT histórica (pre-P6.0) tiene `sucursal_id=1` (MAT) | [ ] |

---

## 8. Rollback

| # | Verificación | Resultado |
|---|--------------|-----------|
| 8.1 | Plan de rollback documentado antes del deploy prod | [ ] |
| 8.2 | Backup BD o snapshot Railway disponible | [ ] |
| 8.3 | Si FAIL crítico: procedimiento acordado (revert app vs hotfix data) | [ ] |
| 8.4 | Post-mortem si hubo `[FAIL]` en producción | [ ] |

---

## 9. Cierre P6.0

| # | Verificación | Resultado |
|---|--------------|-----------|
| 9.1 | Todos los ítems críticos (§2–7) en `[PASS]` | [ ] |
| 9.2 | `CIERRE_P6_0_MULTI_SUCURSAL.md` creado (commit docs separado) | [ ] |
| 9.3 | P6.1 (filtros/reportes) planificado; no mezclado en P6.0 | [ ] |
| 9.4 | Veredicto final: **P6.0 PASS** / **P6.0 FAIL** | [ ] |

---

## Veredicto global

| Campo | Valor |
|-------|-------|
| **Fecha cierre** | |
| **Commit(s) P6.0** | |
| **build_rev prod** | |
| **Resultado** | [ ] PASS  [ ] FAIL |
| **Recomendación** | [ ] GO P6.1  [ ] HOLD |

---

**Estado actual del checklist:** ⬜ NO INICIADO — DOCUMENTADO / NO IMPLEMENTADO
