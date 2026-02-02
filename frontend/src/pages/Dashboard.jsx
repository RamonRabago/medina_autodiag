import { useState, useEffect } from 'react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const requests = [
      api.get('/clientes/', { params: { limit: 1 } }),
      api.get('/ordenes-trabajo/', { params: { limit: 1 } }),
    ]
    if (user?.rol === 'ADMIN' || user?.rol === 'CAJA') {
      requests.push(api.get('/ordenes-trabajo/estadisticas/dashboard'))
      requests.push(api.get('/inventario/reportes/dashboard'))
    }
    if (user?.rol === 'ADMIN') {
      requests.push(api.get('/admin/dashboard/resumen'))
    }

    Promise.allSettled(requests).then((results) => {
      let i = 0
      const clientesRes = results[i++]
      const ordenesRes = results[i++]
      const ordenesStats = (user?.rol === 'ADMIN' || user?.rol === 'CAJA') ? results[i++] : null
      const inventarioRes = (user?.rol === 'ADMIN' || user?.rol === 'CAJA') ? results[i++] : null
      const alertasRes = user?.rol === 'ADMIN' ? results[i++] : null

      const clientesData = clientesRes?.status === 'fulfilled' ? clientesRes.value.data : null
      const ordenesData = ordenesRes?.status === 'fulfilled' ? ordenesRes.value.data : null
      const clientesTotal = clientesData?.total ?? (Array.isArray(clientesData) ? clientesData.length : clientesData?.clientes?.length ?? 0)
      const ordenesTotal = ordenesData?.total ?? (Array.isArray(ordenesData) ? ordenesData.length : ordenesData?.ordenes?.length ?? 0)
      const ordenesStatsData = ordenesStats?.status === 'fulfilled' ? ordenesStats.value.data : null
      const inventarioData = inventarioRes?.status === 'fulfilled' ? inventarioRes.value.data?.metricas : null
      const alertasData = alertasRes?.status === 'fulfilled' ? alertasRes.value.data : null

      setStats({
        clientes: clientesTotal,
        ordenes: ordenesTotal,
        ordenes_hoy: ordenesStatsData?.ordenes_hoy ?? 0,
        total_facturado: ordenesStatsData?.total_facturado ?? 0,
        ordenes_urgentes: ordenesStatsData?.ordenes_urgentes ?? 0,
        ordenes_por_estado: ordenesStatsData?.ordenes_por_estado ?? [],
        inventario: inventarioData,
        alertas: alertasData,
      })
    }).finally(() => setLoading(false))
  }, [user?.rol])

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-slate-500 text-sm font-medium">Clientes</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.clientes ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-slate-500 text-sm font-medium">Órdenes de trabajo</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.ordenes ?? 0}</p>
        </div>
        {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (
          <>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-slate-500 text-sm font-medium">Órdenes hoy</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.ordenes_hoy ?? 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-slate-500 text-sm font-medium">Total facturado (ordenes)</h3>
              <p className="text-2xl font-bold text-green-700 mt-1">${(Number(stats?.total_facturado) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-slate-500 text-sm font-medium">Órdenes urgentes</h3>
              <p className="text-2xl font-bold text-amber-600 mt-1">{stats?.ordenes_urgentes ?? 0}</p>
            </div>
          </>
        )}
        {stats?.inventario && (
          <>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-slate-500 text-sm font-medium">Valor inventario</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">${(Number(stats.inventario?.valor_inventario) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-slate-500 text-sm font-medium">Productos activos</h3>
              <p className="text-2xl font-bold text-slate-800 mt-1">{stats.inventario?.productos_activos ?? 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-slate-500 text-sm font-medium">Stock bajo / Sin stock</h3>
              <p className="text-2xl font-bold text-amber-600 mt-1">{stats.inventario?.productos_stock_bajo ?? 0} / {stats.inventario?.productos_sin_stock ?? 0}</p>
            </div>
          </>
        )}
        {stats?.alertas && (stats.alertas.pendientes > 0 || stats.alertas.criticas > 0) && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-slate-500 text-sm font-medium">Alertas pendientes</h3>
            <p className="text-2xl font-bold text-red-600 mt-1">{stats.alertas.pendientes ?? 0} ({stats.alertas.criticas ?? 0} críticas)</p>
          </div>
        )}
      </div>
      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && stats?.ordenes_por_estado?.length > 0 && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h3 className="text-slate-700 font-semibold mb-4">Órdenes por estado</h3>
          <div className="flex flex-wrap gap-3">
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
