# QA Producción — Citas Fase 1 (Backend) + Fase 2 (Frontend)

**Fecha de creación:** 8 de junio de 2026  
**Versión del documento:** 1.0  
**Estado:** Pendiente de ejecución post-deploy  
**Alcance:** Validar deploy conjunto backend Fase 1 + frontend Fase 2 con migración Alembic `b8c9d0e1f2a3`.

---

## Referencias

| Documento | Propósito |
|-----------|-----------|
| [PLAN_CORRECCION_ESTADO_CITAS_V2.md](./PLAN_CORRECCION_ESTADO_CITAS_V2.md) | Diseño de transiciones gobernadas, historial, roles y fases 1–4 |
| [PLAN_CITA_A_OT_V2.md](./PLAN_CITA_A_OT_V2.md) | Conversión cita → OT, elegibilidad por estado, vínculo `id_orden` |
| [LOGICA_CITAS.md](./LOGICA_CITAS.md) | Ciclo de vida, campos y flujos operativos del módulo Citas |

**Commits objetivo en `main`:**

| Componente | Commit | Mensaje |
|------------|--------|---------|
| Backend Fase 1 | `d903ebe` | `feat(citas): add governed status transitions with history` |
| Frontend Fase 2 | `56d3ea1` | `feat(citas): migrate status UI to PATCH state transitions` |

**Migración Alembic:** `b8c9d0e1f2a3` — `cita_estado_historial` + `citas.estado_origen_cierre`  
**Head esperado:** `b8c9d0e1f2a3`

---

## Control de versiones del documento

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-06-08 | Versión inicial: pre-deploy, checklist QA (20 ítems), cierre de liberación y rollback |

---

## Pre-Deploy Obligatorio

Completar **antes** de autorizar el deploy a producción. No desplegar si algún ítem crítico falla.

### A. Código en `main`

```bash
git fetch origin
git log origin/main -2 --oneline
```

**Esperado (orden descendente):**

```
56d3ea1 feat(citas): migrate status UI to PATCH state transitions
d903ebe feat(citas): add governed status transitions with history
```

- [ ] `origin/main` incluye `56d3ea1` (frontend Fase 2)
- [ ] `origin/main` incluye `d903ebe` (backend Fase 1)
- [ ] No hay commits pendientes de push en la máquina local de quien autoriza

### B. Build local (sanity check previo)

```powershell
cd c:\medina_autodiag_api\frontend
npm run build
```

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1
python -c "from app.main import app; print('OK')"
```

- [ ] `npm run build` OK
- [ ] Import backend OK

### C. Migración Alembic

Revisar `railway.toml`:

```toml
preDeployCommand = "alembic upgrade head"
```

- [ ] `preDeployCommand` configurado (no `alembic` en `startCommand`)
- [ ] Head local = `b8c9d0e1f2a3` (`alembic heads`)
- [ ] Revisión anterior en prod conocida: `a7b8c9d0e1f2` (verificar con `alembic current` en prod si es posible)

### D. Backup de base de datos

```bash
mysqldump -h <HOST> -u <USER> -p <DB> \
  citas alembic_version > backup_pre_citas_estados_v2_$(date +%Y%m%d).sql
```

- [ ] Backup de tabla `citas` y `alembic_version` realizado
- [ ] Backup almacenado y accesible para rollback

### E. Variables y configuración Railway

- [ ] `DATABASE_URL` apunta a MySQL producción correcto
- [ ] `ALLOWED_ORIGINS` incluye URL frontend producción
- [ ] Start Command del dashboard **no** sobrescribe `railway.toml` con `alembic` en arranque (ver [RAILWAY_LECCIONES_APRENDIDAS.md](./RAILWAY_LECCIONES_APRENDIDAS.md))

### F. Coordinación operativa

- [ ] Ventana de deploy acordada (evitar hora pico del taller)
- [ ] Usuario ADMIN disponible para QA inmediato post-deploy
- [ ] Este checklist impreso o abierto para marcar ítems en vivo
- [ ] Plan de rollback revisado (sección final de este documento)

### G. Orden de deploy acordado

1. Deploy conjunto backend + frontend desde `main`
2. Confirmar en logs que `preDeployCommand` ejecutó `alembic upgrade head`
3. Ejecutar checklist QA (secciones 1–19) de inmediato
4. Cierre de liberación (sección dedicada) si todo verde

---

## Variables para la sesión QA

| Variable | Descripción |
|----------|-------------|
| `APP_URL` | URL producción (ej. `https://medina-autodiag-production-xxxx.up.railway.app`) |
| `TOKEN` | JWT usuario **ADMIN** (y opcionalmente EMPLEADO / TECNICO) |
| `ID_CITA_*` | IDs anotados durante pruebas para consultas SQL |

