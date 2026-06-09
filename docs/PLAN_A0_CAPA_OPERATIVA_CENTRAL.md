# PLAN A0 — Capa Operativa Central Medina AutoDiag V2

**Versión:** 1.1  
**Fecha:** Junio 2026  
**Estado:** ✅ Implementado — pendiente deploy manual  
**Relacionado:** [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md) · [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)

---

## 1. Objetivo del hito A0

Crear una **base backend reutilizable** (solo lectura) para que los próximos hitos **P3 Mi Taller**, **P4 Caja Operativa**, **P5 Dashboard por rol** y **P6 Refacción automática** no dupliquen lógica ni consulten datos dispersos.

**Entregables A0:**

| # | Entregable | Alcance |
|---|------------|---------|
| 1 | `OperacionesService` | Diagnóstico consolidado citas / OT / ventas / pagos / caja / inventario |
| 2 | `GET /api/operaciones/resumen` | Contrato JSON estable con bandejas + métricas + acciones por rol |
| 3 | Schemas Pydantic | Contrato tipado y documentado en OpenAPI |
| 4 | Tests pytest mínimos | 5 escenarios obligatorios (ver §8) |
| 5 | Documentación | Este plan + actualización arquitectura V2 |

**Fuera de alcance A0 (explícito):**

- Pantallas P3 / P4 / P5 / P6
- Mutaciones (POST/PATCH/PUT) en `/api/operaciones/*`
- Migraciones Alembic (sin tablas nuevas)
- Refactor del `GET /api/dashboard` existente
- Implementación real de `bloqueo_financiero` (Fase 4 Citas — solo placeholder coherente)

---

## 2. PRE-CHECK ARQUITECTÓNICO

### 2.1 Documentos revisados

- [x] `METODOLOGIA_DESARROLLO_V2.md` — principios, PRE-CHECK, prioridades
- [x] `ARQUITECTURA_OPERATIVA_V2.md` — router agregador planificado
- [x] `LOGICA_CITAS.md` / `PLAN_CITA_A_OT_V2.md` — estados y conversión
- [x] `PLAN_RECEPCION_RAPIDA_V2.md` — recepción y vínculo cita

### 2.2 Modelos existentes relevantes

| Modelo | Campos / estados clave para A0 |
|--------|--------------------------------|
| `Cita` | `estado` (CONFIRMADA, SI_ASISTIO, NO_ASISTIO, CANCELADA), `fecha_hora`, `id_orden`, `id_cliente`, `id_vehiculo` |
| `OrdenTrabajo` | `estado` (PENDIENTE…ENTREGADA), `tecnico_id`, `fecha_ingreso`, `total` |
| `Venta` | `estado` (PAGADA, PENDIENTE, CANCELADA), `id_orden`, `total` |
| `Pago` | `id_venta`, `monto` — saldo = `venta.total - sum(pagos)` |
| `CajaTurno` | `estado` ABIERTO/CERRADO — turno activo |
| `AlertaInventario` | agregados por tipo (reutilizar patrón `dashboard_agregado` / `inventario_reportes`) |
| `CotizacionRefaccionEspecial` | estados Flujo B — **solo contadores preview** en A0 (preparar P6) |

### 2.3 Routers / endpoints reutilizables (solo lectura)

| Endpoint existente | Uso en A0 |
|--------------------|-----------|
| `GET /api/citas/dashboard/proximas` | Patrón query citas CONFIRMADA futuras — **no reemplazar**; A0 agrega bandejas operativas distintas |
| `GET /api/dashboard` | KPIs financieros ADMIN/CAJA — **complementario**, no duplicar lógica financiera profunda |
| `GET /api/inventario/reportes/alertas/resumen` | Patrón conteo alertas |
| `GET /api/ordenes-trabajo/estadisticas/dashboard` | Patrón conteo por estado OT |
| Lógica en `ordenes_trabajo/crud.py` | `venta_saldo_pendiente` por OT — **extraer patrón** a helper en `OperacionesService` |
| `POST /api/ordenes-trabajo/{id}/entregar` | Regla: COMPLETADA + venta PAGADA (saldo≈0) — define bandeja `listas_para_entrega` |

