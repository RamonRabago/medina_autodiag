import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { fechaAStr, formatearFechaHora } from '../utils/fechas'

function getRangoMesActual() {
  const hoy = new Date()
  const año = hoy.getFullYear()
  const mes = hoy.getMonth()
  const desde = `${año}-${String(mes + 1).padStart(2, '0')}-01`
  const hasta = fechaAStr(hoy)
  return { desde, hasta }
}

export default function VentasIngresos() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [fechaDesde, setFechaDesde] = useState(searchParams.get('desde') || getRangoMesActual().desde)
  const [fechaHasta, setFechaHasta] = useState(searchParams.get('hasta') || getRangoMesActual().hasta)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const cargar = async () => {
    if (!fechaDesde || !fechaHasta) {
      setError('Selecciona fecha desde y hasta')
      return
    }
    if (fechaDesde > fechaHasta) {
      setError('La fecha desde no puede ser mayor que la fecha hasta')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/ventas/reportes/ingresos-detalle', {
        params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta }
      })
      setData(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al cargar ingresos')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (fechaDesde && fechaHasta && fechaDesde <= fechaHasta) {
      cargar()
    } else {
      setData(null)
      setLoading(false)
    }
  }, [fechaDesde, fechaHasta])

  const formatearFecha = (s) => formatearFechaHora(s)

  const puedeVer = user?.rol === 'ADMIN' || user?.rol === 'CAJA' || user?.rol === 'EMPLEADO'
  if (!puedeVer) {
    return (
      <div className="p-6">
        <p className="text-red-600">No tienes permiso para ver esta página.</p>
        <Link to="/" className="text-primary-600 hover:underline mt-2 inline-block">Ir al Dashboard</Link>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Detalle de ingresos</h1>
          <p className="text-sm text-slate-500 mt-1">Pagos recibidos por periodo de fechas</p>
        </div>
        <Link to="/" className="text-slate-600 hover:text-slate-800 text-sm flex items-center gap-1 min-h-[44px] items-center touch-manipulation">
          ← Volver al Dashboard
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-3 sm:gap-4 items-end">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fecha desde</label>
            <input
              type="date"
              value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)}
              className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fecha hasta</label>
            <input
              type="date"
              value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)}
              className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation"
            />
          </div>
          <button
            type="button"
            onClick={cargar}
            disabled={loading || !fechaDesde || !fechaHasta}
            className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 text-sm font-medium touch-manipulation"
          >
            {loading ? 'Cargando...' : 'Actualizar'}
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {loading && !data && (
        <p className="text-slate-500 py-8 text-center">Cargando ingresos...</p>
      )}

      {!loading && data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4 sm:p-5">
              <p className="text-xs text-slate-500 uppercase font-medium">Total ingresos</p>
              <p className="text-2xl font-bold text-green-700 mt-1">
                ${(data.total ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
              </p>
              <p className="text-xs text-slate-400 mt-1">{data.fecha_desde} a {data.fecha_hasta}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 sm:p-5">
              <p className="text-xs text-slate-500 uppercase font-medium">Cantidad de pagos</p>
              <p className="text-2xl font-bold text-slate-800 mt-1">{data.cantidad_pagos ?? 0}</p>
            </div>
            {data.resumen_por_metodo && Object.entries(data.resumen_por_metodo).map(([metodo, monto]) => (
              <div key={metodo} className="bg-white rounded-lg shadow p-4 sm:p-5">
                <p className="text-xs text-slate-500 uppercase font-medium">{metodo}</p>
                <p className="text-xl font-bold text-slate-800 mt-1">
                  ${Number(monto).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                </p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
            <div className="p-4 border-b border-slate-200">
              <h2 className="text-lg font-semibold text-slate-800">Detalle de pagos</h2>
              <p className="text-sm text-slate-500">Cada fila es un pago registrado</p>
            </div>
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto min-w-[640px]">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Venta</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Cliente</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Total venta</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Monto pagado</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Método</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Referencia</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(data.pagos ?? []).length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                        No hay pagos en el periodo seleccionado
                      </td>
                    </tr>
                  ) : (
                    (data.pagos ?? []).map((p) => (
                      <tr key={p.id_pago} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-700 whitespace-nowrap">{formatearFecha(p.fecha)}</td>
                        <td className="px-4 py-3 text-sm">
                          <Link
                            to={`/ventas?id=${p.id_venta}`}
                            className="text-primary-600 hover:text-primary-700 hover:underline font-medium"
                          >
                            #{p.id_venta}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700">{p.nombre_cliente || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-700 text-right">
                          ${(p.total_venta ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3 text-sm font-semibold text-green-700 text-right">
                          ${(p.monto ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                            {p.metodo || '-'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">{p.referencia || '-'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
