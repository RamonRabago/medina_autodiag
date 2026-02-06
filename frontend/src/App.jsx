import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Layout from './components/Layout'

import Ventas from './pages/Ventas'
import Clientes from './pages/Clientes'
import Vehiculos from './pages/Vehiculos'
import OrdenesTrabajo from './pages/OrdenesTrabajo'
import DetalleOrdenTrabajo from './pages/DetalleOrdenTrabajo'
import NuevaOrdenTrabajo from './pages/NuevaOrdenTrabajo'
import Servicios from './pages/Servicios'
import Inventario from './pages/Inventario'
import InventarioAlertas from './pages/InventarioAlertas'
import RepuestoForm from './pages/RepuestoForm'
import EntradaInventario from './pages/EntradaInventario'
import Proveedores from './pages/Proveedores'
import OrdenesCompra from './pages/OrdenesCompra'
import NuevaOrdenCompra from './pages/NuevaOrdenCompra'
import CuentasPorPagar from './pages/CuentasPorPagar'
import Citas from './pages/Citas'
import Devoluciones from './pages/Devoluciones'
import Gastos from './pages/Gastos'
import Notificaciones from './pages/Notificaciones'
import Caja from './pages/Caja'
import Auditoria from './pages/Auditoria'
import Configuracion from './pages/Configuracion'

function ProtectedLayout() {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-8 text-slate-500">Cargando...</p>
  if (!user) return <Navigate to="/login" replace />
  return <Layout />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/ventas" element={<Ventas />} />
        <Route path="/clientes" element={<Clientes />} />
        <Route path="/vehiculos" element={<Vehiculos />} />
        <Route path="/ordenes-trabajo" element={<OrdenesTrabajo />} />
        <Route path="/ordenes-trabajo/nueva" element={<NuevaOrdenTrabajo />} />
        <Route path="/ordenes-trabajo/:id" element={<DetalleOrdenTrabajo />} />
        <Route path="/servicios" element={<Servicios />} />
        <Route path="/inventario" element={<Inventario />} />
        <Route path="/inventario/alertas" element={<InventarioAlertas />} />
        <Route path="/inventario/nuevo" element={<RepuestoForm />} />
        <Route path="/inventario/editar/:id" element={<RepuestoForm />} />
        <Route path="/inventario/entrada/:id" element={<EntradaInventario />} />
        <Route path="/proveedores" element={<Proveedores />} />
        <Route path="/ordenes-compra" element={<OrdenesCompra />} />
        <Route path="/ordenes-compra/nueva" element={<NuevaOrdenCompra />} />
        <Route path="/cuentas-por-pagar" element={<CuentasPorPagar />} />
        <Route path="/citas" element={<Citas />} />
        <Route path="/devoluciones" element={<Devoluciones />} />
        <Route path="/gastos" element={<Gastos />} />
        <Route path="/notificaciones" element={<Notificaciones />} />
        <Route path="/caja" element={<Caja />} />
        <Route path="/auditoria" element={<Auditoria />} />
        <Route path="/configuracion" element={<Configuracion />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