### 2.4 Servicios reutilizables

| Servicio | Función / patrón a reutilizar |
|----------|-------------------------------|
| `recepcion_ot_service` | `ESTADOS_CITA_CONVERTIBLES`, reglas de `validar_cita_convertible` → extraer `evaluar_cita_convertible()` **sin HTTPException** |
| `cita_estado_service` | `calcular_estado_meta`, `ventana_correccion_activa`, roles transición |
| `inventario_service` | Consultas dashboard inventario (opcional, contadores) |
| `caja_alertas` | `generar_alerta_turno_largo` (patrón alertas) |
| `ventas_service` | Cálculo saldo (patrón `to_decimal` / `money_round`) |

### 2.5 Componentes frontend (referencia, sin cambios A0)

| Componente | Relación futura |
|------------|-----------------|
| `rolesOperaciones.js` | `ROLES_RECEPCION` — espejo backend para acciones |
| `citaOt.js` | `puedeConvertirCitaAOT` — **debe alinearse** con backend; A0 hace backend autoridad |
| `Citas.jsx` | Sigue usando endpoints citas; P3/P4 consumirán `/operaciones/resumen` |

### 2.6 Reporte PRE-CHECK

```text
PRE-CHECK ARQUITECTÓNICO — A0 Capa Operativa Central

• Componentes reutilizados:
  - Patrones de query de dashboard_agregado (turno caja, alertas inventario)
  - recepcion_ot_service (reglas convertibilidad cita → OT)
  - cita_estado_service (estado_meta por cita en ítems de bandeja)
  - Cálculo saldo venta (ventas/crud + ordenes_trabajo/crud)

• Componentes descartados:
  - Duplicar GET /api/dashboard como /operaciones/resumen
  - Nueva tabla o vista materializada (innecesario en A0)
  - Lógica de permisos solo en frontend (viola principio 1)

• Endpoints reutilizados (mutación delegada, no expuestos en A0):
  - POST /citas/{id}/convertir-orden
  - PATCH /citas/{id}/estado
  - POST /ordenes-trabajo/{id}/iniciar|finalizar|entregar
  - POST /ventas/desde-orden/{id}, POST /pagos/

• Riesgos detectados: ver §9

• Cumplimiento Metodología V2: ✅
  - Backend autoridad, entrega incremental, documentar antes de codificar, sin romper legacy

• Cumplimiento Arquitectura Operativa V2: ✅
  - Capa orquestación lectura; mutaciones en routers existentes
  - Prepara P3–P6 sin implementarlos
```

---

## 3. Diseño — OperacionesService

**Ubicación:** `app/services/operaciones_service.py`

**Responsabilidad:** Agregar y clasificar entidades operativas. **Solo lectura.** Sin `commit`, sin `HTTPException` en funciones internas (retorna estructuras; el router traduce a HTTP si aplica).

### 3.1 Módulos internos (funciones)

| Función | Descripción |
|---------|-------------|
| `calcular_saldo_venta(db, venta_id)` | `max(0, total - pagos)` — helper compartido |
| `evaluar_cita_convertible(cita)` | `{ permitida, motivo_bloqueo, codigo_bloqueo, redirect? }` — espejo de `validar_cita_convertible` sin excepción |
| `bandeja_citas_pendientes_marcacion(db, limit)` | `CONFIRMADA` + `fecha_hora <= ahora` |
| `bandeja_citas_convertibles(db, rol, limit)` | `CONFIRMADA`/`SI_ASISTIO`, sin `id_orden`, con `estado_meta` + acciones ítem |
| `bandeja_ot_pendientes(db, tecnico_id?, limit)` | PENDIENTE, COTIZADA, ESPERANDO_* |
| `bandeja_ot_en_proceso(db, tecnico_id?, limit)` | EN_PROCESO |
| `bandeja_ot_pendientes_cobro(db, limit)` | COMPLETADA sin venta activa o venta con saldo > 0 |
| `bandeja_ot_listas_entrega(db, limit)` | COMPLETADA + venta no cancelada + saldo ≈ 0 |
| `bandeja_ventas_saldo_pendiente(db, limit)` | `estado != CANCELADA` + saldo > 0 |
| `contadores_flujo_b(db)` | Cotizaciones EN_COMPRA, RECIBIDA (preview P6) |
| `alertas_operativas(db, rol)` | Turno caja, inventario crítico, OT urgentes, citas vencidas sin marcar |
| `metricas_por_rol(db, usuario)` | Contadores filtrados según rol |
| `acciones_globales_por_rol(rol)` | Matriz acciones permitidas a nivel módulo |
| `construir_resumen_operativo(db, usuario)` | Orquestador principal |

