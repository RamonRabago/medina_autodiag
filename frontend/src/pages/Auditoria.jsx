import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { fechaAStr, formatearFechaHora } from '../utils/fechas'

function enlaceReferencia(modulo, idRef, descripcion) {
  if (idRef == null || idRef === '') return null
  const id = idRef
  const mod = (modulo || '').toUpperCase()
  if (mod === 'ORDEN_COMPRA' && id) return { to: `/ordenes-compra/editar/${id}`, label: `Ver orden #${id}` }
  if (mod === 'ORDEN_TRABAJO' && id) return { to: `/ordenes-trabajo/${id}`, label: `Ver orden trabajo #${id}` }
  if (mod === 'CUENTA_PAGAR_MANUAL' && id) return { to: '/cuentas-por-pagar?tab=manuales', label: `Cuenta manual #${id}` }
  if (mod === 'VENTA' && id) return { to: '/ventas', label: `Venta #${id}` }
  if (mod === 'GASTO' && id) return { to: '/gastos', label: `Gasto #${id}` }
  if (mod === 'CAJA_TURNO' && id) return { to: '/caja', label: `Turno #${id}` }
  if (mod === 'USUARIO' && id) return { to: '/configuracion', label: `Usuario #${id}` }
  if (mod === 'PAGO_ORDEN_COMPRA' && id) return { to: '/cuentas-por-pagar', label: `Pago #${id}` }
  return null
}

function getRangoMesActual() {
  const hoy = new Date()
  const año = hoy.getFullYear()
  const mes = hoy.getMonth()
  const desde = `${año}-${String(mes + 1).padStart(2, '0')}-01`
  const hasta = fechaAStr(hoy)
  return { desde, hasta }
}

