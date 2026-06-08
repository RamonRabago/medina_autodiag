# Plan Design System — Medina AutoDiag

**Versión:** 1.0 (propuesta)  
**Fecha:** Junio 2026  
**Estado:** Guía de diseño — en evolución  
**Relacionado:** [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md) · [PLAN_UX_MEJORAS.md](./PLAN_UX_MEJORAS.md)

---

## 1. Propósito

Definir reglas visuales y de componentes para que **todas las pantallas — legacy y Centro Operativo V2 —** se perciban como un solo producto.

Este documento complementa la metodología V2 (Principio 6). Antes de crear UI nueva, consultar aquí.

---

## 2. Stack visual

| Tecnología | Uso |
|------------|-----|
| Tailwind CSS | Utilidades, responsive |
| Colores `primary-*` | Acciones principales, focus rings |
| Colores `slate-*` | Texto, bordes, fondos neutros |
| `react-hot-toast` | Notificaciones |
| Vite code-splitting | `vendor-react`, `vendor-ui`, etc. |

---

## 3. Tokens de color (operativos)

| Token | Clase Tailwind | Uso |
|-------|----------------|-----|
| Primario | `primary-600`, `primary-700` | Botones acción, links activos |
| Éxito | `emerald-600` | Exportar, confirmaciones |
| Advertencia | `amber-50`, `amber-800` | Alertas, esperando |
| Error | `red-50`, `red-600` | Validación, cancelación |
| Neutro | `slate-*` | Texto, bordes, fondos |
| Acento marca | `border-red-500` | Franja título PageHeader |

### Estados operativos OT (propuesta badges)

| Estado operativo | Fondo | Texto |
|------------------|-------|-------|
| En recepción | `bg-slate-100` | `text-slate-700` |
| Cotización enviada | `bg-blue-50` | `text-blue-800` |
| Esperando autorización | `bg-amber-50` | `text-amber-800` |
| En reparación | `bg-primary-50` | `text-primary-800` |
| Esperando piezas | `bg-orange-50` | `text-orange-800` |
| Lista para cobro | `bg-green-50` | `text-green-800` |
| Entregada | `bg-emerald-50` | `text-emerald-800` |
| Cancelada | `bg-red-50` | `text-red-700` |

Componente objetivo: `EstadoOTBadge.jsx`.

---

## 4. Layout

### 4.1 Componentes existentes

| Componente | Archivo | Uso |
|------------|---------|-----|
| `Layout` | `components/Layout.jsx` | Sidebar, outlet, drawer móvil |
| `PageHeader` | `components/PageHeader.jsx` | Título + franja roja + acciones |
| `PageLoading` | `components/PageLoading.jsx` | Carga full-page |
| `Modal` | `components/Modal.jsx` | Diálogos estándar |

### 4.2 Componentes planificados (V2)

| Componente | Responsabilidad |
|------------|-----------------|
| `PageContainer` | `max-w-* mx-auto px-4` consistente |
| `CardContainer` | `bg-white rounded-xl shadow-sm border border-slate-200 p-6` |
| `SectionContainer` | Agrupación con título de sección dentro de card |
| `BandejaOperativa` | Lista filtrable con acciones rápidas (Centro Operativo) |

### 4.3 Patrón de página estándar

```
Layout
└── PageContainer
    ├── PageHeader (título + CTA)
    ├── [opcional] KPIWidget row
    └── CardContainer(s)
        └── contenido (tabla, formulario, bandeja)
```

---

## 5. Componentes de formulario

### 5.1 Inputs

```html
className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
```

- Labels: `block text-sm font-medium text-slate-700 mb-1`
- Campos obligatorios: asterisco en label o `(opcional)` explícito
- Touch targets: `min-h-[44px]` en móvil

### 5.2 Botones

Exportados desde `PageHeader.jsx`:

| Variante | Constante | Uso |
|----------|-----------|-----|
| Primario | `btnNuevo` | Crear, guardar, confirmar |
| Exportar | `btnExport` | Excel, PDF |
| Secundario | `border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50` | Cancelar |
| Peligro | `bg-red-600 text-white` | Eliminar, cancelar orden |

Estados: `disabled:opacity-50 disabled:cursor-not-allowed`

### 5.3 Selectores especializados (reutilizar)