### 3.2 Definiciones de bandejas (reglas de negocio)

#### Citas pendientes de confirmar / marcación

Citas en `CONFIRMADA` cuya `fecha_hora` ya pasó (`<= ahora_local`) y el cliente aún no fue marcado (no asistió / sí asistió). Son la cola de recepción para marcar asistencia.

#### Citas convertibles a OT

- `estado IN (CONFIRMADA, SI_ASISTIO)`
- `id_orden IS NULL`
- Evaluación `evaluar_cita_convertible` (incluye vehículo faltante → `COMPLETAR_RECEPCION`)

#### OT pendientes

`estado IN (PENDIENTE, COTIZADA, ESPERANDO_AUTORIZACION, ESPERANDO_REPUESTOS)`

#### OT en proceso

`estado = EN_PROCESO`

#### OT finalizadas pendientes de cobro

`estado = COMPLETADA` Y (
  no existe venta activa (`estado != CANCELADA`) **O**
  venta existe con `saldo_pendiente > 0.001`
)

#### Vehículos listos para entrega

`estado = COMPLETADA` Y venta activa existe Y `saldo_pendiente <= 0.001`  
(Alineado con regla de `entregar_orden_trabajo` en `acciones.py`)

#### Ventas con saldo pendiente

Todas las ventas no canceladas con saldo > 0 (incluye ventas sin OT).

### 3.3 Filtro por rol

| Rol | Visibilidad bandejas |
|-----|----------------------|
| **ADMIN** | Todas las bandejas + métricas completas |
| **CAJA** | Citas, OT cobro/entrega, ventas saldo, caja, alertas |
| **EMPLEADO** | Citas marcación/convertibles, OT pendientes (sin cobro), recepción |
| **TECNICO** | OT pendientes/en proceso **asignadas** (`tecnico_id = usuario`) + métricas propias |

**Nota:** TECNICO no ve ventas/caja salvo contadores neutros (0 / vacío).

### 3.4 Refactor mínimo propuesto (aprobación)

Añadir en `recepcion_ot_service.py`:

```python
def evaluar_cita_convertible(cita: Cita) -> dict:
    """Versión lectura: misma lógica que validar_cita_convertible sin HTTPException."""
```

`validar_cita_convertible` delegará internamente a `evaluar_cita_convertible` y lanzará HTTPException si `permitida=False`. **Evita divergencia** entre Citas V2 y A0.

---

## 4. Endpoint — `GET /api/operaciones/resumen`

**Router:** `app/routers/operaciones.py`  
**Prefijo:** `/operaciones`  
**Auth:** `get_current_user` — todos los roles autenticados  
**Query params opcionales:**

| Param | Default | Descripción |
|-------|---------|-------------|
| `limit_items` | `15` | Máx ítems por bandeja (1–50) |
| `incluir_items` | `true` | Si `false`, solo contadores (ligero para P5) |

**Mutaciones:** ninguna en A0.

### 4.1 Contrato JSON final (propuesto)

