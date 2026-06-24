# PLAN QA Guardrails — Smokes con mutaciones en producción

**Versión:** 1.0  
**Fecha:** 22 de junio de 2026  
**Estado:** 📋 **PLAN APROBADO** — implementación pendiente de autorización explícita  
**Prioridad:** **P0** — gate antes de smokes mutantes post-deploy  
**Origen:** Incidencia OT 47 — [postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md](./postmortems/POSTMORTEM_OT47_SMOKE_PRODUCCION.md)

**Relacionado:**

- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)
- [DEPLOY_RAILWAY.md](./DEPLOY_RAILWAY.md)
- [CIERRE_UX_1B_MI_TALLER_SLICES.md](./CIERRE_UX_1B_MI_TALLER_SLICES.md)

---

## 1. Resumen ejecutivo

Este plan establece **guardrails obligatorios** para cualquier smoke, script o validación manual en **producción** que ejecute **mutaciones** (POST/PUT/PATCH/DELETE) sobre órdenes de trabajo, citas, ventas, pagos, clientes o inventario.

**Objetivo:** evitar repetir la incidencia OT 47 (finalización accidental de OT real durante smoke UX-1B.3).

**Alcance:** proceso + parametrización de scripts + asserts pre-mutación. **No** modifica lógica de negocio ni endpoints.

---

## 2. Convención obligatoria — fixtures QA en producción

### 2.1 Naming de clientes QA

| Campo | Convención | Ejemplo |
|-------|------------|---------|
| **Nombre cliente** | Prefijo `Qa-Op` + identificador único | `Qa-Op100 Cliente Walkin 06161715` |
| **Apellido** | Opcional, descriptivo del escenario | `Smoke UX-1B` |
| **Vehículo** | Marca/modelo identificable como QA | `Toyota Corolla Qa` |
| **OT número** | Generada por sistema; registrar id en script | `OT-20260622-0001` (id 56) |

**Regla:** si `cliente.nombre` **no** empieza con `Qa-Op` (case-sensitive en scripts; tolerancia `Qa-op` documentada como inválida), la entidad **no es fixture QA**.

### 2.2 Fixture QA dedicado por smoke

Cada smoke con mutaciones debe:

1. **Crear** su propia OT/cita/cliente QA al inicio **o**
2. Usar **lista blanca** de ids pre-registrados en el script (variable `OT_QA_IDS`, `CITA_QA_IDS`).

**Prohibido:** reutilizar la primera OT visible en bandeja del técnico sin validar cliente.

### 2.3 Registro de fixtures activos

Mantener en el encabezado del script (comentario) o en sección de este plan:

| id | numero_orden | Cliente | Uso | Último smoke |
|----|--------------|---------|-----|--------------|
| 56 | OT-20260622-0001 | Qa-Op100 Cliente Walkin | UX-1B.3 | 2026-06-22 |

Actualizar tras cada smoke que cree fixtures nuevos.

---

## 3. Regla de oro — no mutar OTs reales

| Permitido | Prohibido |
|-----------|-----------|
| Mutar OT con cliente `Qa-Op*` verificado | Mutar OT de cliente real (Manuel Mata, etc.) |
| Mutar OT cuyo `id` está en lista blanca del script | Mutar OT por conveniencia (“la primera en bandeja”) |
| GET / health / resumen A0 solo lectura en cualquier OT | POST iniciar/finalizar/entregar sin assert QA |
| Mutaciones en BD local / pytest transactional | `railway run` con mutaciones sin guardrails |

**Violación = ABORT inmediato del smoke**, documentar en log, no intentar “revertir en caliente” sin plan autorizado.

---

## 4. Validación previa obligatoria (pre-mutación)

Antes de **cualquier** POST/PUT/PATCH destructivo o de cambio de estado:

### 4.1 Assert en script (pseudocódigo)

```python
def assert_ot_qa_fixture(ot: dict) -> None:
    cliente = (ot.get("cliente") or {}).get("nombre") or ""
    ot_id = ot.get("id")
    numero = ot.get("numero_orden") or ""

    if ot_id not in ALLOWED_OT_QA_IDS:
        raise SmokeAbort(
            f"ABORT: OT id={ot_id} numero={numero} no está en ALLOWED_OT_QA_IDS"
        )
    if not cliente.startswith("Qa-Op"):
        raise SmokeAbort(
            f"ABORT: OT id={ot_id} cliente='{cliente}' no cumple prefijo Qa-Op*"
        )
    if numero and numero not in ALLOWED_OT_QA_NUMEROS optional:
        # opcional si se parametriza numero
        ...
```

### 4.2 Checklist manual (si smoke manual UI)

- [ ] Confirmé **número OT** en pantalla
- [ ] Confirmé **nombre cliente** empieza con `Qa-Op`
- [ ] Confirmé que **no** es vehículo/cliente de operación real del taller
- [ ] Tengo **id OT** anotado antes de clic en Iniciar/Finalizar

---

## 5. Checklist smoke — antes / durante / después

### 5.1 Antes del smoke

- [ ] Script identificado como **solo lectura** o **con mutaciones**
- [ ] Si mutaciones: fixture QA creado o lista blanca actualizada
- [ ] Variables prod (`DATABASE_URL`) solo vía `railway run` autorizado
- [ ] Operador conoce procedimiento reversión (postmortem OT 47)
- [ ] **No** ejecutar smokes mutantes paralelos

### 5.2 Durante el smoke

- [ ] Pre-mutación: assert `Qa-Op*` + id en whitelist
- [ ] Log explícito: `MUTATING OT id=X numero=Y cliente=Z`
- [ ] Un solo flujo mutante por ejecución (iniciar → finalizar misma OT QA)
- [ ] Si assert falla → **ABORT**, no continuar con siguiente OT

