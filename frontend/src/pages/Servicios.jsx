import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Servicios() {
  const [servicios, setServicios] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/servicios/').then((res) => {
      const d = res.data
      setServicios(Array.isArray(d) ? d : d?.servicios ?? [])
    }).catch(() => setServicios([]))
    .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Servicios</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Precio</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {servicios.length === 0 ? (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-500">No hay servicios</td></tr>
            ) : (
              servicios.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{s.codigo}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{s.nombre}</td>
                  <td className="px-4 py-3 text-sm text-right">${(Number(s.precio_base) || 0).toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
