import { useState, useEffect } from 'react'
import api from '../services/api'

export default function Auditoria() {
  const [registros, setRegistros] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/auditoria/').then((res) => {
      const d = res.data
      setRegistros(Array.isArray(d) ? d : d?.registros ?? d?.items ?? [])
    }).catch(() => setRegistros([]))
    setLoading(false)
  }, [])

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Auditoría</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Usuario</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Módulo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Acción</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Detalle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {registros.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">No hay registros de auditoría o el endpoint no está configurado.</td></tr>
            ) : (
              registros.map((r, i) => (
                <tr key={r.id_auditoria ?? i} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-600">{r.fecha ? new Date(r.fecha).toLocaleString() : '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{r.usuario_email ?? r.email ?? '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{r.modulo ?? '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{r.accion ?? '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{r.descripcion ?? r.id_referencia ?? '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
