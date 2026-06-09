# Plan Operativo de Despliegue — Release Citas V2

**Versión:** 1.1  
**Fecha de creación:** 8 de junio de 2026  
**Estado:** Aprobación de ventana pendiente — **no ejecutar deploy sin Go/No-Go formal**  
**Alcance:** Backend Fase 1 + Frontend Fase 2 + Migración `b8c9d0e1f2a3` + QA producción + Rollback

**Referencias:**

- [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md)
- [PLAN_CITA_A_OT_V2.md](./PLAN_CITA_A_OT_V2.md)
- [QA_CITAS_FASE2_PRODUCCION.md](./QA_CITAS_FASE2_PRODUCCION.md)
- [LOGICA_CITAS.md](./LOGICA_CITAS.md)
- [RAILWAY_LECCIONES_APRENDIDAS.md](./RAILWAY_LECCIONES_APRENDIDAS.md)

**Commits objetivo en `main`:**

| Commit | Contenido |
|--------|-----------|
| `d903ebe` | Backend Fase 1 |
| `56d3ea1` | Frontend Fase 2 |
| `a6e463b` | QA producción (checklist) |
| `d2c50f9` | Plan corrección V2 |
| `50c0c1c` | LOGICA_CITAS alineada |

**Migración:** `b8c9d0e1f2a3` (head) — `cita_estado_historial` + `citas.estado_origen_cierre`

---

## Control de versiones del documento

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-06-08 | Plan operativo inicial |
| 1.1 | 2026-06-08 | Gate GO/NO-GO migración, evidencias QA obligatorias, matriz rollback clarificada |
| 1.2 | 2026-06-09 | **Cierre release producción — LIBERADO CON OBSERVACIONES** |

---

# RESUMEN EJECUTIVO

Release **acoplado** Citas Corrección de Estados V2. Un servicio Railway (Dockerfile multi-etapa) despliega **API + frontend** juntos. Migración vía `preDeployCommand = "alembic upgrade head"` en `railway.toml`.

**Riesgo principal:** código nuevo sin migración → PATCH falla.  
**Riesgo secundario:** mezcla de versiones frontend/backend → operación de estados rota.

**Regla de rollback:** solo **release completo** (backend + frontend juntos). No mezclar versiones.

**Ventana:** 90–105 min, fuera de hora pico, ADMIN + acceso MySQL + backup verificado.

---

# PREPARACIÓN PREVIA

## Accesos

GitHub, Railway Dashboard, MySQL producción, `APP_URL`, Railway CLI (opcional), cliente MySQL.

## Usuarios

ADMIN (obligatorio QA), EMPLEADO/CAJA/TECNICO (opcional permisos), datos cliente/vehículo de prueba.

## Herramientas

Navegador + DevTools, `git`, `curl`, cliente MySQL, checklist [QA_CITAS_FASE2_PRODUCCION.md](./QA_CITAS_FASE2_PRODUCCION.md).

## Riesgos conocidos

| Riesgo | Mitigación |
|--------|------------|
| preDeploy no ejecuta Alembic | Verificar logs; manual `alembic upgrade head` |
| Start Command Dashboard vs `railway.toml` | Alinear antes del deploy |
| Rollback solo frontend | **Prohibido** — ver matriz rollback |
| Downgrade schema post-uso | Backup; preferir hotfix forward |

---

# CHECKLIST PRE-DEPLOY

### Código

- [ ] `origin/main` incluye `d903ebe` y `56d3ea1`
- [ ] HEAD documentado: _______________
- [ ] Sin deploy concurrente de otra rama

### Railway

- [ ] Conectado a `main`
- [ ] `preDeployCommand = "alembic upgrade head"`
- [ ] Start Command no contradice `railway.toml`
- [ ] Variables: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `DEBUG_MODE=false`

### Base de datos

- [ ] Acceso MySQL OK
- [ ] `alembic current` pre-release anotado: _______________

### Operación

- [ ] ADMIN disponible
- [ ] Ventana comunicada al taller
- [ ] Backup programado
- [ ] Plan rollback revisado
- [ ] Plantilla evidencias QA preparada (§ EVIDENCIAS QA)

---

# BACKUP

## Tablas obligatorias