```json
{
  "generado_en": "2026-06-08T14:30:00-07:00",
  "usuario": {
    "id_usuario": 1,
    "rol": "CAJA",
    "nombre": "María"
  },
  "acciones_globales": [
    {
      "accion": "convertir_cita_ot",
      "permitida": true,
      "motivo_bloqueo": null
    },
    {
      "accion": "recepcion_rapida",
      "permitida": true,
      "motivo_bloqueo": null
    },
    {
      "accion": "registrar_pago",
      "permitida": true,
      "motivo_bloqueo": null
    },
    {
      "accion": "entregar_vehiculo",
      "permitida": true,
      "motivo_bloqueo": null
    },
    {
      "accion": "iniciar_ot",
      "permitida": false,
      "motivo_bloqueo": "Rol CAJA no puede iniciar órdenes de trabajo"
    }
  ],
  "metricas": {
    "citas_pendientes_marcacion": 2,
    "citas_convertibles": 1,
    "ot_pendientes": 4,
    "ot_en_proceso": 3,
    "ot_pendientes_cobro": 2,
    "ot_listas_entrega": 1,
    "ventas_saldo_pendiente": 5,
    "refacciones_en_compra": 0,
    "refacciones_recibidas_pendiente_entrega": 0
  },
  "caja": {
    "turno_abierto": true,
    "id_turno": 12,
    "alerta_turno_largo": false
  },
  "bandejas": {
    "citas_pendientes_marcacion": {
      "total": 2,
      "items": [
        {
          "tipo_entidad": "cita",
          "id": 4,
          "fecha_hora": "2026-06-08T09:00:00",
          "estado": "CONFIRMADA",
          "cliente_nombre": "Damaris López",
          "vehiculo_resumen": "Nissan Sentra 2018",
          "estado_meta": {
            "transiciones_permitidas": ["SI_ASISTIO", "NO_ASISTIO", "CANCELADA"],
            "requiere_motivo": false,
            "estado_editable": true,
            "ventana_activa": true,
            "tiene_ot": false,
            "bloqueo_financiero": false
          },
          "acciones": [
            {
              "accion": "marcar_asistencia_cita",
              "permitida": true,
              "motivo_bloqueo": null
            },
            {
              "accion": "convertir_cita_ot",
              "permitida": true,
              "motivo_bloqueo": null
            }
          ]
        }
      ]
    },
    "citas_convertibles": {
      "total": 1,
      "items": []
    },
    "ot_pendientes": {
      "total": 4,
      "items": [
        {
          "tipo_entidad": "orden_trabajo",
          "id": 10,
          "numero_orden": "OT-20260609-0001",
          "estado": "PENDIENTE",
          "cliente_nombre": "Erick García",
          "vehiculo_resumen": "Honda Civic 2020",
          "tecnico_nombre": null,
          "fecha_ingreso": "2026-06-09T08:15:00",
          "prioridad": "NORMAL",
          "acciones": [
            {
              "accion": "iniciar_ot",
              "permitida": false,
              "motivo_bloqueo": "Rol CAJA no puede iniciar órdenes"
            }
          ]
        }
      ]
    },
    "ot_en_proceso": { "total": 3, "items": [] },
    "ot_pendientes_cobro": {
      "total": 2,
      "items": [
        {
          "tipo_entidad": "orden_trabajo",
          "id": 7,
          "numero_orden": "OT-20260601-0003",
          "estado": "COMPLETADA",
          "total_orden": 4500.0,
          "id_venta": 22,
          "saldo_pendiente": 1500.0,
          "acciones": [
            {
              "accion": "crear_venta_desde_ot",
              "permitida": false,
              "motivo_bloqueo": "Ya existe venta vinculada"
            },
            {
              "accion": "registrar_pago",
              "permitida": true,
              "motivo_bloqueo": null
            }
          ]
        }
      ]
    },
    "ot_listas_entrega": { "total": 1, "items": [] },
    "ventas_saldo_pendiente": {
      "total": 5,
      "items": [
        {
          "tipo_entidad": "venta",
          "id": 22,
          "id_orden": 7,
          "cliente_nombre": "Cliente X",
          "total": 4500.0,
          "saldo_pendiente": 1500.0,
          "estado": "PENDIENTE",
          "acciones": [
            {
              "accion": "registrar_pago",
              "permitida": true,
              "motivo_bloqueo": null
            }
          ]
        }
      ]
    }
  },
  "alertas_operativas": [
    {
      "codigo": "CITA_VENCIDA_SIN_MARCAR",
      "severidad": "media",
      "mensaje": "2 citas confirmadas ya pasaron su hora sin marcación",
      "cantidad": 2
    },
    {
      "codigo": "INVENTARIO_CRITICO",
      "severidad": "alta",
      "mensaje": "3 alertas de inventario críticas",
      "cantidad": 3
    }
  ],
  "meta": {
    "limit_items": 15,
    "incluir_items": true,
    "version_contrato": "a0-v1"
  }
}
```