**Roles recomendados:**

| Prueba | Rol mínimo |
|--------|------------|
| Marcación inicial (6–8) | ADMIN, EMPLEADO, CAJA o TECNICO |
| Correcciones (9–12) | ADMIN (o EMPLEADO/CAJA dentro ventana 24h) |
| Convertir a OT (13) | Rol con recepción rápida |
| Cita con OT + corrección | Solo ADMIN |

**Preparación UI:** Citas → DevTools → Network → **Preserve log** activado.

---

## FASE A — Infraestructura y schema

### 1. Verificar que Railway tomó el commit `56d3ea1`

**GitHub:**

```bash
git fetch origin
git log origin/main -1 --oneline
# Esperado: 56d3ea1 feat(citas): migrate status UI to PATCH state transitions
```

**Railway Dashboard:**

- Servicio backend → **Deployments** → commit activo incluye `56d3ea1`
- Servicio frontend (si separado) → mismo commit o build que incluya Fase 2

**Smoke HTTP:**

```bash
curl -sI "$APP_URL/" | head -5
```

En navegador: Citas → Network → asset `Citas-*.js` del build post-Fase 2.

- [ ] Deploy activo = `56d3ea1` o posterior sin revertir Fase 2

---

### 2. Ejecutar o confirmar `alembic upgrade head`

Buscar en logs del deploy:

```
INFO  [alembic.runtime.migration] Running upgrade a7b8c9d0e1f2 -> b8c9d0e1f2a3
```

**Manual (solo si preDeploy no corrió):**

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL="mysql+pymysql://..."   # Railway Variables
alembic current
alembic upgrade head
alembic current
# Esperado: b8c9d0e1f2a3 (head)
```

- [ ] Revisión Alembic = `b8c9d0e1f2a3`

---

### 3. Confirmar tabla `cita_estado_historial`

```sql
SHOW TABLES LIKE 'cita_estado_historial';

DESCRIBE cita_estado_historial;
-- Esperado: id, id_cita, estado_anterior, estado_nuevo, motivo_codigo,
--           motivo_detalle, id_usuario, id_orden, origen, creado_en