`citas`, `cita_estado_historial` (si existe), `auditorias`, `ordenes_trabajo`, `alembic_version`

## Comando sugerido

```bash
mysqldump -h <HOST> -P <PORT> -u <USER> -p \
  --single-transaction --routines --triggers \
  <DB> citas auditorias ordenes_trabajo alembic_version \
  > backup_citas_v2_pre_YYYYMMDD_HHMM.sql
```

## Tiempo estimado

10–20 min (dump + validación + almacenamiento seguro)

## Validación

- [ ] Archivo > 0 bytes, contiene `citas` y `alembic_version`
- [ ] Ruta, fecha, responsable anotados

---

# DESPLIEGUE

### Paso 1 — Deploy (backend + frontend embebido)

Railway → Deploy latest from `main`. Monitorear build Docker (Node + Python).

### Paso 2 — Frontend

Cubierto en Paso 1 (`frontend/dist` en imagen). Verificar `npm run build` OK en logs.

### Paso 3 — Confirmar release activo

- [ ] Deployment **Success**, commit SHA ≥ `56d3ea1`
- [ ] `curl -sI $APP_URL/` → 200

### Paso 4 — Verificar logs

Build → preDeploy Alembic → uvicorn sin traceback.

---

# MIGRACIÓN

### Verificación previa

```bash
alembic current
# Pre-release esperado: a7b8c9d0e1f2
```

### Ejecución

Automática en `preDeployCommand`. Manual solo si falló:

```bash
alembic upgrade head
```

### Verificación posterior

```bash
alembic current   # → b8c9d0e1f2a3 (head)
```

### Validaciones SQL

```sql
SHOW TABLES LIKE 'cita_estado_historial';
SHOW COLUMNS FROM citas LIKE 'estado_origen_cierre';
SELECT * FROM alembic_version;
```

---

# GO / NO-GO MIGRACIÓN

> **Ubicación en el flujo:** después de verificación post-migración (Alembic + SQL), **antes** de smoke tests y QA funcional.

Gate formal. Responsable de release firma Go o No-Go.

### Criterios GO (todos obligatorios)

- [ ] `alembic current` = `b8c9d0e1f2a3`
- [ ] Tabla `cita_estado_historial` existe
- [ ] Columna `citas.estado_origen_cierre` existe
- [ ] API responde correctamente (`GET /` o health → 200)
- [ ] Login ADMIN funciona
- [ ] No existen errores 500 ni tracebacks en logs de arranque (últimos 5 min)

**Decisión GO:** _______________  **Hora:** _______________  **Firma responsable:** _______________

→ Continuar con **Validación post-migración (smoke)** y **QA producción**.

### Criterios NO-GO (cualquiera dispara parada)

- Migración incompleta o revision distinta de `b8c9d0e1f2a3`
- Tabla `cita_estado_historial` faltante
- Columna `estado_origen_cierre` faltante
- Error Alembic en logs preDeploy
- API caída o no responde
- Login ADMIN falla
- Tracebacks en logs de arranque

**Decisión NO-GO:** _______________  **Hora:** _______________  **Motivo:** _______________

### Acción si NO-GO

1. **Detener QA** — no iniciar pruebas funcionales
2. **No liberar** operación
3. **Evaluar rollback** según § PLAN DE ROLLBACK
4. Post-mortem antes de reintentar

**No continuar** con smoke tests ni QA hasta resolver o hacer rollback total.

---

# VALIDACIÓN POST-MIGRACIÓN (Smoke)

> Solo ejecutar si gate **GO** aprobado.

| # | Prueba | OK |
|---|--------|-----|
| 1 | API responde | ☐ |
| 2 | Login ADMIN | ☐ |
| 3 | Listado citas | ☐ |
| 4 | Detalle cita | ☐ |
| 5 | PATCH estado (cita prueba) | ☐ |
| 6 | Conversión OT | ☐ |

Fallo en 5–6 → evaluar rollback; no liberar.

---

# QA PRODUCCIÓN

Referencia detallada: [QA_CITAS_FASE2_PRODUCCION.md](./QA_CITAS_FASE2_PRODUCCION.md)

