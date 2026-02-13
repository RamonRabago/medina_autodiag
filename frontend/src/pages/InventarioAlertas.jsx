import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { formatearFechaHora } from '../utils/fechas'

const TIPO_LABEL = {
  STOCK_BAJO: 'Stock bajo',
  STOCK_CRITICO: 'Crítico',
  SIN_STOCK: 'Sin stock',
  SIN_MOVIMIENTO: 'Sin movimiento',
  SOBRE_STOCK: 'Sobre stock',
}

const TIPO_COLOR = {
  STOCK_BAJO: 'bg-amber-100 text-amber-800',
  STOCK_CRITICO: 'bg-red-100 text-red-800',
  SIN_STOCK: 'bg-red-200 text-red-900',
  SIN_MOVIMIENTO: 'bg-slate-100 text-slate-700',
  SOBRE_STOCK: 'bg-blue-100 text-blue-800',
}

export default function InventarioAlertas() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [alertas, setAlertas] = useState([])
  const [resumen, setResumen] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filtroTipo, setFiltroTipo] = useState('')
  const [incluirResueltas, setIncluirResueltas] = useState(false)
  const [resolviendo, setResolviendo] = useState(null)

  const puedeResolver = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  const cargar = () => {
    setLoading(true)
    const params = { activas_solo: !incluirResueltas }
    if (filtroTipo) params.tipo_alerta = filtroTipo
    Promise.all([
      api.get('/inventario/alertas', { params }),
      api.get('/inventario/alertas/resumen'),
    ])
      .then(([resAlertas, resResumen]) => {
        setAlertas(resAlertas.data ?? [])
        setResumen(resResumen.data ?? null)
      })
      .catch(() => {
        setAlertas([])
        setResumen(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => cargar(), [filtroTipo, incluirResueltas])

  const resolverAlerta = async (idAlerta) => {
    if (!puedeResolver) return
    setResolviendo(idAlerta)
    try {
      await api.post(`/inventario/alertas/${idAlerta}/resolver`)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al resolver alerta')
    } finally {
      setResolviendo(null)
    }
  }

  return (
    <div>
      <Link
        to="/inventario"
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-100 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-200 hover:border-slate-400 transition-colors shadow-sm mb-6"
      >
        ← Volver a Inventario
      </Link>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Alertas de inventario</h1>

      {resumen && (
        <div className="flex flex-wrap gap-3 mb-6">
          <span className="px-3 py-1.5 bg-slate-100 rounded-lg text-sm">
            <strong>Total:</strong> {resumen.total_alertas}
          </span>
          {resumen.alertas_criticas > 0 && (
            <span className="px-3 py-1.5 bg-red-100 text-red-800 rounded-lg text-sm">Críticas: {resumen.alertas_criticas}</span>
          )}
          {resumen.alertas_sin_stock > 0 && (
            <span className="px-3 py-1.5 bg-red-200 text-red-900 rounded-lg text-sm">Sin stock: {resumen.alertas_sin_stock}</span>
          )}
          {resumen.alertas_stock_bajo > 0 && (
            <span className="px-3 py-1.5 bg-amber-100 text-amber-800 rounded-lg text-sm">Stock bajo: {resumen.alertas_stock_bajo}</span>
          )}
          {resumen.alertas_sobre_stock > 0 && (
            <span className="px-3 py-1.5 bg-blue-100 text-blue-800 rounded-lg text-sm">Sobre stock: {resumen.alertas_sobre_stock}</span>
          )}
          {resumen.alertas_sin_movimiento > 0 && (
            <span className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-sm">Sin movimiento: {resumen.alertas_sin_movimiento}</span>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={filtroTipo}
          onChange={(e) => setFiltroTipo(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Todos los tipos</option>
          {Object.entries(TIPO_LABEL).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={incluirResueltas}
            onChange={(e) => setIncluirResueltas(e.target.checked)}
          />
          Incluir resueltas
        </label>
      </div>

      {loading ? (
        <p className="text-slate-500">Cargando...</p>
      ) : alertas.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-slate-500">
          No hay alertas {incluirResueltas ? '' : 'activas'}.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-slate-600">Tipo</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-slate-600">Repuesto</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-slate-600">Mensaje</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-slate-600">Stock</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-slate-600">Fecha</th>
                {puedeResolver && <th className="text-right px-4 py-3 text-sm font-medium text-slate-600">Acción</th>}
              </tr>
            </thead>
            <tbody>
              {alertas.map((a) => (
                <tr key={a.id_alerta} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${TIPO_COLOR[a.tipo_alerta] || 'bg-slate-100'}`}>
                      {TIPO_LABEL[a.tipo_alerta] ?? a.tipo_alerta}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {a.repuesto ? (
                      <Link
                        to={`/inventario/editar/${a.id_repuesto}`}
                        className="text-primary-600 hover:underline"
                      >
                        {a.repuesto.codigo} - {a.repuesto.nombre}
                      </Link>
                    ) : (
                      <span className="text-slate-400">ID {a.id_repuesto}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">{a.mensaje}</td>
                  <td className="px-4 py-3 text-sm">
                    {a.stock_actual != null && (
                      <span className={a.stock_actual === 0 ? 'text-red-600 font-medium' : ''}>
                        {a.stock_actual} {a.stock_minimo != null && `(mín: ${a.stock_minimo})`}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {formatearFechaHora(a.fecha_creacion)}
                  </td>
                  {puedeResolver && (
                    <td className="px-4 py-3 text-right">
                      {a.activa ? (
                        <button
                          type="button"
                          onClick={() => resolverAlerta(a.id_alerta)}
                          disabled={resolviendo === a.id_alerta}
                          className="text-sm px-2 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200 disabled:opacity-50"
                        >
                          {resolviendo === a.id_alerta ? '...' : 'Resolver'}
                        </button>
                      ) : (
                        <span className="text-slate-400 text-xs">Resuelta</span>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
