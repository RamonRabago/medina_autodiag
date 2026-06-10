# CHECKLIST P4.0 — Validación en staging

**Versión del documento:** 1.0  
**Fecha:** Junio 2026  
**Commit de referencia:** `41531ae` — `feat(operaciones): implementar contrato A0 v2 para acciones financieras P4.0`  
**Estado:** Pendiente de ejecución en staging  
**Relacionado:** [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md) · [PLAN_P4_CAJA_OPERATIVA.md](./PLAN_P4_CAJA_OPERATIVA.md) · [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

## 1. Objetivo

Validar **P4.0 Evaluador Financiero / Contrato A0 v2** en un entorno con **MySQL accesible** antes de permitir:

- push del commit `41531ae` a remoto,
- deploy a staging y producción,
- desbloqueo de la **planeación P4.1 UI**.

Este documento es la **fuente operativa** para declarar el veredicto:

> **P4.0 VALIDADO EN STAGING**

---

## 2. Pre-requisitos

| Requisito | Verificación |
|-----------|--------------|
| Commit P4.0 en local | `git log -1 --oneline` → `41531ae` |
| Entorno virtual activo | `.\venv\Scripts\Activate.ps1` (Windows) |
| MySQL 8.x disponible | Servicio activo o instancia staging remota |
| Esquema al día | `alembic upgrade head` |
| Variables `.env` correctas | Ver sección 2.1 |
| P4.1 UI | **No iniciar** hasta completar este checklist |

### 2.1 Variables `.env`

#### Opción A — MySQL local

```env
DB_USER=root
DB_PASSWORD=<password>
DB_HOST=localhost
DB_PORT=3306
DB_NAME=medina_autodiag

SECRET_KEY=<mínimo 32 caracteres>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
DEBUG_MODE=True
```

No definir `DATABASE_URL` si se usan variables `DB_*` en local (la app construye `mysql+pymysql://...`).

#### Opción B — MySQL staging remoto

```env
DATABASE_URL=mysql+pymysql://USER:PASS@HOST:PORT/DB_NAME
SECRET_KEY=<mínimo 32 caracteres>
DEBUG_MODE=True
```

Para proveedores con SSL obligatorio (p. ej. Aiven), la app detecta `aivencloud.com` o `ssl-mode=REQUIRED` y configura SSL en `app/database.py`.

Referencia: [.env.example](../.env.example)

### 2.2 Datos seed

**Los tests de integración no requieren seed manual.** Usan la fixture `db_session_transactional` (`tests/conftest.py`): crean datos inline y hacen **ROLLBACK** al terminar. Una BD vacía con esquema migrado es suficiente.

Escenarios de dominio cubiertos por los tests (referencia):

| Escenario | Suite / test |
|-----------|--------------|
| OT COMPLETADA sin venta activa | Unitarios + venta `CANCELADA` en integración |
| OT COMPLETADA con venta parcial | `test_p40_deduplicacion_ot_parcial_no_en_ventas_saldo` |
| OT COMPLETADA con venta pagada | `test_detecta_ot_listas_para_entrega` |
| Venta mostrador sin OT | `test_detecta_ventas_saldo_pendiente` |
| Venta CANCELADA vinculada a OT | `test_p40_venta_cancelada_ot_como_sin_venta_activa` |
| Turno de caja abierto | `_seed_turno_caja()` en varios tests |
| Usuario CAJA sin turno | `test_p40_registrar_pago_item_requiere_turno`, contrato A0 ↔ pagos |

---

## 3. Validación de infraestructura

Ejecutar en orden. **No continuar** si algún paso falla.

### 3.1 Servicio MySQL

```powershell
# Windows — servicio local
Get-Service -Name "*mysql*" | Select-Object Name, Status

# Cliente mysql (si está en PATH)
mysql -h localhost -P 3306 -u root -p -e "SELECT 1 AS ok;"
```

### 3.2 Conexión desde la aplicación

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1

python -c "from app.database import engine; from sqlalchemy import text; c=engine.connect(); print('SELECT 1 =>', c.execute(text('SELECT 1')).scalar()); c.close(); print('DB OK')"
```

**Esperado:** `SELECT 1 => 1` y `DB OK`.

### 3.3 Import de la aplicación

```powershell
python -c "from app.main import app; print('OK')"
```

**Esperado:** `OK`

### 3.4 Alembic

```powershell
alembic current
alembic upgrade head
alembic current
```

**Esperado:** revisión actual == head (sin migraciones pendientes).

### 3.5 Preflight integración

```powershell
pytest tests/test_operaciones_resumen.py::test_resumen_responde_sin_datos -v
```

**Esperado:** `PASSED` (no `SKIPPED ... Base de datos no disponible`).

---

## 4. Ejecución de suites

### 4.1 Comandos

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1

python -c "from app.main import app; print('OK')"

pytest tests/test_acciones_operativas_service.py tests/test_operaciones_resumen.py tests/test_p40_contrato_a0_pagos.py -v --tb=short

pytest tests/test_ot_acciones_service.py -v --tb=short
```

### 4.2 Solo integración (opcional)

```powershell
pytest tests/test_operaciones_resumen.py tests/test_p40_contrato_a0_pagos.py tests/test_ot_acciones_service.py -m integration -v --tb=short
```

### 4.3 Inventario de tests

| Tipo | Cantidad | Requiere MySQL |
|------|----------|----------------|
| Total suites P4.0 + ot_acciones | **55** | — |
| Unitarios | **38** | No |
| Integración (`@pytest.mark.integration`) | **17** | **Sí** |

**Integración (17):**

- `test_operaciones_resumen.py` — 10 tests
- `test_p40_contrato_a0_pagos.py` — 4 tests (incl. parametrizado CAJA/ADMIN)
- `test_ot_acciones_service.py` — 3 tests

### 4.4 Resultado esperado

```
55 passed, 0 failed, 0 skipped
```

> **Nota:** Con MySQL caído, el baseline local observado fue `38 passed, 17 skipped`. Ese resultado **no** cierra P4.0.

Skip aceptable único: `test_iniciar_tecnico_sin_asignar_compat_self_assign` si `ALLOW_TECNICO_SELF_ASSIGN=False` en `ot_acciones_service.py` (hoy está `True`).

---

## 5. Validaciones contractuales

Verificar que los tests pasados confirman estos invariantes (normativa: [ADR_P4_0_EVALUADOR_FINANCIERO.md](./ADR_P4_0_EVALUADOR_FINANCIERO.md)):

| Invariante | Señal de éxito |
|------------|----------------|
| **Contrato A0 v2** | `meta.version_contrato == "a0-v2"` en `GET /api/operaciones/resumen` |
| **Globals item_only** | `registrar_pago`, `crear_venta_desde_ot`, `entregar_vehiculo` → `permitida=false`, `alcance=item_only`, `codigo_bloqueo=REQUIERE_CONTEXTO_ENTIDAD` |
| **Dedup O1/V1** | Venta OT con saldo parcial en `ot_pendientes_cobro` (O1), **ausente** en `ventas_saldo_pendiente` (V1) |
| **Venta cancelada** | OT en O1; `crear_venta_desde_ot` permitida; `registrar_pago` → `VENTA_INEXISTENTE` |
| **Turno en O1** | Sin turno → `TURNO_CERRADO`; con turno abierto → `registrar_pago.permitida=true` + `contexto.id_venta` |
| **Coherencia A0 ↔ POST pagos** | A0 verde + `POST /api/pagos/` 201 con turno; A0 rojo + POST 400 sin turno; **nunca** A0 verde si POST falla por turno |
| **Regresión Mi Taller** | Bandejas técnicas sin regresión (`test_tecnico_solo_ve_ot_asignadas`, `test_ot_completadas_tecnico_solo_propias`) |

### Smoke manual opcional (post-pytest)

```http
GET /api/operaciones/resumen
Authorization: Bearer <token_usuario_CAJA>
```

Confirmar en JSON: `meta.version_contrato == "a0-v2"` y globals financieros `item_only`.

---

## 6. Clasificación de fallos

**No modificar código** hasta clasificar y acordar corrección.

| Tipo | Síntomas | Acción |
|------|----------|--------|
| **Infraestructura** | `SKIPPED ... Base de datos no disponible`, timeout, `Access denied`, SSL | Corregir MySQL, `.env`, firewall. Re-ejecutar sección 3. |
| **Esquema / seed** | `Table doesn't exist`, FK violation, columna faltante | `alembic upgrade head`; verificar BD correcta. |
| **Bug real P4.0** | MySQL OK, esquema al día, fallo en assertion contractual | Reproducir con `-v --tb=long` en un test; documentar causa raíz; proponer fix antes de parchear. |

### Protocolo de reporte

1. Comando ejecutado, test fallido, traceback completo.
2. Confirmar pasos 3.2–3.4 (conexión, import, alembic).
3. Clasificar: infra / esquema / bug.
4. Entregar causa raíz + propuesta de corrección + impacto en P4.1.

### Fuera de alcance P4.0

Fallos en otras suites (p. ej. `test_comisiones_nomina.py` con MySQL caído) **no bloquean** este gate si las suites de la sección 4 pasan al 100%.

---

## 7. Gate de aprobación

Marcar **todas** las condiciones antes de declarar el veredicto.

- [ ] Commit local `41531ae` presente
- [ ] Paso 3.2 — conexión BD OK
- [ ] Paso 3.3 — import app OK
- [ ] Paso 3.4 — `alembic current` == head
- [ ] Sección 4 — **55 passed, 0 failed, 0 unexpected skipped**
- [ ] 17 tests de integración **PASSED** (no skipped)
- [ ] Invariantes contractuales (sección 5) verificados
- [ ] Bitácora: fecha, entorno (local/staging), ejecutor, resultado pytest

### Veredicto

Cuando todas las casillas estén marcadas:

> **P4.0 VALIDADO EN STAGING** ✅

Actualizar el campo **Estado** al inicio de este documento y registrar fecha de cierre.

---

## 8. Siguientes pasos

Secuencia **obligatoria** (no saltar pasos):

```text
P4.0 VALIDADO EN STAGING
    → Push commit 41531ae a origin/main
    → Deploy staging
    → Re-ejecutar suites en staging desplegado
    → Smoke A0 v2 (GET /api/operaciones/resumen)
    → Actualizar scripts/smoke_a0_prod.py (commit separado; hoy espera a0-v1)
    → Deploy producción P4.0
    → Re-validar smoke + regresión
    → Desbloquear planeación P4.1 UI
```

| Paso | Condición |
|------|-----------|
| Push | Gate sección 7 ✅ |
| Deploy staging | Push completado |
| Smoke A0 | Deploy staging OK; `version_contrato=a0-v2` |
| Deploy producción | Staging validado + smoke OK |
| P4.1 UI | P4.0 en prod sin violaciones A0 ↔ mutación |

---

## Riesgos conocidos

| Riesgo | Mitigación |
|--------|------------|
| MySQL caído → 17 skipped | Verificar **0 skipped** antes de cerrar |
| Esquema desactualizado | `alembic upgrade head` obligatorio |
| `DATABASE_URL` mal configurada | Paso 3.2 antes de pytest |
| `smoke_a0_prod.py` desactualizado | Commit aparte post-validación staging |
| Confundir skip infra con bug | Clasificar (sección 6) antes de parchear |

---

## Historial del documento

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | Junio 2026 | Versión inicial — checklist operativo P4.0 staging |
