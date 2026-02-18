# Análisis: Tiempos de Carga en Medina AutoDiag

**Fecha:** 2025-02-17  
**Objetivo:** Explicar de qué depende la velocidad de carga y qué se puede mejorar.

---

## 1. ¿De qué depende el tiempo de carga?

El tiempo que tarda en verse una página útil depende de **varios factores en cadena**:

```
[Navegador] → Descarga HTML/JS/CSS → Ejecuta React → Pide datos al backend → Renderiza
     │               │                     │                   │                │
   ~100ms         ~500ms–2s            ~50ms            ~200ms–3s           ~50ms
```

### 1.1 Carga inicial de la aplicación (primera visita)

| Factor | Qué es | Situación actual | Impacto |
|--------|--------|------------------|---------|
| **Bundle JS** | Todo el código React que se descarga | ~685 kB (index) + vendors (~370 kB) | **Alto** — Vite ya hace code splitting (vendor-react, vendor-query, etc.) pero el `index` principal es grande |
| **CSS** | Estilos | ~66 kB (Tailwind) | Bajo |
| **Import estático** | Todas las páginas se cargan al inicio | En `App.jsx` hay ~40 imports directos | **Alto** — No hay lazy loading de rutas; al entrar a /login ya se descarga Dashboard, Inventario, Configuracion, etc. |
| **Autenticación** | Verificar token antes de mostrar contenido | `PageLoading` mientras `loading` | Correcto; añade ~100–500 ms si hay llamada a /me o similar |

### 1.2 Carga de datos (API)

| Factor | Qué es | Situación actual | Impacto |
|--------|--------|------------------|---------|
| **Número de requests** | Cuántas llamadas HTTP hace cada página | Dashboard: **12+ requests** en paralelo (ADMIN). Configuracion: **9 requests**. CuentasPorPagar: **3**. | **Alto** — Más requests = más latencia total (aunque sean en paralelo, la más lenta define el total) |
| **Tiempo de respuesta del backend** | Cuánto tarda cada endpoint | Depende de queries DB, N+1, índices | **Variable** — Con BD local suele ser <200 ms; con Railway/remoto puede ser 300–800 ms |
| **Tamaño del payload** | Cantidad de datos en cada respuesta | Listas con limit 50–500; algunos endpoints traen todo | **Medio** — JSON de 50 clientes es aceptable; 500 repuestos con detalles puede ser pesado |
| **Waterfall** | Requests que dependen unos de otros | En su mayoría se usan `Promise.all` / `Promise.allSettled` | **Bien** — Las páginas cargan datos en paralelo, no en secuencia |
| **Caché** | Reutilizar datos ya cargados | Casi no hay; cada visita recarga todo | **Alto** — React Query está instalado pero poco usado; no hay stale-while-revalidate |

### 1.3 Base de datos (backend)

| Factor | Qué es | Situación actual | Impacto |
|--------|--------|------------------|---------|
| **N+1 queries** | Por cada fila, una query extra (ej. proveedor por orden) | Presente en `listar_cuentas_por_pagar`, `ordenes_compra`, etc. | **Alto** — 50 órdenes = 50+ queries extra |
| **Índices** | Columnas indexadas para filtrar/ordenar | Hay índices en PK/FK; falta revisar filtros frecuentes | **Medio** — Puede haber cuellos de botella en listados grandes |
| **joinedload** | Cargar relaciones en una sola query | Algunos endpoints lo usan (Auditoria, exportaciones); otros no | **Variable** |
| **Paginación** | No traer todo de golpe | La mayoría de listados tiene skip/limit | **Bien** |

### 1.4 Red e infraestructura

| Factor | Qué es | Situación actual | Impacto |
|--------|--------|------------------|---------|
| **Latencia** | Tiempo ida y vuelta al servidor | Local: ~10 ms. Railway/Internet: 100–400 ms | **Alto** en producción |
| **CDN / estáticos** | Servir JS/CSS desde edge | El backend sirve el SPA desde `frontend/dist` | **Medio** — Sin CDN, todo viene del mismo origen |
| **Compresión** | Gzip/Brotli en respuestas | Depende de la configuración del servidor | Revisar si está habilitado |

---

## 2. Páginas más afectadas (estimación)

| Página | Requests | Datos | Probable cuello de botella |
|--------|----------|-------|----------------------------|
| **Dashboard** | 12+ (ADMIN) | Muchos resúmenes | Varios endpoints; el más lento bloquea la visión completa |
| **Configuracion** | 9 en paralelo | Catálogos (500+ items algunos) | 9 APIs; si una tarda, loading hasta que todas terminen |
| **CuentasPorPagar** | 3 (OC + manuales + proveedores) | Listas + aging | Menos crítico; 3 requests manejables |
| **Inventario** | Variable (repuestos + movimientos) | Puede ser pesado con muchos ítems | Listados con limit alto |
| **OrdenesTrabajo** | 1–2 al listar | Órdenes con relaciones | Posible N+1 en detalles |
| **Clientes / Proveedores** | 1–2 | Lista paginada | Normal |
| **Caja** | 3–4 (turno + corte + alertas + histórico) | Datos del turno actual | Aceptable |

