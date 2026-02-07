import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../services/api'

export default function Kardex() {
  const { id } = useParams()
  const [repuesto, setRepuesto] = useState(null)
  const [movimientos, setMovimientos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) {
      setError('ID de repuesto no especificado')
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    Promise.all([
      api.get(`/repuestos/${id}`),
      api.get(`/inventario/movimientos/repuesto/${id}`, { params: { limite: 200 } }),
    ])
      .then(([r1, r2]) => {
        setRepuesto(r1.data)
        setMovimientos(Array.isArray(r2.data) ? r2.data : [])
      })
      .catch((err) => {
        const d = err.response?.data?.detail
        const msg = typeof d === 'string' ? d : (Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : 'Error al cargar el kardex')
        setError(msg)
        setRepuesto(null)
        setMovimientos([])
      })
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="p-8">
        <p className="text-slate-500">Cargando kardex...</p>
      </div>
    )
  }

  if (error || !repuesto) {
    return (
      <div className="max-w-3xl mx-auto p-8">
        <p className="text-red-600 mb-4">{error || 'Repuesto no encontrado'}</p>
        <Link to="/inventario" className="text-primary-600 hover:underline">← Volver a inventario</Link>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <Link to="/inventario" className="text-slate-600 hover:text-slate-800 font-medium">
            ← Volver a inventario
          </Link>
          <h1 className="text-2xl font-bold text-slate-800">
            Kardex – {repuesto.nombre} ({repuesto.codigo})
          </h1>
        </div>
      </div>

      <p className="text-sm text-slate-600 mb-4">
        Historial de movimientos. Stock actual: <strong>{repuesto.stock_actual ?? 0}</strong> unidades.
      </p>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {movimientos.length === 0 ? (
          <p className="p-8 text-slate-500 text-center">No hay movimientos registrados.</p>
        ) : (
          <div className="overflow-x-auto max-h-[calc(100vh-260px)] overflow-y-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Tipo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Cant.</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock ant.</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock nuevo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Costo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Referencia / Motivo</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Comprobante</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {movimientos.map((m) => (
                  <tr key={m.id_movimiento} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-slate-600 whitespace-nowrap">
                      {m.fecha_movimiento ? new Date(m.fecha_movimiento).toLocaleString('es-MX') : '-'}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${m.tipo_movimiento === 'ENTRADA' || m.tipo_movimiento === 'AJUSTE+' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {m.tipo_movimiento}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium">{m.cantidad}</td>
                    <td className="px-4 py-2.5 text-right text-slate-600">{m.stock_anterior ?? '-'}</td>
                    <td className="px-4 py-2.5 text-right font-medium">{m.stock_nuevo ?? '-'}</td>
                    <td className="px-4 py-2.5 text-right">${(Number(m.costo_total) || 0).toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-slate-600 max-w-[200px] truncate" title={[m.referencia, m.motivo].filter(Boolean).join(' – ')}>
                      {m.referencia || m.motivo || '-'}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {m.imagen_comprobante_url ? (
                        <div className="flex items-center justify-center gap-2">
                          <a
                            href={m.imagen_comprobante_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                            title="Ver comprobante"
                          >
                            {(m.imagen_comprobante_url || '').toLowerCase().endsWith('.pdf') ? '📄 Ver' : '🖼 Ver'}
                          </a>
                          <span className="text-slate-300">|</span>
                          <a
                            href={m.imagen_comprobante_url}
                            download
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                            title="Descargar comprobante"
                          >
                            ⬇ Descargar
                          </a>
                        </div>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
