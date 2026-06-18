# ADR-P6.0 — Multi-sucursal Foundation

**Estado:** ✅ **APROBADO (documentación)** — implementación **NO iniciada**  
**Fecha:** Junio 2026  
**Decisor:** Arquitectura / Negocio  
**Relacionado:** [PLAN_P6_0_IMPLEMENTACION.md](./PLAN_P6_0_IMPLEMENTACION.md) · [CHECKLIST_P6_0_MULTI_SUCURSAL.md](./CHECKLIST_P6_0_MULTI_SUCURSAL.md) · [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md) · [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

## Contexto

Medina AutoDiag opera en **múltiples sucursales físicas** (Matamoros como principal, Cd. Mante). El sistema actual es **mono-contexto**: una sola base de datos compartida, sin identificador de sucursal en operaciones transaccionales.

Recientemente se corrigió TZ-1 con `TALLER_TIMEZONE=America/Matamoros` a nivel **global**. Esa decisión permanece vigente; **no** se introduce timezone por sucursal en P6.0.

Este ADR es la **fuente normativa** para la fundación multi-sucursal P6.0 y fases posteriores (P6.1+).

---

## Problema actual

| Síntoma | Impacto |
|---------|---------|
| OT, ventas, caja y citas sin `sucursal_id` | Imposible atribuir operaciones a Matamoros vs Mante |
| Dashboard y A0 agregan **todo** el universo de datos | Reportes futuros mezclarían sucursales sin posibilidad de separar |
| JWT solo lleva `sub` + `rol` | No hay contexto de sucursal en sesión |
| `numero_orden` secuencia global `OT-YYYYMMDD-NNNN` | Aceptable en P6.0; prefijos por sucursal quedan para fase posterior |
| Confusión potencial `bodegas` vs sucursal | `bodegas` modela almacenes físicos de inventario, no ubicaciones operativas del negocio |

Sin P6.0, cualquier reporte por sucursal, caja independiente o dashboard filtrado requeriría **reconstrucción histórica** o heurísticas frágiles.

---

## Estado actual del sistema (baseline técnico)

| Área | Estado |
|------|--------|
| **Base de datos** | MySQL; sin tabla `sucursales`; sin FK de sucursal en entidades operativas |
| **Auth** | `POST /auth/login` → JWT con `sub`, `rol` (`app/routers/auth.py`) |
| **Frontend** | `AuthContext` sin sucursal; usuario derivado del payload JWT |
| **Timezone** | `TALLER_TIMEZONE` / `TIMEZONE` global (`America/Matamoros`) |
| **Inventario** | `repuestos.stock_actual` global; `bodegas` + `usuario_bodegas` para visibilidad de almacén |
| **Centro Operativo** | `GET /api/operaciones/resumen` sin filtro geográfico |
| **Dashboard** | `dashboard_agregado.py` suma totales globales |
| **Clientes / vehículos** | Catálogo compartido; sin pertenencia a sucursal |

**Sucursales conocidas (negocio):**

| Código | Nombre |
|--------|--------|
| `MAT` | Matamoros (principal) |
| `MTE` | Cd. Mante |

---

## Justificación de multi-sucursal

1. **Trazabilidad operativa:** cada recepción, venta, turno de caja y cita debe quedar etiquetada con la sucursal donde ocurrió.
2. **Habilitar P6.1+** sin rediseño: reportes, filtros y dashboards por sucursal requieren datos ya persistidos.
3. **Mínima fricción en P6.0:** solo **escritura** (stamp server-side); sin cambiar UX ni listados existentes.
4. **Alineación V2:** prepara Flujo A y Flujo B sin tocar fases cerradas P1–P5.1 más allá de columnas nuevas y puntos de creación.

---

## Decisión

Aprobar P6.0 como **fundación de datos multi-sucursal** con:

1. Nueva tabla **`sucursales`**.
2. Columna **`sucursal_id`** en entidades operativas aprobadas (ver § Aprobado).
3. **Stamp automático server-side** al crear registros (no enviado por el cliente).
4. **Backfill** de datos históricos → Matamoros (`MAT`).
5. **Sin filtros de lectura** en P6.0; listados y bandejas siguen mostrando el universo completo hasta P6.1.

---

## Aprobado en P6.0

### Tabla `sucursales` (MVP)

```text
sucursales
---------
id              INT PK
codigo          VARCHAR(10) UNIQUE NOT NULL   -- MAT, MTE
nombre          VARCHAR(100) NOT NULL
activa          BOOLEAN NOT NULL DEFAULT TRUE
created_at      TIMESTAMP NOT NULL
```

**Seed inicial:** `MAT` (Matamoros), `MTE` (Cd. Mante).

### Columnas `sucursal_id` (FK → sucursales.id)

| Tabla | Obligatoriedad post-migración | Origen al crear |
|-------|------------------------------|-----------------|
| **`usuarios`** | NOT NULL (sucursal home) | Asignación admin / default MAT |
| **`ordenes_trabajo`** | NOT NULL | `usuario.sucursal_id` del creador |
| **`ventas`** | NOT NULL | Usuario activo; si desde OT → `orden.sucursal_id` |
| **`pagos`** | NOT NULL | `venta.sucursal_id` y/o `caja_turno.sucursal_id` al registrar pago |
| **`caja_turnos`** | NOT NULL | `usuario.sucursal_id` al abrir turno |
| **`citas`** | NOT NULL | `usuario.sucursal_id` al crear cita |

### Decisiones de dominio aprobadas

| # | Decisión |
|---|----------|
| 1 | **Clientes** permanecen **globales** (compartidos entre sucursales). |
| 2 | **Vehículos** permanecen **globales** (pertenecen al cliente). |
| 3 | **Inventario** no forma parte de P6.0. |
| 4 | **Timezone por sucursal** no forma parte de P6.0 (`TALLER_TIMEZONE` global). |
| 5 | P6.0 **solo etiqueta datos** en escritura; no cambia semántica de negocio. |
| 6 | P6.0 **no filtrará listados** ni bandejas operativas. |
| 7 | **P6.1** evaluará filtros, dashboards y reportes por sucursal. |
| 8 | Tabla futura **`usuario_sucursales`** (M:N) documentada para multi-sucursal por usuario; **no** en P6.0. |

### Sucursal ≠ Bodega

| Concepto | Tabla / modelo | Propósito |
|----------|----------------|-----------|
| **Sucursal** | `sucursales` (nueva) | Ubicación operativa del negocio (Matamoros, Mante) |
| **Bodega** | `bodegas` (existente) | Almacén físico dentro del inventario (Principal, Taller, Mostrador) |

**Norma:** las bodegas existentes **NO** deben reutilizarse ni renombrarse como sucursal. En fases futuras de inventario por sucursal, se podrá relacionar `bodegas.sucursal_id` → `sucursales.id` (fuera de P6.0).

---

## Fuera de alcance P6.0

| Ítem | Fase sugerida |
|------|---------------|
| Inventario por sucursal | P6.x inventario |
| Timezone por sucursal | Post-P6.1 / configuración avanzada |
| Dashboard por sucursal | P6.1 |
| Reportes por sucursal | P6.1 |
| Filtros en listados / Mi Taller / Caja / A0 | P6.1 |
| Multi-tenant (BD o app separada por sucursal) | No planificado |
| Selector de sucursal en UI | P6.2 (con `usuario_sucursales`) |
| `cotizaciones_refaccion_especial.sucursal_id` | P6.0 opcional extendido o P6.1 — no bloqueante para fundación núcleo |
| Prefijo `OT-MAT-` en numeración | Fase posterior |
| Dirección / teléfono en `sucursales` | MVP excluido; PDF hoy usa constante Matamoros |

---

## Alcance P6.0 (resumen)

**Incluye:**

- Modelo y migraciones Alembic (tabla + columnas + backfill + NOT NULL).
- Helper de contexto de sucursal en backend (resolución desde usuario).
- Stamp en puntos de creación: OT, venta, pago, turno caja, cita.
- `usuarios.sucursal_id` + asignación manual usuarios Mante.
- JWT / login con claim o endpoint que exponga sucursal al frontend.
- Smoke de validación: OT nueva con hora y sucursal correctas en BD/API.

**No incluye:**

- Cambios de comportamiento en listados existentes.
- Reportes ni agregaciones filtradas.
- Modificación de inventario, stock ni `movimientos_inventario`.

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Escritura sin `sucursal_id` en algún `POST` | Alta | Helper central + checklist + tests integración |
| Confusión Bodega / Sucursal | Alta | ADR explícito; nombres y docs |
| Usuarios de Mante con `sucursal_id` incorrecto | Media | Paso P6.0.3 manual en configuración |
| Datos históricos atribuidos a MAT por convención | Media | Documentar; Mante solo post-go-live |
| Lecturas mezcladas entre sucursales | Media (esperado) | Comunicar; P6.1 introduce filtros |
| Regresión P1–P5.1 | Alta si se filtra mal | P6.0 sin filtros de lectura |
| `pagos.sucursal_id` divergente de venta/turno | Media | Stamp atómico en mismo transaction que pago |
| JWT sin sucursal | Baja | Resolver siempre desde BD en backend si falta claim |

---

## Fases futuras

| Fase | Contenido |
|------|-----------|
| **P6.0** | Fundación: tabla, columnas, stamp, JWT, backfill MAT |
| **P6.1** | Filtros lectura, dashboard/reportes por sucursal, A0 scoped |
| **P6.2** | `usuario_sucursales` M:N, selector sucursal en sesión |
| **P6.x inventario** | Stock / bodegas por sucursal |
| **P6.x TZ** | `sucursales.timezone` opcional reemplazando global |
| **P6.x PDF** | Dirección por sucursal en cotización |

### Tabla futura `usuario_sucursales` (no P6.0)

```text
usuario_sucursales
------------------
id_usuario      FK → usuarios.id_usuario
id_sucursal     FK → sucursales.id
PRIMARY KEY (id_usuario, id_sucursal)
```

Permite que un usuario opere varias sucursales. En P6.0 basta `usuarios.sucursal_id` como sucursal home.

---

## Compatibilidad

| Consumidor | Impacto P6.0 |
|------------|--------------|
| Recepción / Mi Taller / Caja P3–P5.1 | Sin cambio de listados; responses pueden incluir `sucursal_id` opcional |
| Dashboard ADMIN | Sin cambio de agregados |
| A0 v2 | Sin filtro; meta futura `sucursal_context` en P6.1 |
| TZ-1 | Sin cambio; `TALLER_TIMEZONE` global |
| Inventario / bodegas | Sin cambio |

---

## Referencias

- Investigación arquitectónica P6.0 (junio 2026) — aprobada conceptualmente.
- Commit TZ Matamoros: `0d15575` — `TALLER_TIMEZONE=America/Matamoros` en Railway.

---

**Estado final:** DOCUMENTADO / NO IMPLEMENTADO
