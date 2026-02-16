# Mejoras UX - Medina AutoDiag

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

## Pendiente (opcional)
- [ ] Spinner en botones durante acciones (ej. "Guardando...")
- [ ] Skeleton loading en tablas (alternativa a spinner)
- [ ] Mejorar placeholder en búsquedas
- [ ] Más showSuccess en otras páginas (Clientes, Ventas, Inventario)
