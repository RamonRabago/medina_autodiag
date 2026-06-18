# PLAN P6.0 — Multi-sucursal Foundation (Implementación futura)

**Versión:** 1.0  
**Fecha:** Junio 2026  
**Estado:** 📋 **PLAN DOCUMENTADO** — implementación **pendiente de autorización explícita**  
**ADR normativo:** [ADR_P6_0_MULTI_SUCURSAL.md](./ADR_P6_0_MULTI_SUCURSAL.md)  
**Checklist operativo:** [CHECKLIST_P6_0_MULTI_SUCURSAL.md](./CHECKLIST_P6_0_MULTI_SUCURSAL.md)  
**Relacionado:** [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md) · [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

## Resumen ejecutivo

P6.0 introduce la tabla **`sucursales`** y la columna **`sucursal_id`** en el núcleo transaccional (usuarios, OT, ventas, pagos, turnos caja, citas). Los registros nuevos se **etiquetan automáticamente** en el servidor según la sucursal del usuario. Los datos históricos se **backfillean** a Matamoros (`MAT`).

**P6.0 no filtra listados.** La UX operativa permanece igual hasta P6.1.

---

## Decisiones de alcance (recordatorio)

| Aprobado | Fuera de P6.0 |
|----------|---------------|
| Tabla `sucursales` | Inventario por sucursal |
| `usuarios.sucursal_id` | Timezone por sucursal |
| `ordenes_trabajo.sucursal_id` | Dashboard por sucursal |
| `ventas.sucursal_id` | Reportes por sucursal |
| `pagos.sucursal_id` | Filtros por sucursal |
| `caja_turnos.sucursal_id` | Multi-tenant |
| `citas.sucursal_id` | `usuario_sucursales` M:N |
| Clientes / vehículos globales | |

---

## Dependencias

| Dependencia | Estado |
|-------------|--------|
| TZ-1 Matamoros (`TALLER_TIMEZONE`) | ✅ Desplegado |
| Alembic como fuente de verdad | ✅ Vigente |
| P1–P5.1 cerrados | ✅ No modificar listados sin P6.1 |
| Autorización explícita por hito | 🔲 Pendiente al retomar |
| Usuarios Mante identificados en configuración | 🔲 Antes de P6.0.3 prod |

---

## Hitos de implementación

### P6.0.1 — Fundación de datos

**Objetivo:** Definir modelo y contrato de datos sin alterar comportamiento de lectura.

**Entregables (futuros):**

- Modelo SQLAlchemy `Sucursal` (`app/models/sucursal.py`).
- Registro en `app/models/__init__.py`.
- Schema Pydantic lectura (`SucursalOut`) — opcional `GET /api/sucursales`.
- Constantes seed: `MAT`, `MTE`.
- Documentación inline: **Sucursal ≠ Bodega**.

**Archivos previstos (referencia, no implementar ahora):**

- `app/models/sucursal.py`
- `app/schemas/sucursal_schema.py`
- `app/routers/sucursales.py` (solo `GET` lista activas, rol ADMIN)

**Criterios de aceptación:**

- [ ] Modelo compila; `from app.main import app` OK.
- [ ] Sin migración aplicada aún en este sub-hito si se prefiere separar; o migración solo `sucursales` vacía.

**Riesgos:**

- Crear modelo sin migración → desincronización; preferir 6.0.1+6.0.2 en mismo sprint.

---

### P6.0.2 — Migraciones y backfill

**Objetivo:** Esquema BD con columnas nullable, seed, backfill MAT, cierre NOT NULL.

**Estrategia en 3 despliegues (sin downtime):**

```text
Deploy A: CREATE sucursales + INSERT MAT/MTE + ADD COLUMN sucursal_id NULL
Deploy B: UPDATE backfill sucursal_id = 1 (MAT) en todas las tablas aprobadas
Deploy C: ALTER COLUMN NOT NULL + ADD FK + índices
```

**Migraciones Alembic previstas:**

| # | Contenido |
|---|-----------|
| `p6_0_01_sucursales` | Tabla `sucursales` + seed MAT (id=1), MTE (id=2) |
| `p6_0_02_sucursal_id_nullable` | `sucursal_id` nullable en usuarios, ordenes_trabajo, ventas, pagos, caja_turnos, citas |
| `p6_0_03_backfill_matamoros` | `UPDATE ... SET sucursal_id = 1 WHERE sucursal_id IS NULL` |
| `p6_0_04_sucursal_id_not_null` | NOT NULL + FK + índices `(sucursal_id)` |

**Backfill (convención negocio):**

| Tabla | Valor |
|-------|-------|
| Todas las filas existentes | `sucursal_id = 1` (Matamoros) |

**Verificación SQL post-backfill:**

```sql
SELECT 'ordenes_trabajo' t, COUNT(*) c FROM ordenes_trabajo WHERE sucursal_id IS NULL
UNION ALL SELECT 'ventas', COUNT(*) FROM ventas WHERE sucursal_id IS NULL
-- repetir por tabla aprobada
```

**Criterios de aceptación:**

- [ ] `alembic current` = head en prod tras deploy.
- [ ] 0 filas con `sucursal_id` NULL antes de migración NOT NULL.
- [ ] FK válidas; seed MAT/MTE presentes.

**Riesgos:**

- Migración NOT NULL con NULLs residuales → falla deploy; ejecutar verificación obligatoria.
- Orden de migraciones en Railway `preDeployCommand`.

**Rollback:**

- Antes de NOT NULL: revertir migración nullable (drop column) si no hay escrituras con sucursal.
- Tras NOT NULL: **no** drop column sin plan de contingencia; preferir forward-fix.

---

### P6.0.3 — Asignación de sucursal a usuarios

**Objetivo:** Cada usuario activo tiene `sucursal_id` correcto antes de habilitar stamp en producción.

**Tareas:**

1. Backfill automático: todos los usuarios existentes → `MAT` (id=1).
2. Configuración manual: usuarios que operan **solo en Mante** → `MTE` (id=2).
3. Pantalla o script ops: listar usuarios sin sucursal (debe ser 0).
4. Documentar en configuración quién es Mante vs Matamoros.

**Criterios de aceptación:**

- [ ] 100 % usuarios activos con `sucursal_id` NOT NULL.
- [ ] Lista de usuarios Mante validada por negocio.
- [ ] Nuevos usuarios: default `MAT` o obligatorio en alta (decisión en implementación).

**Riesgos:**

- Usuario Mante con `sucursal_id=MAT` → OT/ventas etiquetadas mal hasta corrección manual.

---

### P6.0.4 — Stamp automático de sucursal

**Objetivo:** Todo `INSERT` en entidades aprobadas recibe `sucursal_id` sin input del cliente.

**Helper propuesto:** `app/utils/sucursal_context.py`

- `resolver_sucursal_id(usuario: Usuario) -> int`
- `aplicar_sucursal(entidad, usuario)` en creación

**Puntos de escritura obligatorios:**

| Flujo | Servicio / router |
|-------|-------------------|
| OT normal / recepción rápida | `crud.py`, `recepcion_ot_service.py` |
| Cita → OT | `recepcion_ot_service.py` |
| Venta manual | `ventas_service.crear_venta` |
| Venta desde OT | `ventas_service` (ruta desde OT) |
| Pago | Router/servicio de pagos al crear `Pago` |
| Apertura turno caja | Router caja |
| Alta cita | Router citas |

**Reglas de stamp:**

| Entidad | Regla |
|---------|-------|
| `ordenes_trabajo` | `current_user.sucursal_id` |
| `ventas` | Usuario; si `id_orden` → copiar `orden.sucursal_id` |
| `caja_turnos` | `current_user.sucursal_id` |
| `pagos` | `venta.sucursal_id` (y coherencia con `turno.sucursal_id`) |
| `citas` | `current_user.sucursal_id` |

**Invariante:** el cliente **no** envía `sucursal_id` en body en P6.0.

**Criterios de aceptación:**

- [ ] Tests integración: POST recepción rápida → `sucursal_id` = usuario.
- [ ] Tests: venta desde OT → misma sucursal que OT.
- [ ] Tests: pago → misma sucursal que venta.
- [ ] Ningún `INSERT` aprobado sin stamp.

**Riesgos:**

- Rutas legacy o scripts que crean OT sin usuario → auditar `scripts/` y smokes.
- Transacción pago + turno de otra sucursal → validar coherencia venta/turno.

---

### P6.0.5 — JWT y contexto frontend

**Objetivo:** Sesión conoce la sucursal del usuario para UI futura; backend resuelve siempre desde BD.

**Backend (opciones, elegir una en implementación):**

- **A)** Claim JWT `sucursal_id` + `sucursal_codigo` en `create_access_token`.
- **B)** `GET /api/usuarios/me` con sucursal tras login.