---

## 3. Mejoras posibles (sin orden de prioridad)

### 3.1 Frontend — Carga inicial

| Mejora | Descripción | Esfuerzo | Impacto |
|--------|-------------|----------|---------|
| **Lazy loading de rutas** | `React.lazy(() => import('./pages/Dashboard'))` + `Suspense` | Bajo | **Alto** — Solo se descarga el código de la página al entrar; la primera carga baja bastante |
| **Preload en hover** | Al pasar el mouse sobre un link del menú, hacer prefetch del módulo | Medio | Medio |
| **Reducir bundle index** | Revisar qué entra en el chunk principal; quizá mover más a vendors | Medio | Medio |

### 3.2 Frontend — Datos

| Mejora | Descripción | Esfuerzo | Impacto |
|--------|-------------|----------|---------|
| **React Query en más páginas** | Usar `useQuery` con `staleTime` para no recalcular al volver | Medio | **Alto** — Dashboard, Configuracion, listados: cache 30 s–1 min |
| **Endpoint agregado para Dashboard** | Un solo `GET /dashboard` que devuelva todo lo que necesita | Medio | **Alto** — De 12 requests a 1; menos latencia total |
| **Endpoint agregado para Configuracion** | `GET /configuracion/catalogos` con todos los catálogos | Bajo | **Alto** — De 9 a 1 request |
| **Cargar por pestaña** | En Configuracion, cargar solo categorías-servicios primero; el resto al cambiar tab | Medio | Medio |
| **Skeleton / placeholder** | Mostrar estructura vacía mientras cargan datos | Bajo | **Percepción** — La página “responde” antes |

### 3.3 Backend — Base de datos

| Mejora | Descripción | Esfuerzo | Impacto |
|--------|-------------|----------|---------|
| **joinedload en listados** | Evitar N+1 en cuentas-por-pagar, órdenes de compra, etc. | Bajo–Medio | **Alto** donde hay N+1 |
| **Índices en filtros** | Índices en columnas usadas en WHERE/ORDER (fecha, estado, etc.) | Bajo | Medio (con muchos datos) |
| **Comprimir respuestas** | Gzip en FastAPI (middleware o reverse proxy) | Bajo | Medio |

### 3.4 Backend — API

| Mejora | Descripción | Esfuerzo | Impacto |
|--------|-------------|----------|---------|
| **Endpoints agregados** | Dashboard y Configuracion con un solo request | Medio | **Alto** |
| **Límites razonables** | Revisar si limit 500 es necesario en todos los catálogos | Bajo | Bajo |

### 3.5 Infraestructura

| Mejora | Descripción | Esfuerzo | Impacto |
|--------|-------------|----------|---------|
| **CDN para estáticos** | Servir JS/CSS desde CDN (Cloudflare, etc.) | Medio | Medio |
| **Servidor más cercano** | Railway/región cerca de usuarios | Depende del plan | Alto si hay mucha latencia |
| **HTTP/2** | Multiplexing de requests | Suele venir por defecto | Bajo–Medio |

---

## 4. Resumen: de qué depende la velocidad

1. **Carga inicial (primera visita):**  
   - Tamaño del bundle JS (actualmente ~1 MB total).  
   - No hay lazy loading → se descarga todo desde el principio.

2. **Navegación entre páginas:**  
   - Ya está descargado el código → es rápido.  
   - Cada página hace sus requests → el cuello de botella pasa a la API.

3. **Tiempo hasta “datos útiles”:**  
   - Número de requests (ej. Dashboard: 12).  
   - Tiempo de cada endpoint (DB, N+1, índices).  
   - Latencia de red (muy relevante en producción).

4. **Percepción de velocidad:**  
   - Loading indefinido vs skeleton/placeholder.  
   - Caché (React Query) para no recargar al volver.

---

## 5. Recomendaciones prioritarias

Si se prioriza por **impacto / esfuerzo**:

1. **Lazy loading de rutas** — Mucho impacto, poco esfuerzo.  
2. **Endpoint agregado Dashboard** — De 12 a 1 request; mejora clara.  
3. **Endpoint agregado Configuracion** — De 9 a 1 request.  
4. **React Query con cache** — Mejora al navegar entre páginas.  
5. **Eliminar N+1 en listados críticos** — Menos carga en DB y respuestas más rápidas.

---

## 6. Cómo medir antes y después

- **Chrome DevTools** → Network: tiempo de cada request, tamaño de respuestas.  
- **Lighthouse** → Performance, First Contentful Paint (FCP), Time to Interactive (TTI).  
- **React DevTools** → Profiler para ver renders lentos.

Con eso se puede comprobar si las mejoras tienen el efecto esperado.
