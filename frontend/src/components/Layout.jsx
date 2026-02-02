import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

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
]

const adminItems = [
  { path: '/caja', label: 'Caja', icon: '🖥️', roles: ['ADMIN', 'CAJA'] },
  { path: '/auditoria', label: 'Auditoría', icon: '📋' },
  { path: '/configuracion', label: 'Configuración', icon: '⚙️' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen bg-slate-100">
      <aside className="w-64 bg-slate-800 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h1 className="font-bold text-lg">MedinaAutoDiag</h1>
          <p className="text-xs text-slate-400">Taller mecánico</p>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg mb-1 ${isActive ? 'bg-primary-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`
              }
            >
              <span>{item.icon}</span>
              <span className="text-sm">{item.label}</span>
            </NavLink>
          ))}
          <div className="border-t border-slate-700 mt-4 pt-2">
            <p className="px-3 text-xs text-slate-500 uppercase mb-2">ADMIN</p>
            {adminItems.map((item) => {
              if (item.roles && !item.roles.includes(user?.rol)) return null
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg mb-1 ${isActive ? 'bg-primary-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`
                  }
                >
                  <span>{item.icon}</span>
                  <span className="text-sm">{item.label}</span>
                </NavLink>
              )
            })}
          </div>
        </nav>
        <div className="p-4 border-t border-slate-700">
          <p className="text-sm text-slate-400 truncate">{user?.nombre || user?.email}</p>
          <p className="text-xs text-slate-500">{user?.rol}</p>
          <button onClick={handleLogout} className="mt-2 text-sm text-red-400 hover:text-red-300">
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
