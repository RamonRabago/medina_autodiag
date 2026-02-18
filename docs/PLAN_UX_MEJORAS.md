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

### 7. showSuccess ampliado (feb 2026)
- **Ventas**: crear venta, registrar pago
- **Clientes**: crear/editar cliente, agregar vehículo
- **Configuracion**: guardar categorías, bodegas, ubicaciones, estantes, niveles, filas, festivos; bodegas usuario; comisiones; eliminar
- **Inventario**: desactivar, eliminar permanente, reactivar, ajuste, entrada masiva, orden desde sugerencia, exportar

### 8. Spinner en botones (feb 2026)
- **Ventas**: Guardar venta, Guardar cambios, Registrar pago
- **Clientes**: Guardar cliente, Agregar vehículo, Eliminar cliente
- **Configuracion**: Guardar/Crear, Eliminar, Guardar bodegas usuario, comisiones
- **Inventario**: Procesar archivo, Desactivar, Ajustar, Eliminar permanentemente

### 9. Inventario: Skeleton y placeholder (feb 2026)
- **TableSkeleton**: Componente reutilizable para tablas en carga
- **Inventario**: Skeleton de 12 filas durante carga inicial; placeholder de búsqueda "Ej: REF-001, Filtro aceite, Bosch..."

## Pendiente (opcional)
- [ ] Skeleton loading en Ventas, Clientes, OrdenesTrabajo
- [ ] Mejorar placeholder en búsquedas (Clientes, Ventas, etc.)