### 4.2 Catálogo de acciones (`accion`)

| Código | Roles típicos | Endpoint delegado (futuro) |
|--------|---------------|----------------------------|
| `recepcion_rapida` | ADMIN, CAJA, EMPLEADO | `POST /ordenes-trabajo/recepcion-rapida` |
| `convertir_cita_ot` | ADMIN, CAJA, EMPLEADO | `POST /citas/{id}/convertir-orden` |
| `marcar_asistencia_cita` | ADMIN, CAJA, EMPLEADO, TECNICO* | `PATCH /citas/{id}/estado` |
| `iniciar_ot` | ADMIN, TECNICO† | `POST /ordenes-trabajo/{id}/iniciar` |
| `finalizar_ot` | ADMIN, TECNICO† | `POST /ordenes-trabajo/{id}/finalizar` |
| `crear_venta_desde_ot` | ADMIN, CAJA | `POST /ventas/desde-orden/{id}` |
| `registrar_pago` | ADMIN, CAJA | `POST /pagos/` |
| `entregar_vehiculo` | ADMIN, CAJA | `POST /ordenes-trabajo/{id}/entregar` |

\* TECNICO solo marcación inicial (sin corrección con motivo) — reglas de `cita_estado_service`.  
† TECNICO solo OT asignadas.

### 4.3 Respuesta vacía / sin datos

Siempre `200 OK` con estructura completa; contadores en `0`, `items: []`, `acciones_globales` coherentes con rol. **Nunca** error por BD vacía.

---

## 5. Preparación futura P3–P6

| Hito | Consumo de A0 |
|------|----------------|
| **P3 Mi Taller** | `bandejas.ot_pendientes` + `ot_en_proceso` filtradas por `tecnico_id`; acciones `iniciar_ot` / `finalizar_ot` |
| **P4 Caja Operativa** | `ot_pendientes_cobro`, `ventas_saldo_pendiente`, `ot_listas_entrega`; cuando exista Fase 4, `bloqueo_financiero` en ítems cita |
| **P5 Dashboard por rol** | `metricas` + `alertas_operativas`; `incluir_items=false` para carga rápida |
| **P6 Refacción automática** | Extender `metricas.refacciones_*` y bandeja `refacciones_pendientes` sin romper contrato (`version_contrato` bump) |

**Extensibilidad:** campo `meta.version_contrato` permite evolucionar bandejas sin romper clientes.

---

## 6. Archivos a tocar (implementación post-aprobación)

| Archivo | Acción |
|---------|--------|
| `app/services/operaciones_service.py` | **Crear** — lógica agregación |
| `app/services/recepcion_ot_service.py` | **Actualizar** — `evaluar_cita_convertible` + refactor `validar_cita_convertible` |
| `app/schemas/operaciones_schema.py` | **Crear** — modelos Pydantic respuesta |
| `app/routers/operaciones.py` | **Crear** — `GET /resumen` |
| `app/main.py` | **Actualizar** — registrar router bajo `/api` |
| `tests/test_operaciones_resumen.py` | **Crear** — 5+ tests |
| `docs/ARQUITECTURA_OPERATIVA_V2.md` | **Actualizar** — hito A0 |
| `docs/PLAN_A0_CAPA_OPERATIVA_CENTRAL.md` | **Actualizar** — marcar implementado tras QA |

**Sin tocar en A0:** frontend, Alembic, Citas.jsx, RecepcionRapida.jsx.

