import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Inventario() {
  const [repuestos, setRepuestos] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/repuestos/', { params: { limit: 200 } }).then((res) => {
      const d = res.data
      setRepuestos(Array.isArray(d) ? d : d?.repuestos ?? d?.items ?? [])
    }).catch(() => setRepuestos([]))
    setLoading(false)
  }, [])

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Inventario</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Precio venta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {repuestos.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-500">No hay repuestos</td></tr>
            ) : (
              repuestos.map((r) => (
                <tr key={r.id_repuesto} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{r.codigo}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{r.nombre}</td>
                  <td className="px-4 py-3 text-sm text-right">{r.stock_actual ?? 0}</td>
                  <td className="px-4 py-3 text-sm text-right">${(Number(r.precio_venta) || 0).toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