**Orden:** Infra (1–4) → Flujos UI (5–15) → Integridad (16–17) → Regresión (18–19)  
**Duración:** 50–70 min QA completo; ventana total ~105 min con buffer  
**Aprobación:** ítems 1–19 OK; evidencias § EVIDENCIAS QA completas

---

# EVIDENCIAS QA

Registrar en cada liberación. Adjuntar al **Cierre de liberación**.

### Plantilla — Cita creada (QA)

| Campo | Valor |
|-------|-------|
| ID cita | |
| Fecha/hora cita | |
| Usuario | |
| Timestamp prueba | |

### Plantilla — Corrección de estado

| Campo | Valor |
|-------|-------|
| ID cita | |
| Estado anterior | |
| Estado nuevo | |
| motivo_codigo | |
| motivo_detalle (si aplica) | |
| Usuario | |

### Plantilla — Conversión OT

| Campo | Valor |
|-------|-------|
| ID cita | |
| ID OT | |
| Usuario | |
| Timestamp | |

### Plantilla — Historial (SQL o captura)

```sql
SELECT id, id_cita, estado_anterior, estado_nuevo, origen, creado_en
FROM cita_estado_historial
WHERE id_cita IN (<IDs QA>)
ORDER BY id_cita, creado_en;
```

- [ ] Captura / export adjunto
- [ ] Eventos `CREACION`, `MANUAL`, `CONVERTIR_OT` según pruebas ejecutadas

### Plantilla — estado_origen_cierre

```sql
-- Tras primera marcación (ej. CONFIRMADA → SI_ASISTIO)
SELECT id_cita, estado, estado_origen_cierre FROM citas WHERE id_cita = <ID>;

-- Tras corrección posterior
SELECT id_cita, estado, estado_origen_cierre FROM citas WHERE id_cita = <ID>;
```

- [ ] Valor inicial anotado: _______________
- [ ] Valor post-corrección anotado: _______________
- [ ] Confirmado **sin cambio** en `estado_origen_cierre`: ☐ Sí

### Plantilla — Network (DevTools)

- [ ] Captura mostrando `PATCH /api/citas/{id}/estado` (status 200)
- [ ] Captura confirmando **ausencia** de `PUT` con campo `estado` en cambios de estado
- [ ] Captura `PUT /api/citas/{id}` en edición normal **sin** `estado` (regresión)

### Resultado final del release

| Decisión | Marcar |
|----------|--------|
| LIBERADO | ☐ |
| LIBERADO CON OBSERVACIONES | ☐ |
| ROLLBACK | ☐ |

**Observaciones / incidencias:** _______________________________________________

**Evidencias adjuntas (lista):** _______________________________________________

**Responsable cierre:** _______________  **Fecha/hora:** _______________

---

# CRITERIOS DE LIBERACIÓN

### LIBERADO

Gate GO + QA 1–19 OK + evidencias completas + backup verificado.

### LIBERADO CON OBSERVACIONES

Core OK; observaciones menores documentadas; plan seguimiento ≤ 48h; evidencias core presentes.

### ROLLBACK

Gate NO-GO; PATCH/OT roto; 500 sistemático; schema inconsistente; decisión explícita post-mortem.

---

# PLAN DE ROLLBACK

## Regla operativa

> **Si se requiere rollback: hacer rollback del release completo. No mezclar versiones.**

---

## Matriz de rollback

### Rollback soportado

| Escenario | Acción | Notas |
|-----------|--------|-------|
| ✅ **Backend + Frontend juntos** | Redeploy / revert a commit pre-V2 (ej. `caf4f7f`) | Restaura coherencia PUT legacy + UI legacy |
| ✅ **Rollback total** | Restore backup (si corrupción) + `alembic downgrade a7b8c9d0e1f2` + redeploy `caf4f7f` | Destructivo; ventana mantenimiento |

### Rollback NO soportado

| Escenario | Motivo |
|-----------|--------|
| ❌ **Solo frontend** (revert `56d3ea1`, backend en `d903ebe`) | Frontend viejo usa `PUT` con `estado`. Backend nuevo **rechaza** PUT con estado → botones rotos |

### Rollback NO recomendado

| Escenario | Motivo |
|-----------|--------|
| ❌ **Solo backend** (revert `d903ebe`, frontend en `56d3ea1`) | Frontend nuevo consume `PATCH` y `estado_meta`. Backend legacy no expone contrato completo → UI parcialmente incompatible |