| Componente | Cuándo usar |
|------------|-------------|
| `ClienteAutocompleteConAltaRapida` | Cualquier captura de cliente |
| `ModalVehiculoRapido` | Alta vehículo de cliente |
| `SearchableRepuestoSelect` | Líneas de OC |
| `SearchableVehiculoSelect` | Catálogo compatibilidad repuestos |

**No crear** `<select>` de cliente con lista estática si hay búsqueda dinámica.

---

## 6. Modales

Usar siempre `Modal.jsx`:

| Prop | Valores | Uso |
|------|---------|-----|
| `size` | `default`, `lg`, `xl`, `2xl` | Formularios complejos → `lg`+ |
| `titulo` | string | Descriptivo con contexto (ej. "Agregar vehículo — Juan Pérez") |
| Cierre | Escape + click fuera | Ya implementado |

**Evitar:** modals inline con `<div className="fixed inset-0">` (existe en CotizacionesRefaccion — migrar).

---

## 7. Tablas y listados

| Elemento | Patrón |
|----------|--------|
| Carga | `TableSkeleton` o `PageLoading` |
| Paginación | Controles al pie; `limit` 20 default |
| Acciones fila | Iconos + texto en desktop; menú compacto móvil |
| Empty state | Mensaje + CTA (ej. "No hay clientes. Crear uno") |
| Búsqueda | Input con debounce 280ms en autocompletes |

---

## 8. Dashboard

### 8.1 Componentes planificados

**`KPIWidget`**
- Props: `titulo`, `valor`, `subtitulo`, `trend`, `href`, `color`
- Uso: métricas numéricas clicables

**`DashboardCard`**
- Props: `titulo`, `children`, `acciones`
- Uso: sección agrupada (ej. "Por cobrar hoy")

### 8.2 Grid responsive

```html
grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4
```

Referencia actual: `Dashboard.jsx`.

---

## 9. Feedback y errores

| Tipo | Mecanismo |
|------|-----------|
| Error API | `showError(err, fallback)` |
| Éxito | `showSuccess(msg)` |
| Validación inline | `bg-red-50 text-red-600 text-sm` en formulario |
| Advertencia | `showWarning` o banner `amber-50` |

Normalizar `detail` del API con `normalizeDetail()` (soporta string, array Pydantic, objeto `{ mensaje }`).

---

## 10. Accesibilidad y móvil

- Botones táctiles: mínimo 44×44 px
- Sidebar: drawer en móvil (`Layout.jsx`)
- `safe-area-inset` para dispositivos con notch
- Focus visible: `focus:ring-2 focus:ring-primary-500`
- Modales: `aria-label="Cerrar"` en botón ×

---

## 11. Iconografía

- SVG inline en `PageHeader` (`IconPlus`, `IconDownload`)
- Emoji permitido solo en estados operativos/badge cuando aporte claridad (ej. ➕ Crear cliente)
- Preferir iconos SVG consistentes en V2

---

## 12. Checklist UI pre-PR

- [ ] Usa `PageHeader` + layout estándar
- [ ] Usa `Modal.jsx` (no inline)
- [ ] Botones con clases estándar
- [ ] Estados operativos con `EstadoOTBadge` (cuando aplique)
- [ ] Feedback con toast utilities
- [ ] Responsive probado (sm breakpoint mínimo)
- [ ] Componentes compartidos consultados antes de crear nuevos

---

## 13. Roadmap del design system

| Fase | Entregable |
|------|------------|
| DS-1 | `EstadoOTBadge`, `estadoOperativo.js` |
| DS-2 | `PageContainer`, `CardContainer`, `SectionContainer` |
| DS-3 | `KPIWidget`, `DashboardCard` |
| DS-4 | `BandejaOperativa`, `FlujoCobroModal` |
| DS-5 | Migrar modals inline legacy a `Modal.jsx` |
| DS-6 | Storybook o página `/dev/components` (opcional) |

---

## 14. Referencias

- [METODOLOGIA_DESARROLLO_V2.md](./METODOLOGIA_DESARROLLO_V2.md)
- [PLAN_UX_MEJORAS.md](./PLAN_UX_MEJORAS.md)
- [ARQUITECTURA_OPERATIVA_V2.md](./ARQUITECTURA_OPERATIVA_V2.md)
- Código: `frontend/src/components/`, `frontend/tailwind.config.js`