**Frontend:**

- Extender `AuthContext` con `sucursal_id`, `sucursal_codigo`, `sucursal_nombre`.
- `Login.jsx`: leer claim o llamar `/me`.
- **Sin selector** de sucursal en P6.0.
- Badge opcional en `Layout` (solo informativo).

**Criterios de aceptación:**

- [ ] Tras login, `localStorage.user` incluye sucursal.
- [ ] Usuario Mante ve codigo `MTE` en sesión (si se implementa badge).
- [ ] Listados **sin** filtro por sucursal (comportamiento idéntico a hoy).

**Riesgos:**

- Frontend filtra por sucursal por error → bloquear en code review; solo P6.1.

---

### P6.0.6 — Validación y smoke

**Objetivo:** Evidencia prod/staging de stamp correcto sin regresión operativa.

**Smoke tests requeridos:**

| # | Escenario | Verificación |
|---|-----------|--------------|
| S1 | Usuario MAT crea OT recepción rápida | BD/API `sucursal_id=1` |
| S2 | Usuario MTE crea OT (tras P6.0.3) | BD/API `sucursal_id=2` |
| S3 | Venta desde OT MAT | `venta.sucursal_id` = OT |
| S4 | Pago sobre venta | `pago.sucursal_id` = venta |
| S5 | Apertura turno caja | `caja_turnos.sucursal_id` = usuario |
| S6 | Cita nueva | `citas.sucursal_id` = usuario |
| S7 | Listado Mi Taller / Órdenes | Sigue mostrando OT de ambas sucursales (sin filtro) |
| S8 | `GET /health`, `alembic current=head` | OK post-deploy |
| S9 | Regresión TZ-1 | `fecha_ingreso` coherente API/UI/PDF (sin cambio TZ) |

