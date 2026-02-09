import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

function getRangoMesActual() {
  const hoy = new Date()
  const año = hoy.getFullYear()
  const mes = hoy.getMonth()
  const desde = `${año}-${String(mes + 1).padStart(2, '0')}-01`
  const hasta = hoy.toISOString().slice(0, 10)
  return { desde, hasta }
}

export default function Devoluciones() {
  const rango = getRangoMesActual()
  const [fechaDesde, setFechaDesde] = useState(rango.desde)
  const [fechaHasta, setFechaHasta] = useState(rango.hasta)
  const [buscar, setBuscar] = useState('')
  const [tipoMotivo, setTipoMotivo] = useState('') // '' = todos, 'venta', 'orden'
  const [ordenPor, setOrdenPor] = useState('fecha')
  const [ordenDir, setOrdenDir] = useState('desc') // 'asc' | 'desc'
  const [devoluciones, setDevoluciones] = useState([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exportando, setExportando] = useState(false)

  const limit = 30

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = {}
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta
      if (buscar?.trim()) params.buscar = buscar.trim()
      if (tipoMotivo) params.tipo_motivo = tipoMotivo
      const res = await api.get('/exportaciones/devoluciones', { params, responseType: 'blob' })
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `devoluciones_${new Date().toISOString().slice(0, 10)}.xlsx`
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fn)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  const cargar = async (pag = 1) => {
    setLoading(true)
    setError('')
    try {
      const skip = (pag - 1) * limit
      const params = { skip, limit }
      if (fechaDesde) params.fecha_desde = fechaDesde + 'T00:00:00'
      if (fechaHasta) params.fecha_hasta = fechaHasta + 'T23:59:59'
      if (buscar?.trim()) params.buscar = buscar.trim()
      if (tipoMotivo) params.tipo_motivo = tipoMotivo
      params.orden_por = ordenPor
      params.direccion = ordenDir
      const res = await api.get('/devoluciones/', { params })
      const data = res.data
      setDevoluciones(data.devoluciones || [])
      setTotal(data.total ?? 0)
      setPagina(data.pagina ?? 1)
      setTotalPaginas(data.total_paginas ?? 1)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al cargar devoluciones')
      setDevoluciones([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar(1)
  }, [fechaDesde, fechaHasta, buscar, tipoMotivo, ordenPor, ordenDir])

  const toggleOrden = (col) => {
    if (ordenPor === col) {
      setOrdenDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setOrdenPor(col)
      setOrdenDir('desc')
    }
  }
  const ThSort = ({ col, label }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase cursor-pointer hover:bg-slate-100 select-none"
      onClick={() => toggleOrden(col)}
    >
      <span className="flex items-center gap-1">
        {label}
        {ordenPor === col && <span>{ordenDir === 'asc' ? '▲' : '▼'}</span>}
      </span>
    </th>
  )

  const formatearFecha = (s) => {
    if (!s) return '-'
    try {
      return new Date(s).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })
    } catch {
      return s
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Devoluciones</h1>
        <p className="text-sm text-slate-500 mt-1">
          Productos devueltos al inventario por cancelación de ventas u órdenes de trabajo
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fecha desde</label>
            <input
              type="date"
              value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fecha hasta</label>
            <input
              type="date"
              value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Buscar</label>
            <input
              type="text"
              value={buscar}
              onChange={(e) => setBuscar(e.target.value)}
              placeholder="Repuesto, referencia o motivo..."
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm w-56"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Tipo de motivo</label>
            <select
              value={tipoMotivo}
              onChange={(e) => setTipoMotivo(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="">Todos</option>
              <option value="venta">Devolución por venta</option>
              <option value="orden">Cancelación de orden</option>
            </select>
          </div>
          <button
            onClick={() => cargar(1)}
            disabled={loading}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm font-medium"
          >
            {loading ? 'Cargando...' : 'Actualizar'}
          </button>
          <button
            onClick={exportarExcel}
            disabled={exportando}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
          >
            📥 {exportando ? 'Exportando...' : 'Exportar a Excel'}
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {loading && devoluciones.length === 0 && (
        <p className="text-slate-500 py-8 text-center">Cargando devoluciones...</p>
      )}

      {!loading && !error && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {devoluciones.length === 0 ? (
            <p className="p-8 text-slate-500 text-center">
              No hay devoluciones en el rango de fechas seleccionado.
            </p>
          ) : (
            <>
              <p className="px-4 py-2 text-sm text-slate-600 bg-slate-50 border-b border-slate-200">
                Total: <strong>{total}</strong> devolución{total !== 1 ? 'es' : ''}
              </p>
              <div className="overflow-x-auto max-h-[calc(100vh-340px)] overflow-y-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50 sticky top-0 z-10">
                    <tr>
                      <ThSort col="fecha" label="Fecha" />
                      <ThSort col="repuesto" label="Repuesto" />
                      <th
                        className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase cursor-pointer hover:bg-slate-100 select-none"
                        onClick={() => toggleOrden('cantidad')}
                      >
                        <span className="flex items-center justify-end gap-1">
                          Cantidad
                          {ordenPor === 'cantidad' && <span>{ordenDir === 'asc' ? '▲' : '▼'}</span>}
                        </span>
                      </th>
                      <ThSort col="motivo" label="Motivo" />
                      <ThSort col="referencia" label="Referencia" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {devoluciones.map((m) => (
                      <tr key={m.id_movimiento} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 text-slate-600 whitespace-nowrap">
                          {formatearFecha(m.fecha_movimiento)}
                        </td>
                        <td className="px-4 py-2.5">
                          {m.repuesto ? (
                            <Link
                              to={`/inventario/kardex/${m.id_repuesto}`}
                              className="text-primary-600 hover:text-primary-700 font-medium"
                            >
                              {m.repuesto.nombre || m.repuesto.codigo || `#${m.id_repuesto}`}
                            </Link>
                          ) : (
                            `#${m.id_repuesto}`
                          )}
                          {m.repuesto?.codigo && (
                            <span className="text-slate-400 ml-1">({m.repuesto.codigo})</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-right font-medium">+{m.cantidad}</td>
                        <td className="px-4 py-2.5 text-slate-600 max-w-[280px] truncate" title={m.motivo}>
                          {m.motivo || '-'}
                        </td>
                        <td className="px-4 py-2.5 text-slate-600">
                          {m.id_venta ? (
                            <Link
                              to="/ventas"
                              className="text-primary-600 hover:text-primary-700 font-medium"
                              title="Ir a ventas"
                            >
                              Venta #{m.id_venta}
                            </Link>
                          ) : (
                            m.referencia || '—'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPaginas > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50">
                  <p className="text-xs text-slate-500">
                    Página {pagina} de {totalPaginas}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => cargar(pagina - 1)}
                      disabled={pagina <= 1 || loading}
                      className="px-3 py-1 text-sm border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50"
                    >
                      Anterior
                    </button>
                    <button
                      onClick={() => cargar(pagina + 1)}
                      disabled={pagina >= totalPaginas || loading}
                      className="px-3 py-1 text-sm border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50"
                    >
                      Siguiente
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