---

## Procedimientos

### Rollback release completo (recomendado)

1. Comunicar ventana; detener cambios de estado en citas
2. Redeploy commit **`caf4f7f`** (o revert conjunto `56d3ea1` + `d903ebe`)
3. Smoke: listado citas, PUT estado, convertir OT
4. Evaluar si downgrade schema necesario (solo si migración causa conflicto en código legacy)

### Rollback migración (destructivo)

```bash
alembic downgrade a7b8c9d0e1f2
```

```sql
DROP TABLE IF EXISTS cita_estado_historial;
ALTER TABLE citas DROP COLUMN estado_origen_cierre;
```

**Riesgo:** pérdida de historial y `estado_origen_cierre`. Solo si no hubo uso productivo o se restaura backup.

### Rollback total

Backup restore → downgrade → redeploy `caf4f7f` → smoke → post-mortem.

**Tiempo estimado:** 30–60 min.

---

# RESPONSABLES

| Actividad | Responsable | Estado |
|-----------|-------------|--------|
| Go/No-Go pre-deploy | | ☐ |
| Backup + validación | | ☐ |
| Trigger deploy | | ☐ |
| Monitoreo logs / preDeploy | | ☐ |
| **Gate GO/NO-GO migración** | | ☐ |
| Smoke post-migración | | ☐ |
| QA producción + evidencias | | ☐ |
| Decisión LIBERADO / ROLLBACK | | ☐ |
| Comunicación taller | | ☐ |

---

# CRONOGRAMA RECOMENDADO

| Hora | Actividad | Duración |
|------|-----------|----------|
| T-1 | Pre-deploy checklist | 30 min |
| 09:00 | Backup | 15 min |
| 09:15 | Deploy Railway | 10–20 min |
| 09:30 | Verificación Alembic + SQL | 10 min |
| **09:40** | **Gate GO/NO-GO migración** | **5 min** |
| 09:45 | Smoke (si GO) | 10 min |
| 09:55 | QA producción | 45 min |
| 10:40 | Evidencias SQL + Network | 15 min |
| 10:55 | Decisión + cierre liberación | 15 min |
| 11:10 | Comunicación operación | 5 min |

**Ventana total:** ~105 min.

---

**Próxima revisión:** tras Fase 3 (reportes) o Fase 4 (bloqueo financiero).

---

# CIERRE DE RELEASE — PRODUCCIÓN

**Fecha/hora cierre:** 9 de junio de 2026  
**Entorno:** Producción — `https://medinaautodiag.up.railway.app`  
**Proyecto Railway:** `disciplined-adaptation` · servicio `web` · environment `production`  
**Deploy ejecutado:** `railway up` — deployment `e81a9c9d-134a-4bfa-8329-b9ecb33a25e7`  
**Commit desplegado (repo):** `50c0c1c` (incluye código Fase 1 `d903ebe` + Fase 2 `56d3ea1`)  
**Revisión Alembic prod:** `b8c9d0e1f2a3` (ya aplicada pre-deploy)

## Decisión final

### **LIBERADO CON OBSERVACIONES**

Funcionalidad core de Corrección de Estados V2 operativa en producción. Observaciones menores documentadas abajo; plan de seguimiento ≤ 48 h no bloqueante.

---

## Ejecución de la ventana

| Paso | Resultado | Evidencia |
|------|-----------|-----------|
| Pre-deploy | ✅ GO | `main` con Fase 1+2; Railway link OK |
| Backup | ✅ GO | `backups/backup_citas_v2_pre_20260609_0832.sql` (~20 KB) |
| Deploy | ✅ GO | Build OK; Uvicorn startup OK |
| Gate GO/NO-GO migración | ✅ GO | Schema + API + login ADMIN |
| Smoke API | ✅ GO | HTTP 200; bundle `Citas-D2icVTjl.js` con PATCH |
| QA producción | ✅ Parcial completo | Ver tabla abajo |
| Rollback | ❌ No aplicado | — |

---

## QA producción — resultados

