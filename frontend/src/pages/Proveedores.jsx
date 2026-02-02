import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Proveedores() {
  const [proveedores, setProveedores] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/proveedores/').then((res) => {
      const d = res.data
      setProveedores(Array.isArray(d) ? d : d?.proveedores ?? d?.items ?? [])
    }).catch(() => setProveedores([]))
    setLoading(false)
  }, [])

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Proveedores</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Teléfono</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {proveedores.length === 0 ? (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-slate-500">No hay proveedores</td></tr>
            ) : (
              proveedores.map((p) => (
                <tr key={p.id_proveedor} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{p.nombre}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.telefono || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.email || '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
