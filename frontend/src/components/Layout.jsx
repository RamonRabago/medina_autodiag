import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ErrorBoundary from './ErrorBoundary'

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
  { path: '/notificaciones', label: 'Notificaciones', icon: '🔔' },
  { path: '/ayuda', label: 'Ayuda', icon: '📖' },
]

const adminItems = [
  { path: '/caja', label: 'Caja', icon: '🖥️', roles: ['ADMIN', 'CAJA'] },
  { path: '/cuentas-por-pagar', label: 'Cuentas por pagar', icon: '🏦', roles: ['ADMIN', 'CAJA'] },
  { path: '/auditoria', label: 'Auditoría', icon: '📋', roles: ['ADMIN', 'CAJA'] },
  { path: '/configuracion', label: 'Configuración', icon: '⚙️' },
]

function NavItem({ item, onNavigate }) {
  return (
    <NavLink
      to={item.path}
      onClick={onNavigate}
      className={({ isActive: active }) =>
        `flex items-center gap-2 px-3 py-3 rounded-lg mb-1 min-h-[44px] touch-manipulation ${active ? 'bg-slate-100 text-slate-800 font-medium' : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'}`
      }
    >
      <span className="text-lg">{item.icon}</span>
      <span className="text-sm">{item.label}</span>
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const closeSidebar = () => setSidebarOpen(false)

  return (
    <div className="flex min-h-screen bg-slate-100" style={{ minHeight: '100dvh' }}>
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
          fixed md:static inset-y-0 left-0 z-40 w-64 max-w-[85vw] bg-white border-r border-slate-200 flex flex-col
          transform transition-transform duration-200 ease-out
          pt-[env(safe-area-inset-top)]
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <div className="p-4 border-b border-slate-200 shrink-0">
          <h1 className="font-bold text-lg text-slate-800">MedinaAutoDiag</h1>
          <p className="text-xs text-slate-500">Taller mecánico</p>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {menuItems.map((item) => (
            <NavItem key={item.path} item={item} onNavigate={closeSidebar} />
          ))}
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
      <main className="flex-1 flex flex-col min-w-0 min-h-screen">
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
          <h1 className="font-semibold text-slate-800 truncate">MedinaAutoDiag</h1>
        </header>
        <div className="flex-1 overflow-auto p-4 sm:p-6 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </div>
      </main>
    </div>
  )
}
