import { lazy, Suspense } from 'react'
import { Toaster } from 'react-hot-toast'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import PageLoading from './components/PageLoading'
import Layout from './components/Layout'

// Páginas de auth (se cargan primero al entrar a login/registro)
const Login = lazy(() => import('./pages/Login'))
const Registro = lazy(() => import('./pages/Registro'))
const OlvideContrasena = lazy(() => import('./pages/OlvideContrasena'))
const RestablecerContrasena = lazy(() => import('./pages/RestablecerContrasena'))

// Páginas principales (lazy: se descargan al navegar)
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Ventas = lazy(() => import('./pages/Ventas'))
const VentasIngresos = lazy(() => import('./pages/VentasIngresos'))
const Clientes = lazy(() => import('./pages/Clientes'))
const Vehiculos = lazy(() => import('./pages/Vehiculos'))
const OrdenesTrabajo = lazy(() => import('./pages/OrdenesTrabajo'))
const DetalleOrdenTrabajo = lazy(() => import('./pages/DetalleOrdenTrabajo'))
const NuevaOrdenTrabajo = lazy(() => import('./pages/NuevaOrdenTrabajo'))
const Servicios = lazy(() => import('./pages/Servicios'))
const Inventario = lazy(() => import('./pages/Inventario'))
const Kardex = lazy(() => import('./pages/Kardex'))
const InventarioAlertas = lazy(() => import('./pages/InventarioAlertas'))
const RepuestoForm = lazy(() => import('./pages/RepuestoForm'))
const EntradaInventario = lazy(() => import('./pages/EntradaInventario'))
const Proveedores = lazy(() => import('./pages/Proveedores'))
const OrdenesCompra = lazy(() => import('./pages/OrdenesCompra'))
const NuevaOrdenCompra = lazy(() => import('./pages/NuevaOrdenCompra'))
const EditarOrdenCompra = lazy(() => import('./pages/EditarOrdenCompra'))
const CuentasPorPagar = lazy(() => import('./pages/CuentasPorPagar'))
const Citas = lazy(() => import('./pages/Citas'))
const Devoluciones = lazy(() => import('./pages/Devoluciones'))
const Gastos = lazy(() => import('./pages/Gastos'))
const Notificaciones = lazy(() => import('./pages/Notificaciones'))
const Caja = lazy(() => import('./pages/Caja'))
const Auditoria = lazy(() => import('./pages/Auditoria'))
const Configuracion = lazy(() => import('./pages/Configuracion'))
const UsuarioForm = lazy(() => import('./pages/UsuarioForm'))
const Prestamos = lazy(() => import('./pages/Prestamos'))
const Asistencia = lazy(() => import('./pages/Asistencia'))
const Vacaciones = lazy(() => import('./pages/Vacaciones'))
const MiNomina = lazy(() => import('./pages/MiNomina'))
const Ayuda = lazy(() => import('./pages/Ayuda'))

function ProtectedLayout() {
  const { user, loading } = useAuth()
  if (loading) return <PageLoading mensaje="Verificando sesión..." />
  if (!user) return <Navigate to="/login" replace />
  return <Layout />
}

function AppRoutes() {
  return (
    <Suspense fallback={<PageLoading mensaje="Cargando..." />}>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
      <Route path="/olvide-contrasena" element={<OlvideContrasena />} />
      <Route path="/restablecer-contrasena" element={<RestablecerContrasena />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/ventas" element={<Ventas />} />
        <Route path="/ventas/ingresos" element={<VentasIngresos />} />
        <Route path="/clientes" element={<Clientes />} />
        <Route path="/vehiculos" element={<Vehiculos />} />
        <Route path="/ordenes-trabajo" element={<OrdenesTrabajo />} />
        <Route path="/ordenes-trabajo/nueva" element={<NuevaOrdenTrabajo />} />
        <Route path="/ordenes-trabajo/:id" element={<DetalleOrdenTrabajo />} />
        <Route path="/servicios" element={<Servicios />} />
        <Route path="/inventario" element={<Inventario />} />
        <Route path="/inventario/kardex/:id" element={<Kardex />} />
        <Route path="/inventario/alertas" element={<InventarioAlertas />} />
        <Route path="/inventario/nuevo" element={<RepuestoForm />} />
        <Route path="/inventario/editar/:id" element={<RepuestoForm />} />
        <Route path="/inventario/entrada/:id" element={<EntradaInventario />} />
        <Route path="/proveedores" element={<Proveedores />} />
        <Route path="/ordenes-compra" element={<OrdenesCompra />} />
        <Route path="/ordenes-compra/nueva" element={<NuevaOrdenCompra />} />
        <Route path="/ordenes-compra/editar/:id" element={<EditarOrdenCompra />} />
        <Route path="/cuentas-por-pagar" element={<CuentasPorPagar />} />
        <Route path="/citas" element={<Citas />} />
        <Route path="/devoluciones" element={<Devoluciones />} />
        <Route path="/gastos" element={<Gastos />} />
        <Route path="/notificaciones" element={<Notificaciones />} />
        <Route path="/caja" element={<Caja />} />
        <Route path="/auditoria" element={<Auditoria />} />
        <Route path="/configuracion" element={<Configuracion />} />
        <Route path="/configuracion/usuarios/nuevo" element={<UsuarioForm />} />
        <Route path="/configuracion/usuarios/editar/:id" element={<UsuarioForm />} />
        <Route path="/prestamos" element={<Prestamos />} />
        <Route path="/asistencia" element={<Asistencia />} />
        <Route path="/vacaciones" element={<Vacaciones />} />
        <Route path="/mi-nomina" element={<MiNomina />} />
        <Route path="/ayuda" element={<Ayuda />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <div className="h-full min-h-0" style={{ height: '100%' }}>
      <Toaster position="top-center" toastOptions={{ duration: 4000 }} />
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </div>
  )
}