| # | Prueba | Resultado | Notas |
|---|--------|-----------|-------|
| 1 | Commit / deploy activo | ✅ | Fase 2 frontend en prod |
| 2–4 | Alembic + schema | ✅ | Pre-existente `b8c9d0e1f2a3` |
| 5 | Crear cita | ⏸ | No ejecutado en sesión (citas reales usadas) |
| 6–7 | CONFIRMADA → SI/NO | ✅ | Cita #4 Damaris (flujo completo) |
| 8 | CONFIRMADA → CANCELADA | ✅ | Motivo: *EL CLIENTE TUVO UN PROBLEMA Y AVISO QUE NO VENDRIA* |
| 9–12 | Correcciones | ✅ | NO→CONF, SI→CONF, CONF→SI; modal + motivos |
| 13 | Convertir a OT | ✅ | Erick Torres → **OT-20260609-0001** (`id_orden` 10) |
| 14 | NO_ASISTIO bloquea OT | ✅ | Mensaje UI + reglas backend |
| 15 | Ver OT | ✅ | Detalle OT-20260609-0001 |
| 16 | Historial | ✅ | `cita_estado_historial` poblado (ej. cita #4) |
| 17 | `estado_origen_cierre` | ✅ | Cita #4: `NO_ASISTIO` inmutable tras correcciones |
| 18 | PUT editar sin `estado` | ⏸ | No probado explícitamente en sesión |
| 19 | Sin PUT con `estado` / Network PATCH | ⚠️ | PATCH verificado por UI+BD; **captura DevTools no archivada** |

### Citas de prueba / evidencia operativa

| id_cita | Cliente | Flujos probados |
|---------|---------|-----------------|
| 4 | Damaris Berrones Alfaro | NO→CONF→SI→CONF; cancelación; `estado_origen_cierre=NO_ASISTIO` |
| 2 | Erick Torres | Convertir a OT → OT-20260609-0001 |

---

## Observaciones (motivo LIBERADO CON OBSERVACIONES)

1. **Captura Network DevTools** de `PATCH /api/citas/{id}/estado` no adjuntada al cierre (comportamiento validado por UI, confirmación modal y filas en `cita_estado_historial`).
2. **PUT editar cita** sin campo `estado` no re-probado en UI en esta sesión (sin cambio de contrato en Fase 2; riesgo bajo).
3. **Crear cita nueva** de QA dedicada no ejecutada; se usaron citas operativas reales.
4. **Migración** ya estaba aplicada antes del deploy de código; ventana coordinada cumplida en schema, deploy enfocado en binarios/UI.
5. **Roles no-ADMIN** (CAJA/EMPLEADO/TECNICO post-24h) no probados en prod en esta sesión; reglas documentadas en [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md).

---

## Seguimiento post-liberación (≤ 48 h)

| # | Acción | Prioridad |
|---|--------|-----------|
| 1 | Comunicar a recepción: correcciones post-24h solo **ADMIN** | Alta |
| 2 | Archivar captura PATCH en próxima corrección real (opcional) | Baja |
| 3 | Probar PUT editar sin `estado` en turno recepción | Baja |
| 4 | Iniciar Fase 3 (reportes operativo vs calidad) cuando se priorice | Roadmap |

---

## Incidencias de release

| ID | Descripción | Resolución |
|----|-------------|------------|
| INC-001 | Sin DATABASE_URL local | Backup vía Railway CLI |
| INC-002 | Login browser falló | `login --browserless` OK |
| INC-003 | Agente no-interactivo | Login en CMD operador; luego CLI compartido |

---

## Responsables (cierre)

| Actividad | Responsable | Estado |
|-----------|-------------|--------|
| Go/No-Go pre-deploy | Operador / Release | ☑ |
| Backup + validación | Agente + operador | ☑ |
| Trigger deploy | Agente (`railway up`) | ☑ |
| Gate GO/NO-GO migración | Release Manager | ☑ GO |
| QA producción | Operador (ADMIN prod) | ☑ |
| Decisión final | Operador | ☑ **LIBERADO CON OBSERVACIONES** |
| Comunicación taller | Pendiente operador | ☐ |

---

## Rollback

**No requerido.** Backup disponible: `backups/backup_citas_v2_pre_20260609_0832.sql`.  
Regla vigente: rollback solo **release completo** (backend + frontend); no mezclar versiones.