**Tests automatizados sugeridos:**

- `tests/test_p6_0_sucursal_stamp.py` (nuevo, en implementación).
- Ampliar smoke recepción rápida con assert `sucursal_id`.

**Criterios de cierre P6.0:**

- [ ] Todos los smoke S1–S9 PASS.
- [ ] Documento de cierre `CIERRE_P6_0_MULTI_SUCURSAL.md` (futuro).
- [ ] Commit(s) separados: migración / backend / frontend JWT.

---

## Estrategia de rollback

| Momento | Acción |
|---------|--------|
| Tras Deploy A (nullable) | Revert Alembic; drop columns si sin datos stamped |
| Tras Deploy B (backfill) | Forward-only; corregir IDs incorrectos con UPDATE |
| Tras Deploy C (NOT NULL) | **No** eliminar columnas en prod sin ventana; hotfix UPDATE si stamp erróneo |
| Stamp erróneo en prod | Script `UPDATE` puntual + fix en código; no redeploy destructivo |

**Principio:** P6.0 es aditivo. Rollback de aplicación sin revertir migración NOT NULL deja columnas obligatorias → coordinar versión app + BD.

---

## Orden de commits sugerido (al implementar)

1. `feat(p6.0): add Sucursal model and alembic foundation`
2. `feat(p6.0): backfill and not-null sucursal_id columns`
3. `feat(p6.0): stamp sucursal on operational writes`
4. `feat(p6.0): JWT and AuthContext sucursal`
5. `test(p6.0): integration tests and smoke scripts`
6. `docs(p6.0): cierre P6.0` (commit docs separado)

**No usar `git add .`** — stage explícito por tema.

---

## Qué NO hacer en P6.0

- Filtrar `GET /ordenes-trabajo`, A0, dashboard por sucursal.
- Agregar `sucursal_id` a `clientes`, `vehiculos`, `repuestos`.
- Reutilizar `bodegas` como sucursal.
- Cambiar `TALLER_TIMEZONE` por sucursal.
- Implementar `usuario_sucursales` M:N.

---

## Retomar en el futuro

1. Leer [ADR_P6_0_MULTI_SUCURSAL.md](./ADR_P6_0_MULTI_SUCURSAL.md) y este plan.
2. Ejecutar PRE-CHECK arquitectónico (metodología V2).
3. Obtener **autorización explícita** para P6.0.1.
4. Seguir [CHECKLIST_P6_0_MULTI_SUCURSAL.md](./CHECKLIST_P6_0_MULTI_SUCURSAL.md) hito a hito.
5. Al cerrar P6.0, planificar **P6.1** (filtros y reportes) antes de operación intensa en Mante.

---

**Estado final:** DOCUMENTADO / NO IMPLEMENTADO
