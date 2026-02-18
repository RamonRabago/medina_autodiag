import { useState, useRef, useEffect, useCallback } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import ErrorBoundary from './ErrorBoundary'
import VersionCheck from './VersionCheck'

/** Prefetch de chunks al pasar el mouse (misma ruta que lazy en App) */
const prefetchPage = (path) => {
  const map = {
    '/': () => import('../pages/Dashboard'),
    '/ventas': () => import('../pages/Ventas'),
    '/clientes': () => import('../pages/Clientes'),
    '/vehiculos': () => import('../pages/Vehiculos'),
    '/ordenes-trabajo': () => import('../pages/OrdenesTrabajo'),
    '/servicios': () => import('../pages/Servicios'),
    '/inventario': () => import('../pages/Inventario'),
    '/proveedores': () => import('../pages/Proveedores'),
    '/ordenes-compra': () => import('../pages/OrdenesCompra'),
    '/citas': () => import('../pages/Citas'),
    '/devoluciones': () => import('../pages/Devoluciones'),
    '/gastos': () => import('../pages/Gastos'),
    '/notificaciones': () => import('../pages/Notificaciones'),
    '/caja': () => import('../pages/Caja'),
    '/auditoria': () => import('../pages/Auditoria'),
    '/configuracion': () => import('../pages/Configuracion'),
    '/cuentas-por-pagar': () => import('../pages/CuentasPorPagar'),
    '/prestamos': () => import('../pages/Prestamos'),
    '/asistencia': () => import('../pages/Asistencia'),
    '/vacaciones': () => import('../pages/Vacaciones'),
    '/mi-nomina': () => import('../pages/MiNomina'),
    '/ayuda': () => import('../pages/Ayuda'),
  }
  const fn = map[path]
  if (fn) fn().catch(() => {})
}

const menuItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/ventas', label: 'Ventas', icon: '💰' },
  { path: '/clientes', label: 'Clientes', icon: '👥' },
  { path: '/vehiculos', label: 'Vehículos', icon: '🚗' },
  { path: '/ordenes-trabajo', label: 'Órdenes de trabajo', icon: '🔧' },
  { path: '/servicios', label: 'Servicios', icon: '⚙️' },
  { path: '/inventario', label: 'Inventario', icon: '📦' },
  { path: '/proveedores', label: 'Proveedores', icon: '🏢' },
  { path: '/ordenes-compra', label: 'Órdenes de compra', icon: '🛒' },
  { path: '/citas', label: 'Citas', icon: '📅' },
  { path: '/devoluciones', label: 'Devoluciones', icon: '↩️' },
  { path: '/gastos', label: 'Gastos', icon: '💸' },
  { path: '/notificaciones', label: 'Notificaciones', icon: '🔔', badgeKey: true },
  { path: '/asistencia', label: 'Asistencia', icon: '📋', roles: ['ADMIN', 'CAJA', 'TECNICO', 'EMPLEADO'] },
  { path: '/vacaciones', label: 'Vacaciones', icon: '🏖️', roles: ['ADMIN', 'CAJA', 'TECNICO', 'EMPLEADO'] },
  { path: '/mi-nomina', label: 'Mi nómina', icon: '💵', roles: ['ADMIN', 'CAJA', 'TECNICO', 'EMPLEADO'] },
  { path: '/ayuda', label: 'Ayuda', icon: '📖' },
]

const adminItems = [
  { path: '/caja', label: 'Caja', icon: '🖥️', roles: ['ADMIN', 'CAJA'] },
  { path: '/cuentas-por-pagar', label: 'Cuentas por pagar', icon: '🏦', roles: ['ADMIN', 'CAJA'] },
  { path: '/auditoria', label: 'Auditoría', icon: '📋', roles: ['ADMIN', 'CAJA'] },
  { path: '/prestamos', label: 'Préstamos empleados', icon: '🏦', roles: ['ADMIN'] },
  { path: '/configuracion', label: 'Configuración', icon: '⚙️' },
]

