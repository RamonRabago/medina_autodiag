import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { hoyStr, formatearFechaSolo, formatearFechaHora } from '../utils/fechas'
import PageLoading from '../components/PageLoading'
import { normalizeDetail, showError } from '../utils/toast'
import { aEntero } from '../utils/numeros'

export default function Clientes() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({ nombre: '', telefono: '', email: '', direccion: '', rfc: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalVehiculo, setModalVehiculo] = useState(false)
  const [clienteParaVehiculo, setClienteParaVehiculo] = useState(null)
  const [formVehiculo, setFormVehiculo] = useState({ marca: '', modelo: '', anio: new Date().getFullYear(), color: '', numero_serie: '', motor: '' })
  const [enviandoVehiculo, setEnviandoVehiculo] = useState(false)
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [totalClientes, setTotalClientes] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [modalHistorial, setModalHistorial] = useState(false)
  const [historialData, setHistorialData] = useState(null)
  const [historialError, setHistorialError] = useState('')
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [modalEliminar, setModalEliminar] = useState(false)
  const [clienteAEliminar, setClienteAEliminar] = useState(null)
  const [datosEliminar, setDatosEliminar] = useState(null)
  const [motivoEliminacion, setMotivoEliminacion] = useState('')
  const [errorEliminar, setErrorEliminar] = useState('')
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [procesandoOrdenId, setProcesandoOrdenId] = useState(null)
  const [exportando, setExportando] = useState(false)
  const limit = 20

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = { limit: 10000 }
      if (buscar.trim()) params.buscar = buscar.trim()
      const res = await api.get('/exportaciones/clientes', { params, responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `clientes_${hoyStr()}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      showError(err, 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  const cargar = () => {
    const params = { skip: (pagina - 1) * limit, limit }
    if (buscar.trim()) params.buscar = buscar.trim()
    api.get('/clientes/', { params }).then((res) => {
      const d = res.data
      if (d?.clientes) {
        setClientes(d.clientes)
        setTotalClientes(d.total ?? d.clientes.length)
        setTotalPaginas(d.total_paginas ?? 1)
      } else {
        setClientes(Array.isArray(d) ? d : [])
        setTotalClientes(Array.isArray(d) ? d.length : 0)
        setTotalPaginas(1)
      }
    }).catch((err) => {
      showError(err, 'Error al cargar clientes')
      setClientes([])
    })
  }

  useEffect(() => { cargar() }, [pagina, buscar])
  useEffect(() => {
    setLoading(false)
  }, [])

  useEffect(() => {
    if (searchParams.get('nuevo') === '1') {
      abrirNuevo()
      setSearchParams({})
    }
  }, [])

  const abrirNuevo = () => {
    setEditando(null)
    setForm({ nombre: '', telefono: '', email: '', direccion: '', rfc: '' })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (c) => {
    setEditando(c)
    setForm({ nombre: c.nombre || '', telefono: c.telefono || '', email: c.email || '', direccion: c.direccion || '', rfc: c.rfc || '' })
    setError('')
    setModalAbierto(true)
  }

  const abrirHistorial = async (c) => {
    setHistorialData(null)
    setHistorialError('')
    setModalHistorial(true)
    setCargandoHistorial(true)
    try {
      const res = await api.get(`/clientes/${c.id_cliente}/historial`)
      setHistorialData(res.data)
    } catch (err) {
      setHistorialData(null)
      setHistorialError(normalizeDetail(err.response?.data?.detail) || 'Error al cargar historial')
    } finally {
      setCargandoHistorial(false)
    }
  }

  const abrirAgregarVehiculo = (c) => {
    setClienteParaVehiculo(c)
    setFormVehiculo({ marca: '', modelo: '', anio: new Date().getFullYear(), color: '', numero_serie: '', motor: '' })
    setModalVehiculo(true)
  }

  const abrirModalEliminar = async (c) => {
    setClienteAEliminar(c)
    setDatosEliminar(null)
    setMotivoEliminacion('')
    setErrorEliminar('')
    setModalEliminar(true)
    try {
      const res = await api.get(`/clientes/${c.id_cliente}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      setErrorEliminar(normalizeDetail(err.response?.data?.detail) || 'Error al cargar datos')
    }
  }

  const cancelarOrden = async (orden) => {
    if (orden.estado === 'ENTREGADA' || orden.estado === 'CANCELADA') return
    const motivo = window.prompt('Motivo de la cancelación (mín. 10 caracteres):', '')
    if (!motivo || motivo.trim().length < 10) {
      if (motivo !== null) showError('El motivo debe tener al menos 10 caracteres.')
      return
    }
    setProcesandoOrdenId(orden.id)
    try {
      await api.post(`/ordenes-trabajo/${orden.id}/cancelar`, null, { params: { motivo: motivo.trim() } })
      const res = await api.get(`/clientes/${clienteAEliminar.id_cliente}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      showError(normalizeDetail(err.response?.data?.detail) || 'Error al cancelar')
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
      const res = await api.get(`/clientes/${clienteAEliminar.id_cliente}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      showError(normalizeDetail(err.response?.data?.detail) || 'Error al eliminar orden')
    } finally {
      setProcesandoOrdenId(null)
    }
  }

  const confirmarEliminarCliente = async () => {
    if (!clienteAEliminar) return
    if (!motivoEliminacion.trim() || motivoEliminacion.trim().length < 10) {
      setErrorEliminar('El motivo debe tener al menos 10 caracteres.')
      return
    }
    const ordenes = datosEliminar?.ordenes_trabajo ?? []
    const ventas = datosEliminar?.ventas ?? []
    const vehiculos = datosEliminar?.vehiculos ?? []
    if (ordenes.length > 0 || ventas.length > 0 || vehiculos.length > 0) {
      setErrorEliminar('Debes cancelar/eliminar todas las órdenes. Las ventas y vehículos deben gestionarse en sus respectivas secciones.')
      return
    }
    setEnviandoEliminar(true)
    setErrorEliminar('')
    try {
      await api.delete(`/clientes/${clienteAEliminar.id_cliente}`, { data: { motivo: motivoEliminacion.trim() } })
      setModalEliminar(false)
      setClienteAEliminar(null)
      setDatosEliminar(null)
      setMotivoEliminacion('')
      cargar()
    } catch (err) {
      setErrorEliminar(normalizeDetail(err.response?.data?.detail) || 'Error al eliminar')
    } finally {
      setEnviandoEliminar(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      const payload = {
        nombre: form.nombre.trim(),
        telefono: form.telefono?.trim() || null,
        email: form.email?.trim() || null,
        direccion: form.direccion?.trim() || null,
        rfc: form.rfc?.trim() || null,
      }
      if (editando) {
        await api.put(`/clientes/${editando.id_cliente}`, payload)
      } else {
        await api.post('/clientes/', payload)
      }
      cargar()
      setModalAbierto(false)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const handleVehiculoSubmit = async (e) => {
    e.preventDefault()
    const anio = aEntero(formVehiculo.anio)
    if (!anio || anio < 1900 || anio > 2030) {
      showError(null, 'El año debe ser un número entre 1900 y 2030')
      return
    }
    setEnviandoVehiculo(true)
    try {
      await api.post('/vehiculos/', {
        id_cliente: clienteParaVehiculo.id_cliente,
        marca: formVehiculo.marca.trim(),
        modelo: formVehiculo.modelo.trim(),
        anio,
        color: formVehiculo.color?.trim() || null,
        numero_serie: formVehiculo.numero_serie?.trim() || null,
        motor: formVehiculo.motor?.trim() || null,
      })
      setModalVehiculo(false)
      setClienteParaVehiculo(null)
      cargar()
    } catch (err) {
      showError(normalizeDetail(err.response?.data?.detail) || 'Error al agregar vehículo')
    } finally {
      setEnviandoVehiculo(false)
    }
  }

  if (loading) return <PageLoading mensaje="Cargando clientes..." />

  return (
    <div className="min-h-0">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Clientes</h1>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={exportarExcel} disabled={exportando} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 font-medium disabled:opacity-50 text-sm touch-manipulation">📥 {exportando ? 'Exportando...' : 'Exportar'}</button>
          <button type="button" onClick={abrirNuevo} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation">Nuevo cliente</button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <input
          type="text"
          placeholder="Buscar por nombre, teléfono, email o RFC..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
          className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
        />
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Teléfono</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Dirección</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">RFC</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {clientes.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">No hay clientes registrados</td></tr>
            ) : (
              clientes.map((c) => (
                <tr key={c.id_cliente} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-800">{c.id_cliente}</td>
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{c.nombre}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{c.telefono || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{c.email || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 max-w-[180px] truncate" title={c.direccion || ''}>{c.direccion || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{c.rfc || '-'}</td>
                  <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                    <div className="flex justify-end gap-1 flex-wrap">
                      <button type="button" onClick={() => abrirHistorial(c)} className="min-h-[40px] min-w-[40px] flex items-center justify-center text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation" title="Ver historial">📋</button>
                      <button type="button" onClick={() => abrirAgregarVehiculo(c)} className="min-h-[40px] min-w-[40px] flex items-center justify-center text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation" title="Agregar vehículo">🚗</button>
                      <button type="button" onClick={() => abrirEditar(c)} className="min-h-[40px] px-2 py-1.5 text-sm text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded touch-manipulation">Editar</button>
                      {user?.rol === 'ADMIN' && <button type="button" onClick={() => abrirModalEliminar(c)} className="min-h-[40px] px-2 py-1.5 text-sm text-red-600 hover:text-red-800 active:bg-red-50 rounded touch-manipulation" title="Eliminar cliente">Eliminar</button>}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPaginas > 1 && (
        <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <p className="text-sm text-slate-600 order-2 sm:order-1">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, totalClientes)} de {totalClientes}</p>
          <div className="flex gap-2 justify-center sm:justify-end order-1 sm:order-2">
            <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 touch-manipulation active:bg-slate-50">Anterior</button>
            <span className="min-h-[44px] px-3 py-2 flex items-center justify-center text-sm text-slate-700">Pág. {pagina} de {totalPaginas}</span>
            <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 touch-manipulation active:bg-slate-50">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={`Historial — ${historialData?.cliente?.nombre || 'Cliente'}`} abierto={modalHistorial} onCerrar={() => { setModalHistorial(false); setHistorialData(null); setHistorialError('') }}>
        {cargandoHistorial ? <p className="text-slate-500 py-4">Cargando historial...</p> : historialError ? (
          <div className="p-4 bg-red-50 text-red-600 rounded-lg">{historialError}</div>
        ) : historialData ? (
          <div className="space-y-6 max-h-[70vh] overflow-y-auto">
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Datos</h3>
              <div className="text-sm text-slate-600 space-y-1">
                <p><span className="font-medium">Tel:</span> {historialData.cliente?.telefono || '-'}</p>
                <p><span className="font-medium">Email:</span> {historialData.cliente?.email || '-'}</p>
                <p><span className="font-medium">Dirección:</span> {historialData.cliente?.direccion || '-'}</p>
                <p><span className="font-medium">RFC:</span> {historialData.cliente?.rfc || '-'}</p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Resumen</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 text-sm">
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Ventas:</span> {historialData.resumen?.cantidad_ventas ?? 0}</div>
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Total $:</span> ${(Number(historialData.resumen?.total_ventas) || 0).toFixed(2)}</div>
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Órdenes:</span> {historialData.resumen?.cantidad_ordenes ?? 0}</div>
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Citas:</span> {historialData.resumen?.cantidad_citas ?? 0}</div>
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Vehículos:</span> {historialData.resumen?.cantidad_vehiculos ?? 0}</div>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Vehículos ({historialData.vehiculos?.length ?? 0})</h3>
              {(historialData.vehiculos?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin vehículos</p> : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead><tr><th className="text-left py-1">Marca/Modelo</th><th className="text-left py-1">Año</th><th className="text-left py-1">VIN</th></tr></thead>
                    <tbody>
                      {historialData.vehiculos.map((v) => (
                        <tr key={v.id_vehiculo}><td className="py-1">{v.marca} {v.modelo}</td><td>{v.anio}</td><td>{v.vin || '-'}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Ventas ({historialData.ventas?.length ?? 0})</h3>
              {(historialData.ventas?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin ventas</p> : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead><tr><th className="text-left py-1">ID</th><th className="text-left py-1">Fecha</th><th className="text-right py-1">Total</th><th className="text-right py-1">Pagado</th><th className="text-left py-1">Estado</th></tr></thead>
                    <tbody>
                      {historialData.ventas.map((v) => (
                        <tr key={v.id_venta}><td className="py-1">{v.id_venta}</td><td>{formatearFechaSolo(v.fecha)}</td><td className="text-right">${(Number(v.total) || 0).toFixed(2)}</td><td className="text-right">${(Number(v.total_pagado) || 0).toFixed(2)}</td><td>{v.estado || '-'}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes de trabajo ({historialData.ordenes_trabajo?.length ?? 0})</h3>
              {(historialData.ordenes_trabajo?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin órdenes</p> : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead><tr><th className="text-left py-1">Nº</th><th className="text-left py-1">Vehículo</th><th className="text-left py-1">Estado</th><th className="text-right py-1">Total</th></tr></thead>
                    <tbody>
                      {historialData.ordenes_trabajo.map((o) => (
                        <tr key={o.id}><td className="py-1">{o.numero_orden}</td><td>{o.vehiculo || '-'}</td><td>{o.estado || '-'}</td><td className="text-right">${(Number(o.total) || 0).toFixed(2)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Citas ({historialData.citas?.length ?? 0})</h3>
              {(historialData.citas?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin citas</p> : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead><tr><th className="text-left py-1">Fecha</th><th className="text-left py-1">Tipo</th><th className="text-left py-1">Estado</th><th className="text-left py-1">Motivo</th></tr></thead>
                    <tbody>
                      {historialData.citas.map((c) => (
                        <tr key={c.id_cita}><td className="py-1">{formatearFechaHora(c.fecha_hora)}</td><td>{c.tipo || '-'}</td><td>{c.estado || '-'}</td><td>{c.motivo || '-'}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo={`Eliminar cliente — ${clienteAEliminar?.nombre || ''}`} abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setClienteAEliminar(null); setDatosEliminar(null); setMotivoEliminacion(''); setErrorEliminar('') }}>
        <div className="space-y-4 max-h-[70vh] overflow-y-auto">
          {errorEliminar && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{errorEliminar}</div>}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            Se registrará quién eliminó el cliente y el motivo. Esta acción no se puede deshacer.
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motivo de eliminación (obligatorio, mín. 10 caracteres) *</label>
            <textarea
              value={motivoEliminacion}
              onChange={(e) => setMotivoEliminacion(e.target.value)}
              placeholder="Ej: Cliente duplicado, registro incorrecto, solicitud del cliente..."
              rows={3}
              className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation"
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes de trabajo ({(datosEliminar?.ordenes_trabajo?.length ?? 0)})</h3>
            {!datosEliminar ? <p className="text-slate-500 text-sm">Cargando...</p> : (datosEliminar.ordenes_trabajo?.length ?? 0) === 0 ? (
              <p className="text-slate-500 text-sm">No hay órdenes asociadas.</p>
            ) : (
              <div className="border rounded-lg overflow-hidden overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs text-slate-500">Nº</th>
                      <th className="px-3 py-2 text-left text-xs text-slate-500">Vehículo</th>
                      <th className="px-3 py-2 text-left text-xs text-slate-500">Estado</th>
                      <th className="px-3 py-2 text-right text-xs text-slate-500">Total</th>
                      <th className="px-3 py-2 text-right text-xs text-slate-500">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {datosEliminar.ordenes_trabajo.map((o) => (
                      <tr key={o.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium">{o.numero_orden}</td>
                        <td className="px-3 py-2 text-slate-600">{o.vehiculo || '-'}</td>
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
            <p className="mt-2 text-xs text-slate-500">Cancela las órdenes activas y luego elimina las canceladas.</p>
          </div>
          {(datosEliminar?.ventas?.length ?? 0) > 0 && (
            <div className="p-3 bg-slate-50 rounded-lg text-sm text-slate-700">
              <strong>Ventas ({datosEliminar.ventas.length}):</strong> Deben gestionarse desde la sección Ventas.
            </div>
          )}
          {(datosEliminar?.vehiculos?.length ?? 0) > 0 && (
            <div className="p-3 bg-slate-50 rounded-lg text-sm text-slate-700">
              <strong>Vehículos ({datosEliminar.vehiculos.length}):</strong> Elimínalos desde la sección Vehículos primero.
            </div>
          )}
          <div className="flex flex-wrap justify-end gap-2 pt-2 border-t">
            <button type="button" onClick={() => { setModalEliminar(false); setClienteAEliminar(null); setDatosEliminar(null); setMotivoEliminacion('') }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">No eliminar</button>
            <button
              type="button"
              onClick={confirmarEliminarCliente}
              disabled={enviandoEliminar || !motivoEliminacion.trim() || motivoEliminacion.trim().length < 10 || (datosEliminar?.ordenes_trabajo?.length ?? 0) > 0 || (datosEliminar?.ventas?.length ?? 0) > 0 || (datosEliminar?.vehiculos?.length ?? 0) > 0}
              className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
            >
              {enviandoEliminar ? 'Eliminando...' : 'Eliminar cliente'}
            </button>
          </div>
        </div>
      </Modal>

      <Modal titulo={editando ? 'Editar cliente' : 'Nuevo cliente'} abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
            <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required minLength={3} className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono</label>
            <input type="text" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} placeholder="10 dígitos" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email (opcional)</label>
            <input type="text" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="ejemplo@correo.com" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Dirección (opcional)</label>
            <input type="text" value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} placeholder="Calle, colonia, ciudad..." className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">RFC (opcional)</label>
            <input type="text" value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value })} placeholder="12 o 13 caracteres" maxLength={13} className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation" />
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo={`Agregar vehículo para ${clienteParaVehiculo?.nombre || ''}`} abierto={modalVehiculo} onCerrar={() => { setModalVehiculo(false); setClienteParaVehiculo(null) }}>
        <form onSubmit={handleVehiculoSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label>
              <input type="text" value={formVehiculo.marca} onChange={(e) => setFormVehiculo({ ...formVehiculo, marca: e.target.value })} required placeholder="Ej: Nissan" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label>
              <input type="text" value={formVehiculo.modelo} onChange={(e) => setFormVehiculo({ ...formVehiculo, modelo: e.target.value })} required placeholder="Ej: Versa" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Año *</label>
              <input type="number" min={1900} max={2030} value={formVehiculo.anio} onChange={(e) => setFormVehiculo({ ...formVehiculo, anio: e.target.value })} required className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Color (opcional)</label>
              <input type="text" value={formVehiculo.color} onChange={(e) => setFormVehiculo({ ...formVehiculo, color: e.target.value })} placeholder="Ej: Blanco" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">Motor (opcional)</label>
              <input type="text" value={formVehiculo.motor} onChange={(e) => setFormVehiculo({ ...formVehiculo, motor: e.target.value })} placeholder="Ej: 1.8" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-1">VIN / Núm. serie (opcional)</label>
              <input type="text" value={formVehiculo.numero_serie} onChange={(e) => setFormVehiculo({ ...formVehiculo, numero_serie: e.target.value })} placeholder="Ej: 1HGBH41JXMN109186" className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalVehiculo(false); setClienteParaVehiculo(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviandoVehiculo} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviandoVehiculo ? 'Guardando...' : 'Agregar'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