### 5.3 Después del smoke

- [ ] Verificar estado final fixture QA (esperado según escenario)
- [ ] Confirmar **ninguna OT real** alterada (spot check: listar OTs recientes no-QA)
- [ ] Registrar resultado: PASS / ABORT / FAIL
- [ ] Actualizar tabla fixtures §2.3 si se crearon entidades nuevas
- [ ] No commitear salidas con credenciales (`scripts/*result*.txt`)

---

## 6. Criterios de abort automático

El script **debe terminar con exit code ≠ 0** si:

| Código | Condición |
|--------|-----------|
| `ABORT-QA-001` | Cliente OT no cumple prefijo `Qa-Op` |
| `ABORT-QA-002` | `id` OT no está en `ALLOWED_OT_QA_IDS` |
| `ABORT-QA-003` | `numero_orden` no coincide con whitelist (si configurada) |
| `ABORT-QA-004` | OT tiene `id_venta` / estado inesperado para escenario |
| `ABORT-QA-005` | Intentar mutación sin haber pasado GET previo de la misma OT |
| `ABORT-QA-006` | Más de una OT candidata sin desambiguar — riesgo OT real |

**Comportamiento:** imprimir mensaje claro, **no ejecutar** POST, salir.

---

## 7. Scripts existentes — inventario y protección requerida

### 7.1 Scripts con mutaciones en prod (ALTO RIESGO)

| Script | Mutaciones | Acción requerida |
|--------|------------|------------------|
| `scripts/smoke_p31_mi_taller_prod.py` | POST `iniciar`, POST `finalizar` | **P0:** whitelist + assert Qa-Op; crear fixture al inicio |
| `scripts/crosscheck_e2e_acciones_ot.py` | POST iniciar/finalizar (si apunta prod) | Verificar BASE URL; prod solo con guardrails |
| `scripts/_smoke_p551_setup_ot.py` (untracked) | Posible setup OT | No usar en prod sin revisión |
| `scripts/_fix_ot47_prod.py` (untracked) | PUT OT | **Ops only** — no smoke; no commitear |

### 7.2 Scripts solo lectura prod (BAJO RIESGO — mantener)

| Script | Tipo |
|--------|------|
| `scripts/smoke_a0_prod.py` | GET resumen, valida acciones[] |
| `scripts/smoke_postdeploy_prereq_acciones_prod.py` | GET health + resumen + detalle OT muestra |
| `scripts/smoke_alta_rapida_cliente_prod.py` | POST cliente QA (`Qa-Op*`) — ya parcialmente alineado |
| `scripts/smoke_prereq_acciones_ot.py` | Local/mock — sin prod |

### 7.3 Scripts ops / higiene (FUERA DE SMOKE)

| Script | Uso |
|--------|-----|
| `scripts/_hygiene_ot47_prod.py` | Corrección puntual autorizada — no reutilizar como plantilla |
| `scripts/_verify_ot47_bandejas.py` | Verificación read-only |
| `scripts/listar_usuarios.py` | Diagnóstico |

### 7.4 Implementación futura (autorización separada)

| Entregable | Descripción |
|------------|-------------|
| `scripts/lib/qa_guardrails.py` | Módulo compartido: `assert_ot_qa`, `assert_cliente_qa` |
| Parametrización env | `SMOKE_OT_QA_ID`, `SMOKE_ALLOW_MUTATIONS=true` |
| Modo `--dry-run` | Log de mutaciones que se harían sin ejecutar |

---

## 8. Fuera de alcance (este plan)

| Ítem | Notas |
|------|-------|
| Entorno staging dedicado | Recomendado futuro; no bloquea guardrails P0 |
| Badge UI “QA” en OT | Feature futuro |
| Guardrails en backend API | Evaluar post-P6; fuera de P0 |
| Modificar evaluadores A0 / P4.0 | Prohibido |
| Reabrir OT47 o incidentes cerrados | Solo referencia |
| Commitear credenciales o `.env` | Prohibido |
| Cambios en `METODOLOGIA` | Ver [PROPUESTA_ACTUALIZACION_METODOLOGIA_V2_JUN2026.md](./PROPUESTA_ACTUALIZACION_METODOLOGIA_V2_JUN2026.md) |

---

## 9. Criterios de cierre P0 Guardrails

- [ ] `scripts/lib/qa_guardrails.py` o equivalente implementado
- [ ] `smoke_p31_mi_taller_prod.py` protegido con asserts + fixture QA
- [ ] Documentación METODOLOGIA actualizada (regla smokes prod)
- [ ] Checklist §5 incorporado en `DEPLOY_RAILWAY.md` o runbook smoke
- [ ] Smoke mutante de prueba en prod **solo fixture QA** — PASS documentado
- [ ] Commit separado: `docs(qa): add production smoke guardrails plan` + `feat(scripts): qa guardrails` (dos commits si aplica)

---

## 10. Orden de implementación sugerido

1. Módulo `qa_guardrails.py` (asserts puros, sin side effects)
2. Refactor `smoke_p31_mi_taller_prod.py` (crear OT QA → mutar → validar)
3. Revisar `crosscheck_e2e_acciones_ot.py` — gate `BASE != prod` o guardrails
4. Actualizar METODOLOGIA (propuesta aprobada)
5. Smoke validación prod con fixture únicamente

**Gate:** ningún smoke mutante prod hasta completar pasos 1–2.

---

*Plan P0 — deuda de proceso post OT47. No sustituye PRE-CHECK de features.*