SHOW INDEX FROM cita_estado_historial;
-- Esperado: ix_cita_estado_historial_id_cita, ix_cita_estado_historial_id
```

- [ ] Tabla existe con columnas e índices correctos

---

### 4. Confirmar columna `citas.estado_origen_cierre`

```sql
SHOW COLUMNS FROM citas LIKE 'estado_origen_cierre';
-- Esperado: ENUM('CONFIRMADA','SI_ASISTIO','NO_ASISTIO','CANCELADA') NULL
```

- [ ] Columna presente y nullable

---

## FASE B — Pruebas funcionales UI

### 5. Probar crear cita

1. Citas → **Nueva cita** → cliente, fecha futura, hora, tipo, motivo → **Guardar**
2. Verificar en listado: estado **Confirmada**

**API (opcional):**

```bash
curl -s -X POST "$APP_URL/api/citas/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id_cliente":1,"fecha_hora":"2026-06-15T10:00:00","tipo":"REVISION","motivo":"QA Fase 2"}'
```

- [ ] Cita creada, `estado = CONFIRMADA`, sin error 500  
- [ ] `ID_CITA_5` = ___________

---

### 6. CONFIRMADA → SI_ASISTIO

Detalle → **Sí asistió**.

**Network esperado:**

```
PATCH /api/citas/{id}/estado
Body: { "estado_nuevo": "SI_ASISTIO" }
Status: 200
```

**NO debe aparecer:** `PUT /api/citas/{id}` con campo `estado`.

- [ ] Badge **Sí asistió**, toast éxito  
- [ ] `ID_CITA_6` = ___________

---

### 7. CONFIRMADA → NO_ASISTIO

*(Otra cita CONFIRMADA)*

Detalle → **No asistió**.

**Network:** `PATCH .../estado` con `{ "estado_nuevo": "NO_ASISTIO" }` → 200.

- [ ] Estado **No asistió**  
- [ ] `ID_CITA_7` = ___________

---

### 8. CONFIRMADA → CANCELADA con motivo

*(Otra cita CONFIRMADA)*

Detalle → **Cancelar cita** → motivo → **Confirmar cancelación**.

**Network:**

```
PATCH /api/citas/{id}/estado
Body: { "estado_nuevo": "CANCELADA", "motivo_cancelacion": "..." }
Status: 200
```

- [ ] Estado **Cancelada**, motivo visible en detalle  
- [ ] `ID_CITA_8` = ___________

---

### 9. SI_ASISTIO sin OT → corregir a CONFIRMADA

*(Cita del paso 6, sin OT)*

Detalle → **Corregir estado** → **Confirmada** → motivo → confirmar.

**Network:** `PATCH .../estado` con `estado_nuevo`, `motivo_codigo` → 200.

- [ ] Vuelve a **Confirmada**  
- [ ] Anotar `estado_origen_cierre` en SQL (paso 17)

---

### 10. SI_ASISTIO sin OT → corregir a NO_ASISTIO

*(Marcar otra CONFIRMADA → SI_ASISTIO, sin OT)*

**Corregir estado** → **No asistió** → motivo → confirmar.

- [ ] Estado **No asistió**  
- [ ] `ID_CITA_10` = ___________

---

### 11. NO_ASISTIO → corregir a SI_ASISTIO

*(Cita paso 7 u otra NO_ASISTIO)*

**Corregir estado** → **Sí asistió** → motivo → confirmar.

- [ ] Estado **Sí asistió**, **Convertir a OT** visible

---

### 12. NO_ASISTIO → corregir a CONFIRMADA

*(Otra cita NO_ASISTIO)*

**Corregir estado** → **Confirmada** → motivo → confirmar.

- [ ] Estado **Confirmada**

---

### 13. Convertir cita CONFIRMADA a OT

*(CONFIRMADA futura, sin OT)*

**Convertir a OT** → redirección a OT.

**Network:** `POST /api/citas/{id}/convertir-orden` → 201.

```sql
SELECT id_cita, estado, id_orden, estado_origen_cierre
FROM citas WHERE id_cita = <ID>;
-- estado = SI_ASISTIO, id_orden NOT NULL
```

- [ ] OT creada, cita vinculada  
- [ ] `ID_CITA_13` = ___________

---

### 14. NO_ASISTIO no convierte a OT

*(Cita NO_ASISTIO sin OT)*

- [ ] **No** aparece botón **Convertir a OT** en UI

**Forzar API (opcional):**

```bash
curl -s -X POST "$APP_URL/api/citas/<ID>/convertir-orden" \
  -H "Authorization: Bearer $TOKEN"
# Esperado: 409, accion ESTADO_NO_CONVERTIBLE
```

- [ ] API rechaza con 409

---

### 15. Cita con OT muestra “Ver OT”

*(Cita paso 13)*

- [ ] Detalle muestra **Ver OT** (no **Convertir a OT**)
- [ ] Navegación a `/ordenes-trabajo/{id}` OK
- [ ] *(ADMIN)* Si hay `transiciones_permitidas`, aparece **Corregir estado** con advertencia OT

---

### 16. Registros en `cita_estado_historial`

```sql
SELECT id, id_cita, estado_anterior, estado_nuevo, motivo_codigo,
       motivo_detalle, origen, id_orden, creado_en
FROM cita_estado_historial
WHERE id_cita IN (<IDs probados>)
ORDER BY id_cita, creado_en;
```

**Esperado:**

- Creación: evento con `origen` de creación
- Cada PATCH: fila `origen = MANUAL`
- Conversión OT: fila con `id_orden` poblado

- [ ] Al menos un registro por cambio de estado ejecutado

---

### 17. `estado_origen_cierre` no cambia tras corrección

```sql
-- Tras CONFIRMADA → SI_ASISTIO (primera marcación, paso 6)
SELECT id_cita, estado, estado_origen_cierre FROM citas WHERE id_cita = <ID_CITA_6>;
-- estado_origen_cierre = 'SI_ASISTIO'

