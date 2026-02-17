# Mejoras UX - Medina AutoDiag

**Última actualización:** Febrero 2026

---

## Completado (feb 2026)

### 1. Componentes de carga reutilizables
- **LoadingSpinner**: Spinner animado (sm/md/lg)
- **PageLoading**: Estado de carga para páginas (spinner + mensaje)

### 2. Páginas actualizadas con PageLoading
- App (ProtectedLayout): "Verificando sesión..."
- Dashboard: "Cargando dashboard..."
- OrdenesTrabajo: "Cargando órdenes..."
- DetalleOrdenTrabajo: "Cargando orden..."
- NuevaOrdenTrabajo: "Cargando datos..."
- Ventas: "Cargando ventas..."
- Clientes: "Cargando clientes..."

### 3. Feedback de éxito (showSuccess)
- **DetalleOrdenTrabajo**: Marcar cotización enviada, Autorizar, Iniciar, Finalizar, Entregar
- **OrdenesTrabajo**: Autorizar, Iniciar, Entregar (finalizar ya tenía)

### 4. Ya existente
- Layout responsive: sidebar drawer en móvil, hamburger menu
- Toast (react-hot-toast) para errores y éxito
- min-h-44px y touch-manipulation en botones (accesibilidad táctil)
- safe-area-inset para dispositivos con notch

### 5. Mejoras críticas (feb 2026)
- Dashboard: tarjeta "Utilidad neta del mes" (endpoint /ventas/reportes/utilidad)
- NuevaOrdenTrabajo / RepuestoForm: manejo de errores en carga de config (showError en lugar de catch vacío)
- RepuestoForm, Clientes, Vehiculos: integración numeros.js (aNumero, aEntero, esNumeroValido)
- Validación de NaN: año 1900-2030 en vehículos; precios en repuestos

### 6. Code-splitting
- Vite manualChunks: vendor-react, vendor-query, vendor-ui, vendor-http
- Bundle principal reducido (~682 KB vs ~1 MB anterior)

## Pendiente (opcional)
- [ ] Spinner en botones durante acciones (ej. "Guardando...")
- [ ] Skeleton loading en tablas (alternativa a spinner)
- [ ] Mejorar placeholder en búsquedas
- [ ] Más showSuccess en otras páginas (Clientes, Ventas, Inventario)