---

## 7. Plan de implementación (fases tras aprobación)

| Fase | Duración est. | Contenido |
|------|---------------|-----------|
| **A0.1** | 2–3 h | `evaluar_cita_convertible` + `OperacionesService` core (OT, ventas) |
| **A0.2** | 1–2 h | Bandejas citas + acciones por rol + alertas |
| **A0.3** | 1 h | Router + schemas + registro main |
| **A0.4** | 2 h | Tests pytest + validación `ejecutar_todas_pruebas` + import app |
| **A0.5** | 30 min | QA manual endpoint con curl/Postman; documentar cierre |

---

## 8. Pruebas obligatorias

| # | Test | Criterio |
|---|------|----------|
| 1 | OT pendientes | Crea OT PENDIENTE → contador y bandeja incluyen la OT |
| 2 | Ventas saldo pendiente | Venta PENDIENTE con pago parcial → `saldo_pendiente > 0` en bandeja |
| 3 | OT completada pendiente cobro | OT COMPLETADA + venta con saldo → aparece en `ot_pendientes_cobro` |
| 4 | Roles | TECNICO solo ve OT asignadas; CAJA no tiene `iniciar_ot` permitida |
| 5 | Sin datos | BD sin entidades operativas relevantes → 200, contadores 0, sin excepción |

Marcador: `@pytest.mark.integration` (mismo patrón que `test_cita_convertir_orden.py`).

---

## 9. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|--------|-------|---------|------------|
| Duplicar lógica con `/api/dashboard` | Media | Deuda, inconsistencia KPI | Separación clara: dashboard=finanzas; operaciones=bandejas+acciones |
| Divergencia convertibilidad cita vs Citas V2 | Media | Bugs UX | `evaluar_cita_convertible` compartido con `validar_cita_convertible` |
| Performance N+1 en bandejas | Media | Lentitud resumen | Queries con `joinedload`; límites por bandeja; índices existentes en `estado`, `fecha_hora` |
| Frontend sigue con reglas locales (`citaOt.js`) | Alta | Doble fuente verdad | A0 solo backend; migrar frontend en P3/P4 a consumir `acciones` |
| Confusión `citas_pendientes_marcacion` vs `proximas` | Baja | UX | Documentar en contrato; nombres distintos a `/citas/dashboard/proximas` |
| Scope creep hacia P4 (cobro en operaciones) | Media | Retraso A0 | Bloquear mutaciones; solo diagnóstico |
| `bloqueo_financiero` anticipado sin Fase 4 | Baja | Expectativas | Siempre `false` en A0; comentario en schema |

---

## 10. Validación post-implementación

```powershell
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1
python -c "from app.main import app; print('OK')"
python -m pytest tests/test_operaciones_resumen.py -v
python scripts/ejecutar_todas_pruebas.py
cd frontend; npm run build
```

- Alembic: **sin nueva migración** (verificar `alembic heads` sin cambios)
- Smoke: `GET /api/operaciones/resumen` con token ADMIN, CAJA, TECNICO
- Regresión: tests citas existentes pasan sin modificación

---

## 11. Criterios de aprobación del PRE-CHECK

Para pasar de 📋 a ✅ implementación, confirmar:

- [ ] Contrato JSON §4.1 aceptado (o comentarios incorporados)
- [ ] Definiciones de bandejas §3.2 aceptadas
- [ ] Refactor `evaluar_cita_convertible` aprobado
- [ ] Alcance “solo lectura / sin frontend” confirmado
- [ ] Prioridad sobre `/api/dashboard` entendida

**Aprobado por:** _______________ **Fecha:** _______________

---

## 12. Referencias

- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- [PLAN_CITA_A_OT_V2.md](./PLAN_CITA_A_OT_V2.md)
- [PLAN_RECEPCION_RAPIDA_V2.md](./PLAN_RECEPCION_RAPIDA_V2.md)
- `app/routers/dashboard_agregado.py` — patrón agregador existente
- `app/routers/ordenes_trabajo/acciones.py` — reglas entrega
