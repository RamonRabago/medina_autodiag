import { useState, useEffect, useCallback } from 'react'
import { hoyStr, formatearFechaHora, fechaAStr } from '../utils/fechas'
import { aNumero, esNumeroValido } from '../utils/numeros'
import api from '../services/api'
import Modal from '../components/Modal'
import PageHeader, { IconDownload, btnExport } from '../components/PageHeader'
import { useAuth } from '../context/AuthContext'
import { normalizeDetail, showError } from '../utils/toast'

export default function Caja() {
  const { user } = useAuth()
  const [turno, setTurno] = useState(null)
  const [corte, setCorte] = useState(null)
  const [alertas, setAlertas] = useState([])
  const [historico, setHistorico] = useState([])
  const [turnosAbiertos, setTurnosAbiertos] = useState([])
  const [modalCerrarForzado, setModalCerrarForzado] = useState(false)
  const [turnoForzado, setTurnoForzado] = useState(null)
  const [montoCierreForzado, setMontoCierreForzado] = useState('')
  const [motivoForzado, setMotivoForzado] = useState('')
  const [loading, setLoading] = useState(true)
  const [modalAbrir, setModalAbrir] = useState(false)
  const [modalCerrar, setModalCerrar] = useState(false)
  const [montoApertura, setMontoApertura] = useState('')
  const [montoCierre, setMontoCierre] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [modalDetalle, setModalDetalle] = useState(false)
  const [idTurnoDetalle, setIdTurnoDetalle] = useState(null)
  const [detalleTurno, setDetalleTurno] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [exportando, setExportando] = useState(false)
  const [fechaExpDesde, setFechaExpDesde] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    return fechaAStr(d)
  })
  const [fechaExpHasta, setFechaExpHasta] = useState(() => hoyStr())
  const [errorCarga, setErrorCarga] = useState(null)

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = {}
      if (fechaExpDesde) params.fecha_desde = fechaExpDesde
      if (fechaExpHasta) params.fecha_hasta = fechaExpHasta
      const res = await api.get('/exportaciones/caja', { params, responseType: 'blob' })
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `turnos_caja_${hoyStr()}.xlsx`
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fn)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      showError(err, 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  const cargar = useCallback(() => {
    setLoading(true)
    setErrorCarga(null)
    const paramsHist = {}
    if (fechaExpDesde) paramsHist.fecha_desde = fechaExpDesde
    if (fechaExpHasta) paramsHist.fecha_hasta = fechaExpHasta
    const promTurno = api.get('/caja/turno-actual')
      .then((res) => {
        setTurno(res.data)
        if (res.data?.estado === 'ABIERTO') {
          return Promise.all([
            api.get('/caja/corte-diario').then((r) => setCorte(r.data)).catch((err) => { showError(err, 'Error al cargar corte'); setCorte(null) }),
            api.get('/caja/alertas').then((r) => setAlertas(Array.isArray(r.data) ? r.data : [])).catch((err) => { showError(err, 'Error al cargar alertas'); setAlertas([]) }),
          ])
        }
        setCorte(null)
        setAlertas([])
      })
      .catch((err) => { showError(err, 'Error al cargar turno actual'); setTurno(null); setCorte(null); setAlertas([]); setErrorCarga(true) })
    const promHist = api.get('/caja/historico-turnos', { params: paramsHist })
      .then((r) => setHistorico(Array.isArray(r.data) ? r.data : []))
      .catch((err) => { showError(err, 'Error al cargar histórico'); setHistorico([]) })
    const promAbiertos = user?.rol === 'ADMIN'
      ? api.get('/caja/turnos-abiertos').then((r) => setTurnosAbiertos(Array.isArray(r.data) ? r.data : [])).catch((err) => { showError(err, 'Error al cargar turnos abiertos'); setTurnosAbiertos([]) })
      : Promise.resolve(setTurnosAbiertos([]))
    Promise.allSettled([promTurno, promHist, promAbiertos]).finally(() => setLoading(false))
  }, [user?.rol, fechaExpDesde, fechaExpHasta])

  useEffect(() => { cargar() }, [cargar])

  const efectivoIngresos = corte?.totales_por_metodo?.find((m) => m.metodo === 'EFECTIVO')?.total ?? 0
  const efectivoEsperado = turno?.estado === 'ABIERTO' && corte
    ? (Number(turno.monto_apertura) || 0) + efectivoIngresos - (corte.total_pagos_proveedores || 0) - (corte.total_gastos || 0)
    : null

  const abrirTurno = async (e) => {
    e.preventDefault()
    setError('')
    if (!esNumeroValido(montoApertura) || aNumero(montoApertura) < 0) {
      setError('Monto de apertura debe ser un número mayor o igual a 0')
      return
    }
    setGuardando(true)
    try {
      await api.post('/caja/abrir', { monto_apertura: aNumero(montoApertura) })
      cargar()
      setModalAbrir(false)
      setMontoApertura('')
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al abrir turno')
    } finally {
      setGuardando(false)
    }
  }

  const cerrarTurno = async (e) => {
    e.preventDefault()
    setError('')
    if (!esNumeroValido(montoCierre) || aNumero(montoCierre) < 0) {
      setError('Monto de cierre debe ser un número mayor o igual a 0')
      return
    }
    setGuardando(true)
    try {
      await api.post('/caja/cerrar', { monto_cierre: aNumero(montoCierre) })
      cargar()
      setModalCerrar(false)
      setMontoCierre('')
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al cerrar turno')
    } finally {
      setGuardando(false)
    }
  }

  const abrirModalCerrarForzado = (t) => {
    setTurnoForzado(t)
    setMontoCierreForzado('')
    setMotivoForzado('')
    setError('')
    setModalCerrarForzado(true)
  }

  const cargarDetalleTurno = useCallback((idTurno) => {
    if (!idTurno) return
    setCargandoDetalle(true)
    api.get(`/caja/turno/${idTurno}`)
      .then((r) => setDetalleTurno(r.data))
      .catch((err) => { showError(err, 'Error al cargar detalle del turno'); setDetalleTurno(null) })
      .finally(() => setCargandoDetalle(false))
  }, [])

  const abrirDetalleTurno = (idTurno) => {
    setIdTurnoDetalle(idTurno)
    setDetalleTurno(null)
    setModalDetalle(true)
    cargarDetalleTurno(idTurno)
  }

  const cerrarForzado = async (e) => {
    e.preventDefault()
    if (!turnoForzado) return
    setError('')
    if (!esNumeroValido(montoCierreForzado) || aNumero(montoCierreForzado) < 0) {
      setError('Monto de cierre debe ser un número mayor o igual a 0')
      return
    }
    setGuardando(true)
    try {
      await api.post(`/caja/cerrar-forzado/${turnoForzado.id_turno}`, null, {
        params: { monto_cierre: aNumero(montoCierreForzado), motivo: motivoForzado.trim() || undefined }
      })
      cargar()
      setModalCerrarForzado(false)
      setTurnoForzado(null)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al cerrar turno')
    } finally {
      setGuardando(false)
    }
  }

  if (loading && !turno && !historico.length) {
    return (
      <div className="min-h-0 flex flex-col">
        <PageHeader title="Caja" className="mb-6" />
        <div className="space-y-6 animate-pulse">
          <div className="bg-white rounded-lg shadow p-6 max-w-md">
            <div className="h-5 bg-slate-200 rounded w-24 mb-4" />
            <div className="h-4 bg-slate-200 rounded w-full mb-2" />
            <div className="h-4 bg-slate-200 rounded w-2/3" />
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="h-5 bg-slate-200 rounded w-32 mb-4" />
            <div className="h-10 bg-slate-200 rounded w-full" />
          </div>
        </div>
      </div>
    )
  }

  if (errorCarga && !turno) {
    return (
      <div className="min-h-0 flex flex-col">
        <PageHeader title="Caja" className="mb-6" />
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <p className="text-red-700 mb-4">No se pudo cargar la información de caja. Revisa tu conexión e intenta de nuevo.</p>
          <button type="button" onClick={cargar} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Reintentar</button>
        </div>
      </div>
    )
  }

  const nivelClass = (n) => (n === 'CRITICO' ? 'bg-red-50 border-red-200 text-red-800' : n === 'WARNING' ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-slate-50 border-slate-200 text-slate-700')

  return (
    <div className="min-h-0 flex flex-col">
      <PageHeader title="Caja" className="mb-6">
        <button
          type="button"
          onClick={cargar}
          disabled={loading}
          className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
          title="Actualizar"
        >
          {loading ? 'Actualizando...' : 'Actualizar'}
        </button>
      </PageHeader>
      {alertas.length > 0 && (
        <div className="mb-4 space-y-2">
          {alertas.map((a) => (
            <div key={a.id_alerta} className={`p-3 rounded-lg border ${nivelClass(typeof a.nivel === 'string' ? a.nivel : a.nivel?.value ?? '')}`}>
              <p className="text-sm font-medium">{a.mensaje}</p>
              {a.tipo && <p className="text-xs opacity-75 mt-0.5">{a.tipo}</p>}
            </div>
          ))}
        </div>
      )}
      <div className="bg-white rounded-lg shadow p-6 max-w-md">
        <h3 className="font-semibold text-slate-700 mb-2">Turno actual</h3>
        {turno && turno.estado === 'ABIERTO' ? (
          <div>
            <p className="text-green-600 font-medium">Turno abierto</p>
            <p className="text-sm text-slate-500 mt-1">Apertura: {formatearFechaHora(turno.fecha_apertura)}</p>
            <p className="text-sm text-slate-500">Monto apertura: ${(Number(turno.monto_apertura) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
            {corte && (
              <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-xs font-medium text-slate-500 uppercase mb-2">Efectivo esperado en caja</p>
                <p className="text-lg font-bold text-slate-800">
                  ${(efectivoEsperado ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Apertura + efectivo cobrado − pagos proveedores − gastos
                </p>
                {corte.totales_por_metodo?.length > 0 && (
                  <p className="text-xs text-slate-500 mt-1">
                    Cobros: {corte.totales_por_metodo.map((m) => `${m.metodo}: $${Number(m.total).toFixed(2)}`).join(' · ')}
                  </p>
                )}
              </div>
            )}
            <button type="button" onClick={() => { setModalCerrar(true); setError('') }} className="mt-4 min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 touch-manipulation">Cerrar turno</button>
          </div>
        ) : (
          <div>
            <p className="text-slate-600">No hay turno abierto</p>
            <button type="button" onClick={() => { setModalAbrir(true); setError('') }} className="mt-4 min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 touch-manipulation">Abrir turno</button>
          </div>
        )}
      </div>

      {user?.rol === 'ADMIN' && turnosAbiertos.length > 0 && (
        <div className="mt-8 bg-amber-50 border border-amber-200 rounded-lg overflow-hidden max-w-3xl">
          <h3 className="font-semibold text-amber-900 p-4 border-b border-amber-200">Cierre forzado (ADMIN)</h3>
          <p className="px-4 py-2 text-sm text-amber-800">Turnos abiertos de otros usuarios. Puedes cerrarlos forzadamente.</p>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-amber-200 text-sm">
              <thead className="bg-amber-100/50">
                <tr>
                  <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-amber-800 uppercase">Usuario</th>
                  <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-amber-800 uppercase">Apertura</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-amber-800 uppercase">Monto</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-amber-800 uppercase">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-100">
                {turnosAbiertos.map((t) => (
                  <tr key={t.id_turno} className="hover:bg-amber-50/50">
                    <td className="px-2 sm:px-4 py-3 text-amber-900 font-medium">{t.usuario_nombre || `#${t.id_usuario}`}</td>
                    <td className="px-2 sm:px-4 py-3 text-amber-800">{formatearFechaHora(t.fecha_apertura)}</td>
                    <td className="px-2 sm:px-4 py-3 text-right text-amber-800">${(Number(t.monto_apertura) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                    <td className="px-2 sm:px-4 py-3 text-right">
                      <button type="button" onClick={() => abrirModalCerrarForzado(t)} className="min-h-[44px] px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 touch-manipulation">
                        Cerrar forzado
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-8 bg-white rounded-lg shadow overflow-hidden max-w-4xl">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row flex-wrap items-stretch sm:items-end gap-3 justify-between">
          <h3 className="font-semibold text-slate-700">Histórico de turnos</h3>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Desde</label>
              <input type="date" value={fechaExpDesde} onChange={(e) => setFechaExpDesde(e.target.value)} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Hasta</label>
              <input type="date" value={fechaExpHasta} onChange={(e) => setFechaExpHasta(e.target.value)} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <button type="button" onClick={exportarExcel} disabled={exportando} className={btnExport}>
              <IconDownload />
              {exportando ? 'Exportando...' : 'Exportar'}
            </button>
          </div>
        </div>
        {historico.length === 0 ? (
          <p className="p-4 text-slate-500 text-sm">No hay turnos cerrados</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
                  <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Usuario</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Apertura</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Cierre</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Diferencia</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {historico.map((t) => {
                  const diff = t.diferencia != null ? Number(t.diferencia) : null
                  const diffClass = diff == null ? 'text-slate-400' : Math.abs(diff) < 0.01 ? 'text-green-600 font-medium' : diff < 0 ? 'text-red-600 font-medium' : 'text-green-600'
                  const diffLabel = diff == null ? '-' : diff < 0 ? `Queda a deber $${Math.abs(diff).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : diff > 0.01 ? `Sobra $${diff.toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : 'Cuadra'
                  return (
                    <tr key={t.id_turno} className="hover:bg-slate-50">
                      <td className="px-2 sm:px-4 py-3 text-slate-700">{formatearFechaHora(t.fecha_cierre)}</td>
                      <td className="px-2 sm:px-4 py-3 text-slate-700">{t.usuario_nombre || `#${t.id_usuario}`}</td>
                      <td className="px-2 sm:px-4 py-3 text-right text-slate-700">${(Number(t.monto_apertura) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                      <td className="px-2 sm:px-4 py-3 text-right text-slate-700 font-medium">${(Number(t.monto_cierre) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                      <td className={`px-2 sm:px-4 py-3 text-right ${diffClass}`}>{diffLabel}</td>
                      <td className="px-2 sm:px-4 py-3 text-right">
                        <button type="button" onClick={() => abrirDetalleTurno(t.id_turno)} className="min-h-[36px] px-2 py-1.5 text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded text-sm font-medium touch-manipulation">Ver detalle</button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal titulo="Abrir turno" abierto={modalAbrir} onCerrar={() => setModalAbrir(false)}>
        <form onSubmit={abrirTurno} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto de apertura</label>
            <input type="number" step={0.01} min={0} value={montoApertura} onChange={(e) => setMontoApertura(e.target.value)} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" placeholder="0.00" />
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => setModalAbrir(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={guardando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{guardando ? 'Abriendo...' : 'Abrir'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Cerrar turno" abierto={modalCerrar} onCerrar={() => setModalCerrar(false)}>
        <form onSubmit={cerrarTurno} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          {efectivoEsperado != null && (
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase">Efectivo esperado</p>
                  <p className="text-lg font-bold text-slate-800">
                    ${(efectivoEsperado ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText(String((efectivoEsperado ?? 0).toFixed(2)))}
                  className="text-xs px-2 py-1 border border-slate-300 rounded hover:bg-slate-100"
                  title="Copiar monto"
                >
                  Copiar
                </button>
              </div>
              {corte?.totales_por_metodo?.length > 0 && (
                <p className="text-xs text-slate-500">
                  Apertura + cobros efectivo − pagos proveedores − gastos
                </p>
              )}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto contado en caja</label>
            <input type="number" step={0.01} min={0} value={montoCierre} onChange={(e) => setMontoCierre(e.target.value)} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" placeholder="0.00" />
          </div>
          {efectivoEsperado != null && montoCierre !== '' && (
            (() => {
              const contado = aNumero(montoCierre)
              const diferencia = efectivoEsperado - contado
              const cuadra = Math.abs(diferencia) < 0.01
              return (
                <div className={`p-3 rounded-lg border ${cuadra ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
                  <p className="text-xs font-medium text-slate-500 uppercase">Diferencia</p>
                  <p className={`text-lg font-bold ${cuadra ? 'text-green-700' : 'text-amber-800'}`}>
                    {diferencia >= 0 ? '+' : ''}${diferencia.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {cuadra ? 'La caja cuadra' : diferencia > 0 ? 'Sobra efectivo' : 'Queda a deber'}
                  </p>
                </div>
              )
            })()
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => setModalCerrar(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={guardando} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">{guardando ? 'Cerrando...' : 'Cerrar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Detalle del turno" abierto={modalDetalle} onCerrar={() => { setModalDetalle(false); setDetalleTurno(null); setIdTurnoDetalle(null) }}>
        {cargandoDetalle ? (
          <p className="text-slate-500 py-4">Cargando...</p>
        ) : detalleTurno ? (
          <div className="space-y-4">
            {detalleTurno.turno?.diferencia != null && (
              <div className={`p-4 rounded-lg border ${Number(detalleTurno.turno.diferencia) < 0 ? 'bg-red-50 border-red-200' : Math.abs(Number(detalleTurno.turno.diferencia)) < 0.01 ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
                <p className="text-xs font-medium text-slate-500 uppercase">Resumen de cierre</p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                  <span className="text-slate-600">Efectivo esperado:</span>
                  <span className="text-right font-medium">${(Number(detalleTurno.turno?.efectivo_esperado) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
                  <span className="text-slate-600">Monto contado:</span>
                  <span className="text-right font-medium">${(Number(detalleTurno.turno?.monto_cierre) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
                  <span className="text-slate-600">Diferencia:</span>
                  <span className={`text-right font-bold ${Number(detalleTurno.turno.diferencia) < 0 ? 'text-red-700' : 'text-green-700'}`}>
                    {Number(detalleTurno.turno.diferencia) < 0
                      ? `Queda a deber $${Math.abs(Number(detalleTurno.turno.diferencia)).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
                      : Math.abs(Number(detalleTurno.turno.diferencia)) < 0.01
                        ? 'Cuadra'
                        : `Sobra $${Number(detalleTurno.turno.diferencia).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`}
                  </span>
                </div>
              </div>
            )}
            <div className="text-sm">
              <p className="font-medium text-slate-700 mb-2">Cobros por método</p>
              <ul className="space-y-1 text-slate-600">
                {detalleTurno.totales_por_metodo?.map((m) => (
                  <li key={m.metodo} className="flex justify-between"><span>{m.metodo}</span> <span>${Number(m.total).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span></li>
                ))}
                {(!detalleTurno.totales_por_metodo || detalleTurno.totales_por_metodo.length === 0) && <li className="text-slate-400">Sin cobros</li>}
              </ul>
            </div>
            {(detalleTurno.total_gastos > 0 || detalleTurno.total_pagos_proveedores > 0) && (
              <div className="text-sm space-y-1">
                {detalleTurno.total_gastos > 0 && <p className="text-slate-600">Gastos: <span className="font-medium text-red-600">−${Number(detalleTurno.total_gastos).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span></p>}
                {detalleTurno.total_pagos_proveedores > 0 && <p className="text-slate-600">Pagos proveedores: <span className="font-medium text-red-600">−${Number(detalleTurno.total_pagos_proveedores).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span></p>}
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 text-center">
            <p className="text-slate-500 mb-4">No se pudo cargar el detalle</p>
            {idTurnoDetalle && (
              <button type="button" onClick={() => cargarDetalleTurno(idTurnoDetalle)} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                Reintentar
              </button>
            )}
          </div>
        )}
      </Modal>

      <Modal titulo="Cierre forzado de turno" abierto={modalCerrarForzado} onCerrar={() => { setModalCerrarForzado(false); setTurnoForzado(null) }}>
        {turnoForzado && (
          <form onSubmit={cerrarForzado} className="space-y-4">
            {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
            <p className="text-sm text-slate-600">
              Cerrando turno de <strong>{turnoForzado.usuario_nombre || `#${turnoForzado.id_usuario}`}</strong>
              {turnoForzado.fecha_apertura && ` (apertura: ${formatearFechaHora(turnoForzado.fecha_apertura)})`}
            </p>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Monto en caja al cierre *</label>
              <input type="number" step={0.01} min={0} value={montoCierreForzado} onChange={(e) => setMontoCierreForzado(e.target.value)} required className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" placeholder="0.00" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Motivo (opcional)</label>
              <input type="text" value={motivoForzado} onChange={(e) => setMotivoForzado(e.target.value)} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" placeholder="Ej: Cierre por ausencia del cajero" />
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <button type="button" onClick={() => { setModalCerrarForzado(false); setTurnoForzado(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
              <button type="submit" disabled={guardando} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">{guardando ? 'Cerrando...' : 'Cerrar forzado'}</button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  )
}
