import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageLoading from '../components/PageLoading'
import { formatearFechaHora } from '../utils/fechas'
import { useApiQuery } from '../hooks/useApi'
import api from '../services/api'

export default function Dashboard() {
  const { user } = useAuth()
  const [periodoFacturado, setPeriodoFacturado] = useState('mes')

  const rol = user?.rol?.value ?? user?.rol ?? ''
  const { data: stats, isLoading, error, isError } = useApiQuery(
    ['dashboard', rol, periodoFacturado],
    () => api.get('/dashboard', { params: { periodo: periodoFacturado } }).then((r) => r.data),
    { staleTime: 45 * 1000 }
  )

  const apiErrorsCount = isError ? 1 : 0

  if (isLoading) return <PageLoading mensaje="Cargando dashboard..." />

  return (
    <div className="min-h-0">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Dashboard</h1>
      {apiErrorsCount > 0 && (
        <p className="mb-4 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
          Algunos datos no están disponibles ({apiErrorsCount} {apiErrorsCount === 1 ? 'API' : 'APIs'} no respondieron).
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white rounded-lg shadow p-4 sm:p-6">
          <h3 className="text-slate-500 text-sm font-medium">Clientes</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.clientes ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 sm:p-6">
          <h3 className="text-slate-500 text-sm font-medium">Órdenes de trabajo</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.ordenes ?? 0}</p>
        </div>
        {(rol === 'ADMIN' || rol === 'CAJA') && (
          <>
            {/* Ingresos / operación */}
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">Órdenes hoy</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.ordenes_hoy ?? 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <div className="flex justify-between items-center gap-2 flex-wrap">
                <h3 className="text-slate-500 text-sm font-medium">Ventas del periodo</h3>
                <select
                  value={periodoFacturado}
                  onChange={(e) => setPeriodoFacturado(e.target.value)}
                  className="text-sm sm:text-xs border border-slate-200 rounded px-3 py-2 min-h-[44px] sm:min-h-0 text-slate-600 bg-white focus:ring-1 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
                >
                  <option value="mes">Este mes</option>
                  <option value="mes_pasado">Mes pasado</option>
                  <option value="ano">Este año</option>
                  <option value="acumulado">Acumulado</option>
                </select>
              </div>
              <p className="text-2xl font-bold text-slate-800 mt-1">${(Number(stats?.total_ventas_periodo) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
              <p className="text-xs text-slate-400 mt-2">
                {periodoFacturado === 'mes' && 'Total ventas este mes (por fecha venta)'}
                {periodoFacturado === 'mes_pasado' && 'Total ventas mes pasado'}
                {periodoFacturado === 'ano' && 'Total ventas este año'}
                {periodoFacturado === 'acumulado' && 'Suma total de ventas'}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">Cobrado</h3>
              <p className="text-2xl font-bold text-green-700 mt-1">${(Number(stats?.total_facturado) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
              <p className="text-xs text-slate-400 mt-2">
                {periodoFacturado === 'mes' && 'Pagos recibidos este mes'}
                {periodoFacturado === 'mes_pasado' && 'Pagos recibidos mes pasado'}
                {periodoFacturado === 'ano' && 'Pagos recibidos este año'}
                {periodoFacturado === 'acumulado' && 'Suma de todos los pagos recibidos'}
              </p>
              <Link to="/ventas/ingresos" className="text-sm text-primary-600 hover:text-primary-700 font-medium mt-2 inline-block py-2 min-h-[44px] leading-normal touch-manipulation">
                Ver detalle por fechas →
              </Link>
            </div>
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">Órdenes urgentes</h3>
              <p className="text-2xl font-bold text-amber-600 mt-1">{stats?.ordenes_urgentes ?? 0}</p>
            </div>

            {/* Egresos / pasivo */}
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">
                {periodoFacturado === 'mes' ? 'Gastos del mes' : periodoFacturado === 'mes_pasado' ? 'Gastos del mes pasado' : periodoFacturado === 'ano' ? 'Gastos del año' : 'Gastos acumulados'}
              </h3>
              <p className="text-2xl font-bold text-red-600 mt-1">${(Number(stats?.total_gastos_mes) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
            </div>
            <Link
              to="/ventas"
              className="bg-white rounded-lg shadow p-4 sm:p-6 block border-2 border-transparent hover:border-emerald-300 active:border-emerald-400 hover:shadow-md transition-all touch-manipulation min-h-[88px] flex flex-col justify-center"
            >
              <h3 className="text-slate-500 text-sm font-medium">
                {periodoFacturado === 'mes' ? 'Utilidad neta del mes' : periodoFacturado === 'mes_pasado' ? 'Utilidad neta del mes pasado' : periodoFacturado === 'ano' ? 'Utilidad neta del año' : 'Utilidad neta acumulada'}
              </h3>
              <p className="text-2xl font-bold mt-1">
                <span className={(Number(stats?.utilidad_neta_mes) || 0) >= 0 ? 'text-emerald-700' : 'text-red-600'}>
                  ${(Number(stats?.utilidad_neta_mes) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                </span>
              </p>
              <p className="text-xs text-slate-400 mt-2">Ventas − CMV − Gastos → Ver reporte</p>
            </Link>
            <Link
              to="/cuentas-por-pagar"
              className="bg-white rounded-lg shadow p-4 sm:p-6 block border-2 border-transparent hover:border-amber-400 active:border-amber-500 hover:shadow-md transition-all touch-manipulation min-h-[88px] flex flex-col justify-center"
            >
              <h3 className="text-slate-500 text-sm font-medium">Saldo pendiente proveedores</h3>
              <p className="text-2xl font-bold mt-1">
                <span className={(stats?.cuentas_por_pagar?.total_saldo_pendiente ?? 0) > 0 ? 'text-amber-700' : 'text-slate-800'}>
                  ${(Number(stats?.cuentas_por_pagar?.total_saldo_pendiente) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                </span>
              </p>
              <p className="text-xs text-slate-400 mt-2">
                {(stats?.cuentas_por_pagar?.total_cuentas ?? 0)} cuenta(s) → Ver detalle
              </p>
            </Link>

            {/* Operación caja */}
            <Link
              to="/caja"
              className={`rounded-lg shadow p-4 sm:p-6 block border-2 transition-all touch-manipulation min-h-[88px] flex flex-col justify-center ${
                stats?.turno_caja?.estado === 'ABIERTO'
                  ? 'bg-green-50 border-green-200 hover:border-green-300 active:border-green-400'
                  : 'bg-white border-transparent hover:border-slate-300 hover:shadow-md'
              }`}
            >
              <h3 className="text-slate-500 text-sm font-medium">Turno de caja</h3>
              <p className="text-2xl font-bold mt-1">
                <span className={stats?.turno_caja?.estado === 'ABIERTO' ? 'text-green-700' : 'text-slate-800'}>
                  {stats?.turno_caja?.estado === 'ABIERTO' ? 'Abierto' : 'Sin turno abierto'}
                </span>
              </p>
              <p className="text-xs text-slate-400 mt-2">
                {stats?.turno_caja?.estado === 'ABIERTO'
                  ? `Apertura: ${(Number(stats.turno_caja?.monto_apertura) || 0).toFixed(2)} → Ir a Caja`
                  : 'Ir a Caja para abrir turno'}
              </p>
            </Link>

            {/* Citas próximas */}
            <Link
              to="/citas"
              className="bg-white rounded-lg shadow p-4 sm:p-6 block border-2 border-transparent hover:border-blue-300 active:border-blue-400 hover:shadow-md transition-all touch-manipulation min-h-[88px]"
            >
              <h3 className="text-slate-500 text-sm font-medium">Citas próximas</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.citas_proximas?.length ?? 0}</p>
              <p className="text-xs text-slate-400 mt-2">Confirmadas → Ver Citas</p>
              {(stats?.citas_proximas?.length ?? 0) > 0 && (
                <ul className="mt-3 space-y-1 text-xs text-slate-600 max-h-24 overflow-y-auto">
                  {stats.citas_proximas.slice(0, 4).map((c) => (
                    <li key={c.id_cita} className="truncate">
                      {formatearFechaHora(c.fecha_hora)} — {c.cliente_nombre || '-'}
                    </li>
                  ))}
                </ul>
              )}
            </Link>

            {/* Devoluciones del mes */}
            <Link
              to="/devoluciones"
              className="bg-white rounded-lg shadow p-4 sm:p-6 block border-2 border-transparent hover:border-slate-300 active:border-slate-400 hover:shadow-md transition-all touch-manipulation min-h-[88px]"
            >
              <h3 className="text-slate-500 text-sm font-medium">Devoluciones del mes</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.devoluciones_mes ?? 0}</p>
              <p className="text-xs text-slate-400 mt-2">Productos devueltos → Ver detalle</p>
            </Link>

            {/* Órdenes de compra */}
            {stats?.ordenes_compra_alertas && (
              <Link
                to={stats.ordenes_compra_alertas.ordenes_sin_recibir > 0 ? '/ordenes-compra?pendientes=1' : '/ordenes-compra'}
                className={`rounded-lg shadow p-4 sm:p-6 block border-2 transition-all touch-manipulation min-h-[88px] flex flex-col justify-center ${
                  (stats.ordenes_compra_alertas.ordenes_vencidas || 0) > 0
                    ? 'bg-amber-50 border-amber-300 hover:border-amber-400 active:border-amber-500 hover:shadow-md'
                    : 'bg-white border-transparent hover:border-slate-300 hover:shadow-md'
                }`}
              >
                <h3 className="text-slate-500 text-sm font-medium">Órdenes sin recibir</h3>
                <p className="text-2xl font-bold mt-1">
                  <span className={(stats.ordenes_compra_alertas.ordenes_vencidas || 0) > 0 ? 'text-amber-700' : 'text-slate-800'}>
                    {stats.ordenes_compra_alertas.ordenes_sin_recibir ?? 0}
                  </span>
                  {(stats.ordenes_compra_alertas.ordenes_vencidas || 0) > 0 && (
                    <span className="ml-2 text-sm font-normal text-amber-600">
                      ({stats.ordenes_compra_alertas.ordenes_vencidas} vencidas)
                    </span>
                  )}
                </p>
                <p className="text-xs text-slate-400 mt-2">Ver detalle →</p>
              </Link>
            )}
          </>
        )}
        {stats?.inventario && (
          <>
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">Valor inventario</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">${(Number(stats.inventario?.valor_inventario?.valor_compra ?? stats.inventario?.valor_inventario) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">Productos activos</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">{stats.inventario?.productos_activos ?? 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h3 className="text-slate-500 text-sm font-medium">Stock bajo / Sin stock</h3>
              <p className="text-2xl font-bold text-amber-600 mt-1">{stats.inventario?.productos_stock_bajo ?? 0} / {stats.inventario?.productos_sin_stock ?? 0}</p>
            </div>
            <Link
              to="/inventario/alertas"
              className="bg-white rounded-lg shadow p-4 sm:p-6 block border-2 border-transparent hover:border-amber-400 active:border-amber-500 hover:shadow-md transition-all touch-manipulation min-h-[88px]"
            >
              <h3 className="text-slate-500 text-sm font-medium">Alertas inventario</h3>
              <p className="text-2xl font-bold mt-1">
                <span className={stats.inventario?.total_alertas > 0 ? 'text-amber-600' : 'text-slate-800'}>
                  {stats.inventario?.total_alertas ?? 0}
                </span>
              </p>
              <p className="text-xs text-slate-400 mt-2">Ver detalle →</p>
            </Link>
          </>
        )}
        {stats?.alertas && (stats.alertas.pendientes > 0 || stats.alertas.criticas > 0) && (
          <div className="bg-white rounded-lg shadow p-4 sm:p-6">
            <h3 className="text-slate-500 text-sm font-medium">Alertas pendientes</h3>
            <p className="text-2xl font-bold text-red-600 mt-1">{stats.alertas.pendientes ?? 0} ({stats.alertas.criticas ?? 0} críticas)</p>
          </div>
        )}
      </div>
      {(rol === 'ADMIN' || rol === 'CAJA') && stats?.ordenes_por_estado?.length > 0 && (
        <div className="mt-4 sm:mt-6 bg-white rounded-lg shadow p-4 sm:p-6">
          <h3 className="text-slate-700 font-semibold mb-4">Órdenes por estado</h3>
          <div className="flex flex-wrap gap-2 sm:gap-3">
            {stats.ordenes_por_estado.map((item) => (
              <span key={String(item.estado)} className="px-4 py-2 bg-slate-100 rounded-lg text-sm">
                <span className="font-medium text-slate-800">{typeof item.estado === 'object' ? item.estado?.value ?? item.estado : item.estado}</span>
                <span className="ml-2 text-slate-600">{item.total}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
