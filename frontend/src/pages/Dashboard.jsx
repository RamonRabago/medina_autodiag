import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.get('/ventas/'),
      api.get('/clientes/'),
      api.get('/ordenes-trabajo/'),
    ]).then(([rV, rC, rO]) => {
      const ventas = rV.status === 'fulfilled' ? (rV.value.data?.ventas ?? rV.value.data ?? []) : []
      const clientes = rC.status === 'fulfilled' ? (rC.value.data?.clientes ?? rC.value.data ?? []) : []
      const ordenes = rO.status === 'fulfilled' ? (rO.value.data?.ordenes ?? rO.value.data ?? []) : []
      setStats({
        ventas: Array.isArray(ventas) ? ventas.length : 0,
        clientes: Array.isArray(clientes) ? clientes.length : 0,
        ordenes: Array.isArray(ordenes) ? ordenes.length : 0,
      })
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-slate-500 text-sm font-medium">Ventas</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.ventas ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-slate-500 text-sm font-medium">Clientes</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.clientes ?? 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-slate-500 text-sm font-medium">Órdenes de trabajo</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{stats?.ordenes ?? 0}</p>
        </div>
      </div>
    </div>
  )
}