function NavItem({ item, onNavigate, badgeCount }) {
  const showBadge = item.badgeKey && badgeCount != null && badgeCount > 0
  return (
    <NavLink
      to={item.path}
      onMouseEnter={() => prefetchPage(item.path)}
      onClick={onNavigate}
      className={({ isActive: active }) =>
        `flex items-center gap-2 px-3 py-3 rounded-lg mb-1 min-h-[44px] touch-manipulation ${active ? 'bg-slate-100 text-slate-800 font-medium' : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'}`
      }
    >
      <span className="text-lg">{item.icon}</span>
      <span className="text-sm">{item.label}</span>
      {showBadge && (
        <span className="ml-auto text-xs bg-red-500 text-white min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center font-medium">
          {badgeCount > 99 ? '99+' : badgeCount}
        </span>
      )}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notifCount, setNotifCount] = useState(0)
  const mainContentRef = useRef(null)
  const sidebarNavRef = useRef(null)

  useEffect(() => {
    if (mainContentRef.current) mainContentRef.current.scrollTop = 0
  }, [location.pathname])

  const refrescarNotifCount = useCallback(() => {
    if (!user) return
    api.get('/notificaciones/count')
      .then((r) => setNotifCount(r.data?.total_alertas ?? 0))
      .catch(() => setNotifCount(0))
  }, [user])

  useEffect(() => {
    refrescarNotifCount()
  }, [refrescarNotifCount, location.pathname])

  useEffect(() => {
    const handler = () => refrescarNotifCount()
    window.addEventListener('notificaciones-updated', handler)
    return () => window.removeEventListener('notificaciones-updated', handler)
  }, [refrescarNotifCount])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const closeSidebar = () => setSidebarOpen(false)

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100 min-h-0" style={{ height: '100dvh', maxHeight: '100dvh' }}>
      {/* Overlay móvil */}
      <button
        type="button"
        aria-label="Cerrar menú"
        className={`fixed inset-0 z-30 bg-black/50 transition-opacity md:hidden ${sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={closeSidebar}
      />
      {/* Sidebar: drawer en móvil, fijo en desktop */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-40 w-64 max-w-[85vw] bg-white border-r border-slate-200 flex flex-col shrink-0 min-h-0
          transform transition-transform duration-200 ease-out
          pt-[env(safe-area-inset-top)]
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <div className="p-4 border-b border-slate-200 shrink-0 flex justify-center">
          <img src="/static/logo_medina_autodiag.png" alt="MedinaAutoDiag" className="h-12 w-auto object-contain" />
        </div>
        <nav ref={sidebarNavRef} className="flex-1 min-h-0 overflow-y-auto p-2">
          {menuItems.map((item) => {
            if (item.roles && !item.roles.includes(user?.rol)) return null
            return <NavItem key={item.path} item={item} onNavigate={closeSidebar} badgeCount={item.badgeKey ? notifCount : null} />
          })}
          <div className="border-t border-slate-200 mt-4 pt-2">
            <p className="px-3 text-xs text-slate-400 uppercase mb-2">ADMIN</p>
            {adminItems.map((item) => {
              if (item.roles && !item.roles.includes(user?.rol)) return null
              return <NavItem key={item.path} item={item} onNavigate={closeSidebar} />
            })}
          </div>
        </nav>
        <div className="p-4 border-t border-slate-200 shrink-0">
          <p className="text-sm text-slate-600 truncate">{user?.nombre || user?.email}</p>
          <p className="text-xs text-slate-500">{user?.rol}</p>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 min-h-[44px] py-2 text-sm text-red-600 hover:text-red-700 active:text-red-800 touch-manipulation"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>
      {/* Contenido principal */}
      <main className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden">
        {/* Barra superior solo en móvil */}
        <header className="md:hidden shrink-0 flex items-center gap-3 px-4 py-3 pt-[calc(0.75rem+env(safe-area-inset-top))] pb-3 bg-white border-b border-slate-200">
          <button
            type="button"
            aria-label="Abrir menú"
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 rounded-lg text-slate-600 hover:bg-slate-100 active:bg-slate-200 touch-manipulation"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <img src="/static/logo_medina_autodiag.png" alt="MedinaAutoDiag" className="h-8 w-auto object-contain" />
        </header>
        <div ref={mainContentRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-auto p-4 sm:p-6 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </div>
      </main>
      <VersionCheck />
    </div>
  )
}