export default function Auditoria() {
  const rango = getRangoMesActual()
  const [registros, setRegistros] = useState([])
  const [loading, setLoading] = useState(true)
  const [usuarios, setUsuarios] = useState([])
  const [filtros, setFiltros] = useState({ fecha_desde: rango.desde, fecha_hasta: rango.hasta, modulo: '', id_usuario: '' })
  const [pagina, setPagina] = useState(1)
  const [limit, setLimit] = useState(50)
  const [total, setTotal] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)

  const [error, setError] = useState(null)
  const [exportando, setExportando] = useState(false)

  const cargar = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { skip: (pagina - 1) * limit, limit }
      if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
      if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
      if (filtros.modulo) params.modulo = filtros.modulo
      if (filtros.id_usuario) params.id_usuario = filtros.id_usuario
      const res = await api.get('/auditoria', { params })
      const d = res.data
      setRegistros(Array.isArray(d) ? d : d?.registros ?? d?.items ?? [])
      setTotal(d?.total ?? 0)
      setTotalPaginas(d?.total_paginas ?? 1)
    } catch (err) {
      setRegistros([])
      const status = err.response?.status
      const detail = err.response?.data?.detail
      if (status === 403) setError('No tienes permiso para ver la auditoría.')
      else if (status === 401) setError('Sesión expirada. Inicia sesión de nuevo.')
      else setError(detail || 'No se pudo cargar la auditoría. Verifica que el endpoint esté configurado.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [filtros.fecha_desde, filtros.fecha_hasta, filtros.modulo, filtros.id_usuario, pagina, limit])

  useEffect(() => {
    api.get('/usuarios/').then((r) => {
      const data = r.data?.usuarios ?? r.data ?? []
      setUsuarios(Array.isArray(data) ? data : [])
    }).catch(() => setUsuarios([]))
  }, [])

  if (loading && registros.length === 0) return <p className="text-slate-500">Cargando...</p>

  return (
    <div className="min-w-0">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Auditoría</h1>
      <p className="text-sm text-slate-600 mb-4">Registro de acciones realizadas por usuarios (órdenes de compra, pagos, cuentas manuales, etc.).</p>

      {error && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
          {error}
        </div>
      )}

      <div className="mb-4 sm:mb-6 flex flex-wrap gap-3 sm:gap-4 items-end">
        <div className="flex flex-col gap-1 min-w-[120px] sm:min-w-0">
          <label className="text-xs text-slate-500">Desde</label>
          <input type="date" value={filtros.fecha_desde} onChange={(e) => setFiltros((f) => ({ ...f, fecha_desde: e.target.value }))} className="px-3 py-2.5 min-h-[44px] border border-slate-300 rounded-lg text-sm touch-manipulation w-full" />
        </div>
        <div className="flex flex-col gap-1 min-w-[120px] sm:min-w-0">
          <label className="text-xs text-slate-500">Hasta</label>
          <input type="date" value={filtros.fecha_hasta} onChange={(e) => setFiltros((f) => ({ ...f, fecha_hasta: e.target.value }))} className="px-3 py-2.5 min-h-[44px] border border-slate-300 rounded-lg text-sm touch-manipulation w-full" />
        </div>
        <div className="flex flex-col gap-1 flex-1 min-w-[140px] sm:max-w-[180px]">
          <label className="text-xs text-slate-500">Módulo</label>
          <input type="text" value={filtros.modulo} onChange={(e) => setFiltros((f) => ({ ...f, modulo: e.target.value }))} placeholder="ORDEN_COMPRA, VENTA, GASTO..." className="px-3 py-2.5 min-h-[44px] border border-slate-300 rounded-lg text-sm w-full touch-manipulation" />
        </div>
        <div className="flex flex-col gap-1 min-w-[140px] sm:min-w-[160px]">
          <label className="text-xs text-slate-500">Usuario</label>
          <select value={filtros.id_usuario} onChange={(e) => setFiltros((f) => ({ ...f, id_usuario: e.target.value }))} className="px-3 py-2.5 min-h-[44px] border border-slate-300 rounded-lg text-sm w-full touch-manipulation">
            <option value="">Todos</option>
            {usuarios.map((u) => (
              <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1 min-w-[100px]">
          <label className="text-xs text-slate-500">Por página</label>
          <select value={limit} onChange={(e) => { setLimit(Number(e.target.value)); setPagina(1) }} className="px-3 py-2.5 min-h-[44px] border border-slate-300 rounded-lg text-sm w-full touch-manipulation">
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <button onClick={cargar} disabled={loading} className="flex-1 sm:flex-none min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-60 touch-manipulation">
            {loading ? 'Cargando...' : 'Actualizar'}
          </button>
          <button
          onClick={async () => {
            if (exportando) return
            setExportando(true)
            try {
              const params = {}
              if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
              if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
              if (filtros.modulo) params.modulo = filtros.modulo
              if (filtros.id_usuario) params.id_usuario = filtros.id_usuario
              const res = await api.get('/exportaciones/auditoria', { params, responseType: 'blob' })
              const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || 'auditoria.xlsx'
              const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
              const link = document.createElement('a')
              link.href = window.URL.createObjectURL(blob)
              link.download = fn
              link.click()
              window.URL.revokeObjectURL(link.href)
            } catch (err) {
              alert(err.response?.data?.detail || 'Error al exportar')
            } finally {
              setExportando(false)
            }
          }}
          disabled={exportando}
          className="flex-1 sm:flex-none min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed touch-manipulation"
        >
          {exportando ? 'Exportando...' : 'Exportar'}
        </button>
        </div>
      </div>

      {total > 0 && (
        <div className="mb-2 text-sm text-slate-600">
          Mostrando {(pagina - 1) * limit + 1}–{Math.min(pagina * limit, total)} de {total} registros
        </div>
      )}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
              <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Usuario</th>
              <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Módulo</th>
              <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Acción</th>
              <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Detalle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {registros.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">{error ? '' : 'No hay registros de auditoría. Se registran al crear órdenes de compra, pagar, crear cuentas manuales, etc.'}</td></tr>
            ) : (
              registros.map((r, i) => (
                <tr key={r.id_auditoria ?? i} className="hover:bg-slate-50">
                  <td className="px-2 sm:px-4 py-3 text-sm text-slate-600 whitespace-nowrap">{formatearFechaHora(r.fecha)}</td>
                  <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{r.usuario_nombre ?? r.usuario_email ?? r.email ?? '-'}</td>
                  <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{r.modulo ?? '-'}</td>
                  <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{r.accion ?? '-'}</td>
                  <td className="px-2 sm:px-4 py-3 text-sm text-slate-600 min-w-[120px]">
                    {(() => {
                      const enlace = enlaceReferencia(r.modulo, r.id_referencia, r.descripcion)
                      if (enlace) {
                        return (
                          <span className="flex flex-wrap items-center gap-2">
                            <Link to={enlace.to} className="text-primary-600 hover:text-primary-700 hover:underline">
                              {enlace.label}
                            </Link>
                            {r.descripcion && <span className="text-slate-500">· {String(r.descripcion).slice(0, 80)}{String(r.descripcion).length > 80 ? '…' : ''}</span>}
                          </span>
                        )
                      }
                      return r.descripcion ?? (r.id_referencia != null ? `#${r.id_referencia}` : '-')
                    })()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {totalPaginas > 1 && (
        <div className="mt-4 flex flex-wrap items-center justify-center sm:justify-start gap-2">
          <button
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={pagina <= 1 || loading}
            className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 touch-manipulation"
          >
            Anterior
          </button>
          <span className="text-sm text-slate-600 py-2">
            Página {pagina} de {totalPaginas}
          </span>
          <button
            onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
            disabled={pagina >= totalPaginas || loading}
            className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 touch-manipulation"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  )
}
