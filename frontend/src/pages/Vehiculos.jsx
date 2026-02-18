import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import PageHeader, { IconDownload, IconPlus, btnExport, btnNuevo } from '../components/PageHeader'
import { useAuth } from '../context/AuthContext'
import { hoyStr, formatearFechaSolo } from '../utils/fechas'
import { normalizeDetail, showError } from '../utils/toast'
import { aEntero } from '../utils/numeros'
import { useApiQuery, useInvalidateQueries } from '../hooks/useApi'

export default function Vehiculos() {
  const { user } = useAuth()
  const invalidate = useInvalidateQueries()
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [filtroCliente, setFiltroCliente] = useState('')
  const [form, setForm] = useState({ id_cliente: '', marca: '', modelo: '', anio: new Date().getFullYear(), numero_serie: '', color: '', motor: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clientes, setClientes] = useState([])
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [modalHistorial, setModalHistorial] = useState(false)
  const [historialData, setHistorialData] = useState(null)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [modalEliminar, setModalEliminar] = useState(false)
  const [vehiculoAEliminar, setVehiculoAEliminar] = useState(null)
  const [datosEliminar, setDatosEliminar] = useState(null)
  const [motivoEliminacion, setMotivoEliminacion] = useState('')
  const [errorEliminar, setErrorEliminar] = useState('')
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [procesandoOrdenId, setProcesandoOrdenId] = useState(null)
  const [exportando, setExportando] = useState(false)
  const limit = 20

  const { data: listData, isLoading: loading } = useApiQuery(
    ['vehiculos', pagina, filtroCliente, buscar.trim()],
    () => api.get('/vehiculos/', { params: { skip: (pagina - 1) * limit, limit, ...(filtroCliente ? { id_cliente: filtroCliente } : {}), ...(buscar.trim() ? { buscar: buscar.trim() } : {}) } }).then((r) => r.data),
    { staleTime: 45 * 1000 }
  )
  const vehiculos = listData?.vehiculos ?? (Array.isArray(listData) ? listData : [])
  const totalVehiculos = listData?.total ?? (Array.isArray(listData) ? listData.length : 0)
  const totalPaginas = listData?.total_paginas ?? 1

  const recargar = () => invalidate(['vehiculos'])

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = { limit: 10000 }
      if (buscar.trim()) params.buscar = buscar.trim()
      if (filtroCliente) params.id_cliente = filtroCliente
      const res = await api.get('/exportaciones/vehiculos', { params, responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `vehiculos_${hoyStr()}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      showError(err, 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  useEffect(() => {
    api.get('/clientes/', { params: { limit: 500 } }).then((res) => {
      const d = res.data
      setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
    }).catch((err) => {
      showError(err, 'Error al cargar clientes')
      setClientes([])
    })
  }, [])

  const abrirNuevo = (clientePre = null) => {
    const cliente = clientePre || (filtroCliente ? clientes.find((c) => c.id_cliente === aEntero(filtroCliente)) : null)
    setEditando(null)
    setForm({ id_cliente: cliente?.id_cliente ? String(cliente.id_cliente) : '', marca: '', modelo: '', anio: new Date().getFullYear(), numero_serie: '', color: '', motor: '' })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (v) => {
    setEditando(v)
    setForm({ id_cliente: v.id_cliente ? String(v.id_cliente) : '', marca: v.marca || '', modelo: v.modelo || '', anio: v.anio || new Date().getFullYear(), numero_serie: v.numero_serie || v.vin || '', color: v.color || '', motor: v.motor || '' })
    setError('')
    setModalAbierto(true)
  }

  const abrirHistorial = async (v) => {
    setHistorialData(null)
    setModalHistorial(true)
    setCargandoHistorial(true)
    try {
      const res = await api.get(`/vehiculos/${v.id_vehiculo}/historial`)
      setHistorialData(res.data)
    } catch (err) {
      setHistorialData(null)
      showError(err, 'Error al cargar historial')
    } finally {
      setCargandoHistorial(false)
    }
  }

  const abrirModalEliminar = async (v) => {
    setVehiculoAEliminar(v)
    setDatosEliminar(null)
    setMotivoEliminacion('')
    setErrorEliminar('')
    setModalEliminar(true)
    try {
      const res = await api.get(`/vehiculos/${v.id_vehiculo}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      setErrorEliminar(normalizeDetail(err.response?.data?.detail) || 'Error al cargar datos')
    }
  }

  const cancelarOrden = async (orden) => {
    if (orden.estado === 'ENTREGADA') return
    if (orden.estado === 'CANCELADA') return
    const motivo = window.prompt('Motivo de la cancelación (mín. 10 caracteres):', '')
    if (!motivo || motivo.trim().length < 10) {
      if (motivo !== null) showError('El motivo debe tener al menos 10 caracteres.')
      return
    }
    setProcesandoOrdenId(orden.id)
    try {
      await api.post(`/ordenes-trabajo/${orden.id}/cancelar`, null, { params: { motivo: motivo.trim() } })
      const res = await api.get(`/vehiculos/${vehiculoAEliminar.id_vehiculo}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      showError(err, 'Error al cancelar')
    } finally {
      setProcesandoOrdenId(null)
    }
  }

  const eliminarOrden = async (orden) => {
    if (orden.estado !== 'CANCELADA') return
    if (!window.confirm(`¿Eliminar permanentemente la orden ${orden.numero_orden}?`)) return
    setProcesandoOrdenId(orden.id)
    try {
      await api.delete(`/ordenes-trabajo/${orden.id}`)
      const res = await api.get(`/vehiculos/${vehiculoAEliminar.id_vehiculo}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      showError(err, 'Error al eliminar orden')
    } finally {
      setProcesandoOrdenId(null)
    }
  }

  const confirmarEliminarVehiculo = async () => {
    if (!vehiculoAEliminar) return
    if (!motivoEliminacion.trim() || motivoEliminacion.trim().length < 10) {
      setErrorEliminar('El motivo debe tener al menos 10 caracteres.')
      return
    }
    const ordenes = datosEliminar?.ordenes_trabajo ?? []
    if (ordenes.length > 0) {
      setErrorEliminar('Debes cancelar y/o eliminar todas las órdenes antes de eliminar el vehículo.')
      return
    }
    setEnviandoEliminar(true)
    setErrorEliminar('')
    try {
      await api.delete(`/vehiculos/${vehiculoAEliminar.id_vehiculo}`, { data: { motivo: motivoEliminacion.trim() } })
      setModalEliminar(false)
      setVehiculoAEliminar(null)
      setDatosEliminar(null)
      setMotivoEliminacion('')
      recargar()
    } catch (err) {
      setErrorEliminar(normalizeDetail(err.response?.data?.detail) || 'Error al eliminar')
    } finally {
      setEnviandoEliminar(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const idCliente = aEntero(form.id_cliente)
    const anio = aEntero(form.anio)
    if (!idCliente) {
      setError('Selecciona un cliente')
      return
    }
    if (!anio || anio < 1900 || anio > 2030) {
      setError('El año debe ser un número entre 1900 y 2030')
      return
    }
    setEnviando(true)
    try {
      const payload = {
        id_cliente: idCliente,
        marca: form.marca.trim(),
        modelo: form.modelo.trim(),
        anio,
        numero_serie: form.numero_serie?.trim() || null,
        color: form.color?.trim() || null,
        motor: form.motor?.trim() || null,
      }
      if (editando) await api.put(`/vehiculos/${editando.id_vehiculo}`, payload)
      else await api.post('/vehiculos/', payload)
      recargar()
      setModalAbierto(false)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="min-h-0 space-y-5">
      <PageHeader title="Vehículos" subtitle="Gestión del parque vehicular">
        <button type="button" onClick={exportarExcel} disabled={exportando} className={btnExport}>
          <IconDownload />
          {exportando ? 'Exportando...' : 'Exportar'}
        </button>
        <button type="button" onClick={() => abrirNuevo()} className={btnNuevo}>
          <IconPlus />
          Nuevo vehículo
        </button>
      </PageHeader>

      {/* Filtros en card sutil */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm p-4">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">Buscar</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              </span>
              <input
                type="text"
                placeholder="Marca, modelo, VIN..."
                value={buscar}
                onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
                className="w-full pl-10 pr-4 py-2.5 min-h-[44px] text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors touch-manipulation placeholder:text-slate-400"
              />
            </div>
          </div>
          <div className="min-w-[200px] flex-1 sm:flex-initial">
            <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wider">Cliente</label>
            <select
              value={filtroCliente}
              onChange={(e) => { setFiltroCliente(e.target.value); setPagina(1) }}
              className="w-full px-4 py-2.5 min-h-[44px] text-sm border border-slate-200 rounded-lg bg-slate-50/50 focus:bg-white focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 transition-colors touch-manipulation text-slate-700"
            >
              <option value="">Todos los clientes</option>
              {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Tabla con look refinado */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden relative">
        {loading && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-10 rounded-xl">
            <div className="animate-pulse text-slate-500 text-sm">Cargando...</div>
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70">
                <th className="px-4 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Cliente</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Marca / Modelo</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Año</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Color</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Motor</th>
                <th className="px-4 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">VIN / Serie</th>
                <th className="px-4 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {vehiculos.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-16 text-center">
                    <p className="text-slate-500 font-medium">No hay vehículos</p>
                    <p className="text-sm text-slate-400 mt-1">Registra el primer vehículo con el botón de arriba</p>
                  </td>
                </tr>
              ) : (
                vehiculos.map((v, i) => (
                  <tr
                    key={v.id_vehiculo}
                    className={`hover:bg-primary-50/40 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}
                  >
                    <td className="px-4 py-3.5 text-sm text-slate-700">{v.cliente_nombre || clientes.find((c) => c.id_cliente === v.id_cliente)?.nombre || `ID ${v.id_cliente}`}</td>
                    <td className="px-4 py-3.5">
                      <span className="font-semibold text-slate-800 text-primary-600/90 hover:text-primary-700">{v.marca} {v.modelo}</span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-slate-600">{v.anio}</td>
                    <td className="px-4 py-3.5 text-sm text-slate-600">{v.color || '—'}</td>
                    <td className="px-4 py-3.5 text-sm text-slate-600">{v.motor || '—'}</td>
                    <td className="px-4 py-3.5 text-sm text-slate-600 font-mono text-xs">{v.numero_serie || v.vin || '—'}</td>
                    <td className="px-4 py-3.5 text-right whitespace-nowrap">
                      <div className="flex gap-1 justify-end items-center">
                        <button type="button" onClick={() => abrirHistorial(v)} className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors touch-manipulation" title="Ver historial">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                        </button>
                        <button type="button" onClick={() => abrirEditar(v)} className="px-3 py-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded-lg transition-colors touch-manipulation">Editar</button>
                        {user?.rol === 'ADMIN' && (
                          <button type="button" onClick={() => abrirModalEliminar(v)} className="px-3 py-1.5 text-sm font-medium text-red-600/90 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors touch-manipulation">Eliminar</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPaginas > 1 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 py-2">
          <p className="text-sm text-slate-500 order-2 sm:order-1">{(pagina - 1) * limit + 1} – {Math.min(pagina * limit, totalVehiculos)} de {totalVehiculos}</p>
          <div className="flex items-center gap-2 order-1 sm:order-2">
            <button
              type="button"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1}
              className="min-h-[40px] px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors touch-manipulation"
            >
              Anterior
            </button>
            <span className="px-4 py-2 text-sm text-slate-600 font-medium">Pág. {pagina} de {totalPaginas}</span>
            <button
              type="button"
              onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
              disabled={pagina >= totalPaginas}
              className="min-h-[40px] px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors touch-manipulation"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}

      <Modal titulo={`Historial — ${historialData?.vehiculo?.marca || ''} ${historialData?.vehiculo?.modelo || ''} ${historialData?.vehiculo?.anio || ''}`} abierto={modalHistorial} onCerrar={() => { setModalHistorial(false); setHistorialData(null) }}>
        {cargandoHistorial ? <p className="text-slate-500 py-4">Cargando historial...</p> : historialData ? (
          <div className="space-y-6 max-h-[70vh] overflow-y-auto">
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Datos</h3><div className="text-sm text-slate-600"><p><span className="font-medium">Cliente:</span> {historialData.vehiculo?.cliente_nombre || '-'}</p><p><span className="font-medium">Color:</span> {historialData.vehiculo?.color || '-'}</p><p><span className="font-medium">Motor:</span> {historialData.vehiculo?.motor ?? '-'}</p><p><span className="font-medium">VIN:</span> {historialData.vehiculo?.vin || '-'}</p></div></div>
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Resumen</h3><div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm"><div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Órdenes:</span> {historialData.resumen?.cantidad_ordenes ?? 0}</div><div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Ventas:</span> {historialData.resumen?.cantidad_ventas ?? 0}</div></div></div>
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes ({historialData.ordenes_trabajo?.length ?? 0})</h3>{(historialData.ordenes_trabajo?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin órdenes</p> : <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr><th className="text-left py-1">Nº</th><th className="text-left py-1">Fecha</th><th className="text-left py-1">Estado</th><th className="text-right py-1">Total</th></tr></thead><tbody>{historialData.ordenes_trabajo.map((o) => <tr key={o.id}><td className="py-1">{o.numero_orden}</td><td>{formatearFechaSolo(o.fecha_ingreso)}</td><td>{o.estado || '-'}</td><td className="text-right">${(o.total ?? 0).toFixed(2)}</td></tr>)}</tbody></table></div>}</div>
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Ventas ({historialData.ventas?.length ?? 0})</h3>{(historialData.ventas?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin ventas</p> : <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr><th className="text-left py-1">ID</th><th className="text-left py-1">Fecha</th><th className="text-right py-1">Total</th><th className="text-right py-1">Pagado</th><th className="text-left py-1">Estado</th></tr></thead><tbody>{historialData.ventas.map((v) => <tr key={v.id_venta}><td className="py-1">{v.id_venta}</td><td>{formatearFechaSolo(v.fecha)}</td><td className="text-right">${(v.total ?? 0).toFixed(2)}</td><td className="text-right">${(v.total_pagado ?? 0).toFixed(2)}</td><td>{v.estado || '-'}</td></tr>)}</tbody></table></div>}</div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo={`Eliminar vehículo — ${vehiculoAEliminar?.marca || ''} ${vehiculoAEliminar?.modelo || ''} (${vehiculoAEliminar?.anio || ''})`} abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setVehiculoAEliminar(null); setDatosEliminar(null); setMotivoEliminacion(''); setErrorEliminar('') }}>
        <div className="space-y-4 max-h-[70vh] overflow-y-auto">
          {errorEliminar && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{errorEliminar}</div>}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            Se registrará quién eliminó el vehículo y el motivo. Esta acción no se puede deshacer.
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motivo de eliminación (obligatorio, mín. 10 caracteres) *</label>
            <textarea
              value={motivoEliminacion}
              onChange={(e) => setMotivoEliminacion(e.target.value)}
              placeholder="Ej: Vehículo vendido, registro duplicado, datos incorrectos..."
              rows={3}
              className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation"
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes de trabajo asociadas ({(datosEliminar?.ordenes_trabajo?.length ?? 0)})</h3>
            {!datosEliminar ? <p className="text-slate-500 text-sm">Cargando...</p> : (datosEliminar.ordenes_trabajo?.length ?? 0) === 0 ? (
              <p className="text-slate-500 text-sm">No hay órdenes asociadas.</p>
            ) : (
              <div className="border rounded-lg overflow-hidden overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs text-slate-500">Nº</th>
                      <th className="px-3 py-2 text-left text-xs text-slate-500">Fecha</th>
                      <th className="px-3 py-2 text-left text-xs text-slate-500">Estado</th>
                      <th className="px-3 py-2 text-right text-xs text-slate-500">Total</th>
                      <th className="px-3 py-2 text-right text-xs text-slate-500">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {datosEliminar.ordenes_trabajo.map((o) => (
                      <tr key={o.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium">{o.numero_orden}</td>
                        <td className="px-3 py-2 text-slate-600">{formatearFechaSolo(o.fecha_ingreso)}</td>
                        <td className="px-3 py-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${o.estado === 'CANCELADA' ? 'bg-slate-200 text-slate-700' : o.estado === 'ENTREGADA' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
                            {o.estado || '-'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right">${(o.total ?? 0).toFixed(2)}</td>
                        <td className="px-3 py-2 text-right">
                          {o.estado === 'ENTREGADA' ? (
                            <span className="text-xs text-slate-500">No se puede eliminar</span>
                          ) : o.estado === 'CANCELADA' ? (
                            <button type="button" onClick={() => eliminarOrden(o)} disabled={procesandoOrdenId === o.id} className="text-xs text-red-600 hover:text-red-700 disabled:opacity-50">
                              {procesandoOrdenId === o.id ? '...' : 'Eliminar orden'}
                            </button>
                          ) : (
                            <button type="button" onClick={() => cancelarOrden(o)} disabled={procesandoOrdenId === o.id} className="text-xs text-amber-600 hover:text-amber-700 disabled:opacity-50">
                              {procesandoOrdenId === o.id ? '...' : 'Cancelar orden'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {(datosEliminar?.ordenes_trabajo?.length ?? 0) > 0 && (
              <p className="mt-2 text-xs text-slate-500">Cancela las órdenes activas y luego elimina las canceladas. Las órdenes entregadas bloquean la eliminación del vehículo.</p>
            )}
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2 border-t">
            <button type="button" onClick={() => { setModalEliminar(false); setVehiculoAEliminar(null); setDatosEliminar(null); setMotivoEliminacion('') }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">No eliminar</button>
            <button
              type="button"
              onClick={confirmarEliminarVehiculo}
              disabled={enviandoEliminar || !motivoEliminacion.trim() || motivoEliminacion.trim().length < 10 || (datosEliminar?.ordenes_trabajo?.length ?? 0) > 0}
              className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
            >
              {enviandoEliminar ? 'Eliminando...' : 'Eliminar vehículo'}
            </button>
          </div>
        </div>
      </Modal>

      <Modal titulo={editando ? 'Editar vehículo' : 'Nuevo vehículo'} abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label>
            {editando ? (
              <div className="w-full px-4 py-3 min-h-[48px] flex items-center border border-slate-200 rounded-lg bg-slate-50 text-slate-700">
                {editando.cliente_nombre || clientes.find((c) => c.id_cliente === editando.id_cliente)?.nombre || `Cliente #${editando.id_cliente}`}
              </div>
            ) : (
              <select
                value={form.id_cliente}
                onChange={(e) => setForm({ ...form, id_cliente: e.target.value })}
                required
                className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation"
              >
                <option value="">Seleccionar cliente...</option>
                {clientes.map((c) => <option key={c.id_cliente} value={String(c.id_cliente)}>{c.nombre}</option>)}
              </select>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label><input type="text" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} required placeholder="Ej: Nissan" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" /></div>
            <div><label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label><input type="text" value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value })} required placeholder="Ej: Versa" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" /></div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-slate-700 mb-1">Año *</label><input type="number" min={1900} max={2030} value={form.anio} onChange={(e) => setForm({ ...form, anio: e.target.value })} required className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" /></div>
            <div><label className="block text-sm font-medium text-slate-700 mb-1">VIN / Núm. serie</label><input type="text" value={form.numero_serie} onChange={(e) => setForm({ ...form, numero_serie: e.target.value })} className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" /></div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-slate-700 mb-1">Color</label><input type="text" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} placeholder="Ej: Blanco, Negro" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" /></div>
            <div><label className="block text-sm font-medium text-slate-700 mb-1">Motor</label><input type="text" value={form.motor} onChange={(e) => setForm({ ...form, motor: e.target.value })} placeholder="Ej: 1.8, 2.0" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" /></div>
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2"><button type="button" onClick={() => setModalAbierto(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button><button type="submit" disabled={enviando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviando ? 'Guardando...' : 'Guardar'}</button></div>
        </form>
      </Modal>
    </div>
  )
}