-- Tras corrección SI_ASISTIO → CONFIRMADA (paso 9)
SELECT id_cita, estado, estado_origen_cierre FROM citas WHERE id_cita = <ID_CITA_6>;
-- estado = CONFIRMADA
-- estado_origen_cierre SIGUE 'SI_ASISTIO'
```

- [ ] Columna **inmutable** después del primer cierre desde CONFIRMADA

---

### 18. Edición normal de cita sigue funcionando

Editar cita CONFIRMADA futura → cambiar motivo/notas → **Guardar**.

**Network:**

```
PUT /api/citas/{id}
Body: { id_vehiculo, fecha_hora, tipo, motivo, notas }
SIN "estado"
Status: 200
```

- [ ] Datos actualizados, estado sin cambiar

---

### 19. No error 400 por PUT con `estado` desde UI

Durante toda la sesión: ningún cambio de estado vía PUT.

**Verificación activa (opcional):**

```bash
curl -s -X PUT "$APP_URL/api/citas/<ID>/estado" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"estado":"SI_ASISTIO"}'
# Esperado: 400 — "Use PATCH /api/citas/{id}/estado..."
```

- [ ] UI solo usa PATCH para estados
- [ ] Backend rechaza PUT con `estado`

---

## FASE C — Rollback (ítem 20)

### Matriz de decisión

| Síntoma | Acción inmediata | Rollback |
|---------|------------------|----------|
| Deploy no arranca; migración falla | Revisar logs Alembic | Corregir y redeploy |
| UI rota, API OK | Redeploy frontend anterior | Revert `56d3ea1` |
| PATCH falla 500 (schema) | No usar UI de estados | Hotfix o rollback completo |
| Solo datos QA corruptos | Borrar citas de prueba | Sin rollback schema |

### Rollback completo (schema + código)

**Solo en ventana de mantenimiento** — pierde `cita_estado_historial` y columna `estado_origen_cierre`:

```bash
alembic downgrade a7b8c9d0e1f2
# Redeploy commit anterior a d903ebe (ej. caf4f7f)
```

**SQL manual (si Alembic no corre):**

```sql
DROP TABLE IF EXISTS cita_estado_historial;
ALTER TABLE citas DROP COLUMN estado_origen_cierre;
DELETE FROM alembic_version WHERE version_num = 'b8c9d0e1f2a3';
INSERT INTO alembic_version (version_num) VALUES ('a7b8c9d0e1f2');
```

### Rollback parcial

```bash
git revert 56d3ea1 --no-edit
git push origin main
# Redeploy — backend Fase 1 queda; UI incompatible (PUT estado rechazado)
```

Si hubo uso real de PATCH en prod, **preferir hotfix forward** sobre downgrade.

- [ ] Plan de rollback entendido y backup disponible (ítem 20)

---

## Cierre de Liberación

Completar **solo si** los ítems 1–19 están verdes. Responsable: quien autorizó el deploy.

### Resumen ejecutivo

| # | Ítem | OK | Observaciones |
|---|------|----|---------------|
| 1 | Commit `56d3ea1` en Railway | ☐ | |
| 2 | `alembic head` = `b8c9d0e1f2a3` | ☐ | |
| 3 | Tabla `cita_estado_historial` | ☐ | |
| 4 | Columna `estado_origen_cierre` | ☐ | |
| 5 | Crear cita | ☐ | |
| 6 | CONFIRMADA → SI_ASISTIO | ☐ | |
| 7 | CONFIRMADA → NO_ASISTIO | ☐ | |
| 8 | CONFIRMADA → CANCELADA | ☐ | |
| 9 | SI → CONFIRMADA (corrección) | ☐ | |
| 10 | SI → NO (corrección) | ☐ | |
| 11 | NO → SI (corrección) | ☐ | |
| 12 | NO → CONFIRMADA (corrección) | ☐ | |
| 13 | CONFIRMADA → OT | ☐ | |
| 14 | NO_ASISTIO bloqueada OT | ☐ | |
| 15 | Ver OT | ☐ | |
| 16 | Historial poblado | ☐ | |
| 17 | `estado_origen_cierre` inmutable | ☐ | |
| 18 | PUT editar sin estado | ☐ | |
| 19 | Sin PUT con estado | ☐ | |
| 20 | Rollback documentado + backup | ☐ | |

### Decisión

- [ ] **LIBERADO** — Fase 1 + Fase 2 en producción; operación normal
- [ ] **LIBERADO CON OBSERVACIONES** — detalle: _______________________________
- [ ] **NO LIBERADO** — rollback ejecutado o pendiente; detalle: _______________________________

### Registro

| Campo | Valor |
|-------|-------|
| Fecha / hora cierre QA | |
| Entorno | Producción Railway |
| Commit desplegado | |
| Revisión Alembic | |
| Ejecutó QA | |
| Autorizó liberación | |
| Incidencias | |
| Acciones post-liberación | Actualizar [LOGICA_CITAS.md](./LOGICA_CITAS.md) si flujo UI difiere del doc actual |

### Pendientes fuera de alcance (no bloquean liberación Fase 1+2)

- Fase 3: reportes operativo vs calidad
- Fase 4: bloqueo financiero real (`bloqueo_financiero`)
- Desvinculación OT (acción ADMIN separada)

---

**Próxima revisión del documento:** tras primera ejecución en producción o cambios en Fase 3/4.
