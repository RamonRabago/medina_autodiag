# Metodología de Desarrollo — Medina AutoDiag V2

**Versión:** 1.2.1  
**Fecha:** Junio 2026  
**Estado:** Guía oficial — obligatoria para todo desarrollo futuro  
**Alcance:** Backend (FastAPI), Frontend (React/Vite), documentación, diseño operativo

---

## Propósito de este documento

Este documento **no es documentación descriptiva**. Es la **política oficial** de arquitectura, diseño y desarrollo de Medina AutoDiag.

Toda persona o agente que implemente funcionalidades en este repositorio **debe leer y aplicar** esta metodología **antes de escribir código**.

Si una propuesta contradice estos principios, debe cuestionarse, documentarse la excepción y obtener aprobación explícita.

---

## Documentos relacionados (ecosistema V2)

| Documento | Rol |
|-----------|-----|
| [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md) | Visión arquitectónica: Centro Operativo, capas, componentes, roadmap técnico |
| [MAPA_FLUJO_OPERATIVO.md](./MAPA_FLUJO_OPERATIVO.md) | Mapa de flujos del taller, duplicaciones detectadas, customer journey |
| [PLAN_DESIGN_SYSTEM.md](./PLAN_DESIGN_SYSTEM.md) | Design system visual y de componentes UI |
| [PLAN_UX_MEJORAS.md](./PLAN_UX_MEJORAS.md) | Historial de mejoras UX completadas y pendientes |
| [ANALISIS_MODULO_ORDENES_TRABAJO.md](./ANALISIS_MODULO_ORDENES_TRABAJO.md) | Referencia técnica del módulo núcleo |
| [PLAN_COTIZACIONES_REFACCIONES_ESPECIALES.md](./PLAN_COTIZACIONES_REFACCIONES_ESPECIALES.md) | Flujo B — refacciones especiales |

---

## Contexto del producto

Medina AutoDiag ha evolucionado de un sistema de órdenes de trabajo hacia un **ERP completo para talleres mecánicos** con:

- Clientes, Vehículos, Órdenes de trabajo, Citas
- Inventario, Compras, Proveedores
- Ventas, Caja, Cuentas por pagar
- Comisiones, Nómina
- Dashboard, Auditoría, Configuración
- Cotizaciones de refacciones especiales

### Cambio de paradigma V2

| Antes (V1) | Ahora (V2) |
|------------|------------|
| Organización por **módulos** | Organización por **procesos operativos** |
| Objetivo: agregar funcionalidades | Objetivo: **reducir fricción operativa** |
| Usuario navega el ERP | Usuario **trabaja el día del taller** |
| Captura repetida aceptable | **Captura única, reutilización obligatoria** |

**Regla de oro:** No agregar módulos sin justificación operativa clara.

---

## Visión del producto

El taller opera realmente con **dos procesos principales**. Toda decisión de producto, diseño o código debe evaluarse contra ellos.

### Flujo A — Vehículo en taller

```
Cliente → Vehículo → Recepción → Orden de trabajo → Diagnóstico
→ Cotización → Autorización → Reparación → Cobro → Entrega
```

### Flujo B — Refacción especial

```
Cliente → Cotización especial → Compra → Recepción → Cobro → Entrega
```

Si una funcionalidad no mejora alguno de estos flujos (directa o indirectamente), su prioridad es cuestionable.

---

## PRE-CHECK ARQUITECTÓNICO OBLIGATORIO

**Prioridad sobre cualquier solicitud funcional específica.** Aplica a análisis, diseño, implementación, refactorización y correcciones.

### Documentos obligatorios a revisar

Antes de proponer o escribir código:

1. Este documento (`METODOLOGIA_DESARROLLO_V2.md`)
2. [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
3. Plan del módulo/hito actual (`docs/PLAN_*.md` correspondiente)
4. Componentes reutilizables (`frontend/src/components/`, especialmente `operaciones/`)
5. Endpoints existentes relacionados (`app/routers/`)
6. Flujos operativos ya aprobados

**No asumir. No recordar de memoria. Revisar explícitamente.**

### Checklist obligatorio

#### Reutilización

| Pregunta | Si sí → |
|----------|---------|
| ¿Existe componente que resuelva esto? | Reutilizar |
| ¿Existe formulario/modal/pantalla similar? | Reutilizar |
| ¿Existe endpoint reutilizable? | Reutilizar |

#### Experiencia de usuario

| Pregunta | Si sí → |
|----------|---------|
| ¿Obliga a cambiar de pantalla? | Detener; proponer alternativa |
| ¿Obliga a recapturar información? | Detener |
| ¿Aumenta clics o rompe flujo operativo? | Detener |

#### Arquitectura

| Pregunta | Si sí → |
|----------|---------|
| ¿Encaja con roadmap V2 y prepara fases futuras? | Continuar |
| ¿Genera deuda o patrón paralelo innecesario? | Priorizar arquitectura aprobada |

#### Operación del taller

¿Ayuda a recepción, técnicos o caja? ¿Reduce tiempo operativo? ¿Mejora trazabilidad?

Decidir desde la **operación real del taller**, no desde la comodidad del código.

### Reporte obligatorio (antes de programar)

Para tareas relevantes, incluir bloque:

```text
PRE-CHECK ARQUITECTÓNICO
• Componentes reutilizados:
• Componentes descartados:
• Endpoints reutilizados:
• Riesgos detectados:
• Cumplimiento Metodología V2:
• Cumplimiento Arquitectura Operativa V2:
```

Solo después de este reporte puede iniciarse la implementación.

**Sin plan aprobado (`docs/PLAN_*.md` o alcance explícito del usuario) → no implementar.**

### Reglas de gobernanza del repositorio

Aplican a **toda** tarea relevante, incluida metodología, docs y scripts ops:

| Regla | Acción |
|-------|--------|
| **No implementar sin plan** | Requiere plan aprobado, PRE-CHECK visible y autorización explícita del usuario |
| **No tocar fases cerradas** | P1–P5.1 congelados salvo **bug demostrado** con pasos de reproducción y evidencia |
| **No mezclar temas en un commit** | Metodología, docs, features y scripts ops → **commits separados** por tema |
| **No commitear artefactos sensibles** | Prohibido: `.env`, dumps `backups/`, salidas `scripts/*result*.txt`, credenciales |
| **No usar `git add .`** | Stagear archivos **explícitamente**; revisar `git status` antes de commit |
| **Diff y autorización** | Mostrar diff/resumen al usuario y **esperar autorización** antes de commit o push |
| **P5.2+ no abiertos** | No iniciar fases futuras sin PRE-CHECK y autorización explícita |

### Regla de detección de duplicidad

Durante la implementación, si aparecen formularios, modales, endpoints, flujos o componentes duplicados → **detener**, reportar, proponer reutilización. No implementar la duplicidad.

### Memoria de proyecto (referencia activa)

| Hito | Estado |
|------|--------|
| Recepción Rápida V2 (P1) | ✅ Cerrado |
| Cita → OT V2 (P2) | ✅ Cerrado |
| Mi Taller V2 (P3.1) | ✅ Cerrado |
| Evaluador financiero / A0 v2 (P4.0) | ✅ Cerrado |
| Caja Operativa UI (P4.1) | ✅ Cerrado |
| Flujo guiado Caja (P4.2) | ✅ Cerrado |
| Dashboard por rol (P5.1) | ✅ Cerrado |
| Dashboard resumen CAJA / extensiones P5 (P5.2+) | 🔲 **No abierto** — requiere plan y autorización |

Las nuevas implementaciones **se integran** a estos flujos. **Nunca** crear flujos paralelos ni reabrir hitos cerrados sin bug demostrado.

### Prioridades (en orden)

1. Consistencia
2. Reutilización
3. Menos clics
4. Menos captura repetida
5. Menos deuda técnica
6. Mejor operación del taller

Por encima de velocidad de implementación.

---

## Los 10 principios de desarrollo

### Principio 1 — Reutilizar antes de crear

**NO crear nuevas pantallas, formularios, modales, tablas, selectores, autocompletes, dashboards, badges ni componentes si existe algo similar reutilizable.**

Antes de crear cualquier elemento UI o lógica de captura:

1. Buscar en `frontend/src/components/`
2. Buscar en páginas existentes del mismo dominio
3. Consultar [PLAN_DESIGN_SYSTEM.md](./PLAN_DESIGN_SYSTEM.md)
4. Si existe algo similar → **refactorizar y extender**, no duplicar

**Componentes estándar actuales o planificados:**

| Componente | Ubicación | Uso |
|------------|-----------|-----|
| `ClienteAutocompleteConAltaRapida` | `frontend/src/components/` | Buscar/crear cliente |
| `ModalClienteRapido` | `frontend/src/components/` | Alta rápida de cliente |
| `ModalVehiculoRapido` | `frontend/src/components/` | Alta rápida de vehículo |
| `Modal` | `frontend/src/components/Modal.jsx` | Contenedor modal estándar |
| `PageHeader` | `frontend/src/components/PageHeader.jsx` | Encabezado de página |
| `PageLoading` | `frontend/src/components/PageLoading.jsx` | Estado de carga |
| `SearchableRepuestoSelect` | `frontend/src/components/` | Autocomplete repuestos |
| `SearchableVehiculoSelect` | `frontend/src/components/` | Autocomplete catálogo vehículos |
| `VehiculoSelectorConAltaRapida` | `frontend/src/components/operaciones/` | Selector + alta rápida vehículo |
| `RecepcionRapidaForm` | `frontend/src/components/operaciones/` | OT mínima PENDIENTE |
| `EstadoOTBadge` | `frontend/src/components/operaciones/` | Estados operativos legibles |
| `DashboardCard` / `KPIWidget` | `frontend/src/components/dashboard/` | Dashboard ADMIN (P5.1) |

#### Directiva obligatoria — No abandonar el flujo operativo (Jun 2026)

**Regla permanente:** el usuario **nunca** debe navegar a otro módulo para crear datos maestros (cliente, vehículo, etc.) cuando el flujo actual puede resolverlo con alta rápida inline.

| Prohibido | Correcto |
|-----------|----------|
| Cita → ir a `/clientes` → volver | `ClienteAutocompleteConAltaRapida` + `ModalClienteRapido` |
| Venta → select estático sin alta | Mismo autocomplete en modal de venta |
| Recepción → ir a Vehículos | `VehiculoSelectorConAltaRapida` + `ModalVehiculoRapido` |

**Auditoría obligatoria antes de programar** (responder internamente):

1. ¿Existe ya un componente similar?
2. ¿Existe un flujo parecido?
3. ¿Existe un modal reutilizable?
4. ¿Existe un endpoint reutilizable?
5. ¿Estoy obligando al usuario a **cambiar de contexto**?
6. ¿Cuántos clics agrego?

Si cualquier respuesta indica reutilización posible → **reutilizar**. Sin excepción salvo aprobación documentada.

**Adopción global (estado Jun 2026):**

| Módulo | Cliente | Vehículo |
|--------|---------|----------|
| Recepción rápida | ✅ | ✅ |
| OT avanzada (`NuevaOrdenTrabajo`) | ✅ | ✅ |
| Citas | ✅ | ✅ |
| Ventas (nueva/editar) | ✅ | ✅ |
| Cotizaciones refacción | ✅ | N/A |

Los `<select>` de clientes en **filtros de listado** están permitidos (no es captura operativa).

---

### Principio 2 — Primero experiencia operativa

Antes de implementar **cualquier** cambio, responder por escrito:

| # | Pregunta |
|---|----------|
| 1 | ¿Qué **problema operativo** resuelve? |
| 2 | ¿A qué **rol** beneficia? (Recepción, Técnico, Caja, Gerencia) |
| 3 | ¿Cuántos **clics** elimina? |
| 4 | ¿Cuánto **tiempo** ahorra? (estimado en segundos/minutos) |
| 5 | ¿**Reduce captura duplicada**? |
| 6 | ¿Puede **reutilizarse** en otro módulo o flujo? |

**Si no hay beneficio operativo claro → no implementar** (o escalar a Etapa 2 para replantear).

**Meta de referencia:** recepción walk-in → OT creada en **menos de 90 segundos**.

---

### Principio 3 — Módulos administran datos; Centro Operativo administra el trabajo

La evolución V2 se concentra en la capa **OPERACIONES** (Centro Operativo):

| Superficie operativa | Rol principal | Objetivo |
|---------------------|---------------|----------|
| **Recepción Rápida** | ADMIN, CAJA, EMPLEADO | Walk-in y citas → OT en mínimo tiempo |
| **Mi Taller** | TECNICO | OT asignadas, accionables, sin navegar módulos |
| **Caja Operativa** | ADMIN, CAJA | Cobro + entrega en una sola superficie |
| **Refacciones Especiales** | ADMIN, CAJA, EMPLEADO | Bandeja del Flujo B |

Los módulos actuales (`/clientes`, `/ordenes-trabajo`, `/ventas`, `/inventario`, etc.) **siguen existiendo** para:

- Administración y mantenimiento de catálogos
- Reportes y exportaciones
- Casos excepcionales y correcciones
- Configuración y auditoría

**No eliminar módulos.** Agregar la capa operativa encima.

Detalle arquitectónico: [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)

---

### Principio 4 — No duplicar componentes

Checklist obligatorio antes de un PR con UI nueva:

- [ ] ¿Existe `ClienteAutocompleteConAltaRapida` o equivalente?
- [ ] ¿Existe `ModalVehiculoRapido` o equivalente?
- [ ] ¿Se usa `Modal.jsx` o hay modal inline duplicado?
- [ ] ¿Se usa `PageHeader` + clases `btnNuevo` / `btnExport`?
- [ ] ¿Hay otro formulario de cliente/vehículo en el repo con los mismos campos?

**Acción correcta:** extraer componente compartido → adoptar en todos los consumidores progresivamente.

Duplicaciones conocidas a erradicar (ver [MAPA_FLUJO_OPERATIVO.md](./MAPA_FLUJO_OPERATIVO.md)):

- 5 implementaciones de alta de vehículo cliente
- 4 implementaciones de captura de cliente
- Modal edición OT duplicado vs wizard creación

---

### Principio 5 — Cuatro etapas obligatorias

Ningún desarrollo salta etapas.

#### Etapa 1 — Análisis *(no programar)*

Documentar:

- Flujo actual (UI + API + estados)
- Dependencias (modelos, servicios, permisos)
- Roles afectados
- Impacto operativo (Principio 2)
- Riesgos de regresión (contabilidad, inventario, auditoría)

**Entregable:** nota de análisis en `docs/` o issue/PR description.

#### Etapa 2 — Propuesta *(esperar aprobación)*

Presentar:

- Diagnóstico
- Alternativas (mínimo 2 cuando aplique)
- Riesgos y mitigaciones
- Impacto en Flujo A y/o Flujo B
- Recomendación concreta
- Estimación de complejidad

**No implementar hasta aprobación explícita** del responsable de producto o arquitecto.

#### Etapa 3 — Implementación

- Implementar **solo** lo aprobado
- Mantener permisos (`require_roles`, filtros por rol en frontend)
- Mantener auditoría (`AuditoriaService` donde corresponda)
- Mantener integridad de datos (transacciones, validaciones backend)
- Mantener compatibilidad con APIs y pantallas existentes
- Migraciones Alembic como fuente de verdad (nunca `create_all`)
- Activar venv antes de instalar paquetes Python

#### Etapa 4 — Validación

Siempre ejecutar antes de dar por terminado:

```powershell
# Backend
cd c:\medina_autodiag_api
.\venv\Scripts\Activate.ps1
python -c "from app.main import app; print('OK')"
python scripts/ejecutar_todas_pruebas.py

# Frontend
cd frontend
npm run build
```

Validar además:

- [ ] Regresiones funcionales en flujos existentes
- [ ] Permisos por rol (ADMIN, CAJA, EMPLEADO, TECNICO)
- [ ] Experiencia de usuario (clics, captura, mensajes de error)
- [ ] Flujo completo de punta a punta (Flujo A o B según aplique)
- [ ] No romper lógica contable ni movimientos de inventario sin análisis previo

---

### Principio 6 — Design System Medina AutoDiag

Toda pantalla nueva debe verse como **parte del mismo producto**.

Consultar [PLAN_DESIGN_SYSTEM.md](./PLAN_DESIGN_SYSTEM.md) para tokens, layout y componentes.

**Layout (existentes y planificados):**

| Componente | Estado | Uso |
|------------|--------|-----|
| `Layout` | ✅ Existe | Shell, sidebar, outlet |
| `PageHeader` | ✅ Existe | Título + acciones |
| `PageLoading` | ✅ Existe | Carga de página |
| `PageContainer` | 🔲 Planificado | Contenedor max-width consistente |
| `CardContainer` | 🔲 Planificado | Tarjetas de formulario/listado |
| `SectionContainer` | 🔲 Planificado | Secciones dentro de cards |

**Convenciones visuales actuales:**

- Tailwind + colores `primary-*`, `slate-*`
- Botones primarios: `btnNuevo` (azul), exportar: `btnExport` (verde)
- Modales: `Modal.jsx` con tamaños `default`, `lg`, `xl`, `2xl`
- Feedback: `react-hot-toast` vía `showError`, `showSuccess`, `normalizeDetail`
- Touch: `min-h-[44px]`, `touch-manipulation` en acciones móviles
- Franja roja en títulos: `border-l-4 border-red-500` (PageHeader)

---

### Principio 7 — Estados operativos (capa de presentación)

Los usuarios de recepción y caja **no deben interpretar enums técnicos**. Siempre mostrar etiquetas operativas:

| Estado técnico (backend) | Etiqueta operativa (UI) |
|--------------------------|-------------------------|
| `PENDIENTE` | En recepción |
| `COTIZADA` | Cotización enviada |
| `ESPERANDO_AUTORIZACION` | Esperando autorización |
| `EN_PROCESO` | En reparación |
| `ESPERANDO_REPUESTOS` | Esperando piezas |
| `COMPLETADA` | Lista para cobro |
| `ENTREGADA` | Entregada |
| `CANCELADA` | Cancelada |

**Reglas:**

- Los estados técnicos **permanecen en backend** (no cambiar BD sin migración y análisis)
- La traducción es **capa de presentación** (`EstadoOTBadge`, mapper en `utils/`)
- Mismo patrón para Flujo B (cotización refacción especial)
- Colores e iconos consistentes en todo el producto

---

### Principio 8 — Pensar en el flujo completo

No resolver **solo una pantalla aislada**.

Antes de cada cambio, trazar el recorrido completo:

**Flujo A:** Cliente → Vehículo → Recepción → OT → Diagnóstico → Cotización → Autorización → Reparación → Cobro → Entrega

**Flujo B:** Cliente → Cotización especial → Compra → Recepción → Cobro → Entrega

Preguntas obligatorias:

- ¿Este cambio rompe un paso posterior?
- ¿Genera captura duplicada en otro módulo?
- ¿El siguiente rol en la cadena recibe la información que necesita?

Mapa detallado: [MAPA_FLUJO_OPERATIVO.md](./MAPA_FLUJO_OPERATIVO.md)

---

### Principio 9 — Minimizar captura repetida

Toda información capturada **una vez** debe reutilizarse automáticamente.

| Origen | Destino | Mecanismo V2 |
|--------|---------|--------------|
| Cita | OT | `Convertir a OT` (1 clic) |
| Cliente (autocomplete) | Venta, Refacción, Cita | `ClienteAutocompleteConAltaRapida` |
| Vehículo | OT | `VehiculoSelectorConAltaRapida` |
| OT | Venta | `POST /ventas/desde-orden/{id}` |
| OT pagada | Entrega | `FlujoEntregaModal` |
| Repuesto en OT | OC | `POST /ordenes-compra/desde-orden-trabajo/{id}` |

**Prohibido** volver a pedir nombre, teléfono, marca, modelo o motivo si ya existen en el contexto de la operación.

---

### Principio 10 — Dashboard orientado por rol

| Rol | Debe ver | No debe ver (por defecto) |
|-----|----------|---------------------------|
| **Recepción** | Citas hoy, OT nuevas, esperando autorización, listas para entrega | KPIs financieros detallados |
| **Técnico** | Mis OT, detenidas, esperando piezas | Caja, compras, nómina |
| **Caja** | Por cobrar, entregas pendientes, turno, corte | Edición técnica de OT |
| **Gerencia** | Ingresos, OT abiertas/atrasadas, utilidad, alertas | Detalle operativo de cada OT |

Evitar dashboards genéricos únicos. El landing post-login debe redirigir según rol hacia `/operaciones` o dashboard específico.

---

## Restricciones inmutables

Estas restricciones **no se violan** sin análisis de impacto y aprobación explícita:

| Restricción | Motivo |
|-------------|--------|
| No eliminar módulos existentes | Compatibilidad, reportes, administración |
| No romper funcionalidades probadas en producción | Taller en operación diaria (~20 vehículos/día) |
| No modificar lógica contable sin auditoría | Integridad fiscal y de caja |
| No modificar lógica de inventario (CPP, movimientos) sin análisis | Trazabilidad de stock |
| Alembic = fuente de verdad de esquema | No usar `create_all` |
| Permisos backend son autoritativos | Frontend oculta; backend enforce |
| axios + react-hot-toast + patrones existentes | Consistencia y mantenibilidad |

---

## Roadmap oficial V2

Prioridades **obligatorias** en este orden. No saltar prioridades superiores sin justificación.

| Prioridad | Iniciativa | Objetivo | Meta medible |
|-----------|------------|----------|--------------|
| **P1** | Recepción Rápida | Walk-in → OT mínima | < 90 segundos |
| **P2** | Conversión Cita → OT | Eliminar captura duplicada | 0 re-capturas desde cita |
| **P3** | Mi Taller | Vista operativa única para técnico | > 80% uso vs listado OT |
| **P4** | Caja Operativa | Unificar cobro + entrega | ≤ 3 clics cierre |
| **P5** | Dashboard por rol | Tableros accionables | 1 landing por rol |
| **P6** | Integración Refacciones Especiales | Inventario + Ventas + Caja | Cierre loop Flujo B |

Detalle de implementación: [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md) § Roadmap 30-60-90.

---

## Métricas de éxito

Monitorear en cada iteración V2:

| Métrica | Descripción | Meta V2 |
|---------|-------------|---------|
| Tiempo recepción → OT | Walk-in hasta OT `PENDIENTE` creada | < 90 s |
| Clics para crear OT | Desde landing operativo | ≤ 5 |
| Clics cobrar + entregar | OT `COMPLETADA` → `ENTREGADA` | ≤ 3 |
| Capturas duplicadas | Campos re-ingresados por vehículo/día | Tendencia ↓ |
| Tiempo entrenamiento | Nuevo recepcionista operativo | < 2 horas |
| Productividad por rol | OT/día, cobros/día, entregas/día | Baseline + mejora |

Registrar baseline antes de P1 y comparar tras cada prioridad completada.

---

## Checklist pre-implementación (obligatorio)

Copiar en descripción de PR o issue:

```markdown
## Checklist Metodología V2

### Etapa 1 — Análisis
- [ ] Flujo actual documentado
- [ ] APIs y dependencias identificadas
- [ ] Roles afectados listados
- [ ] Beneficio operativo respondido (Principio 2)

### Etapa 2 — Propuesta
- [ ] Alternativas consideradas
- [ ] Riesgos documentados
- [ ] Alineado con Flujo A y/o B
- [ ] Aprobación obtenida

### Diseño
- [ ] Componentes existentes revisados (Principio 1 y 4)
- [ ] Design system consultado
- [ ] Estados operativos definidos (Principio 7)
- [ ] Sin captura duplicada (Principio 9)

### Etapa 4 — Validación
- [ ] python -c "from app.main import app"
- [ ] python scripts/ejecutar_todas_pruebas.py
- [ ] npm run build
- [ ] Flujo completo probado manualmente
- [ ] Permisos por rol verificados
```

---

## Regla final

Antes de escribir código:

1. **Analizar**
2. **Proponer**
3. **Justificar**
4. **Medir impacto**
5. **Implementar**

Medina AutoDiag debe evolucionar como **plataforma operativa para talleres mecánicos**, no como una colección de módulos independientes.

---

## Control de versiones de este documento

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | Jun 2026 | Versión inicial — política oficial V2 |
| 1.1 | Jun 2026 | Directiva obligatoria: no abandonar flujo operativo; catálogo componentes actualizado; adopción global Citas/Ventas/Cotizaciones |
| 1.2 | Jun 2026 | **PRE-CHECK ARQUITECTÓNICO OBLIGATORIO** — checklist, reporte, detección de duplicidad, gobernanza repo, memoria de proyecto |
| 1.2.1 | Jun 2026 | Memoria de proyecto actualizada (P3.1–P5.1 cerrados); reglas de gobernanza repo; `.gitignore` backups/resultados |

**Próxima revisión:** tras apertura autorizada de P5.2 o cambios arquitectónicos mayores.

**Mantenedor:** equipo de producto / arquitectura Medina AutoDiag
