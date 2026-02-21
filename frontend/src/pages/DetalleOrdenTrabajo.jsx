import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import PageLoading from '../components/PageLoading'
import { normalizeDetail, showError, showSuccess } from '../utils/toast'

const formatearFecha = (f) => {
  if (!f) return '-'
  try {
    const d = new Date(f)
    return isNaN(d.getTime()) ? String(f) : d.toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return String(f)
  }
}

export default function DetalleOrdenTrabajo() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [orden, setOrden] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [autorizandoId, setAutorizandoId] = useState(null)
  const [modalCancelar, setModalCancelar] = useState(false)
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const [enviandoCancelar, setEnviandoCancelar] = useState(false)
  const [enviandoReactivar, setEnviandoReactivar] = useState(false)
  const [devolucionPorRepuesto, setDevolucionPorRepuesto] = useState({})
  const [cantidadDevolverPorRepuesto, setCantidadDevolverPorRepuesto] = useState({})

  const puedeAutorizar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  const cargar = () => {
    if (!id) return
    setLoading(true)
    setError('')
    api.get(`/ordenes-trabajo/${id}`)
      .then((res) => setOrden(res.data))
      .catch((err) => {
        const status = err?.response?.status
        const detail = normalizeDetail(err?.response?.data?.detail)
        const msg = status === 404
          ? (detail && !detail.includes('Not Found') ? detail : 'Orden no encontrada. Verifica que el ID sea correcto.')
          : (detail || 'Error al cargar la orden')
        setError(msg)
        setOrden(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [id])

  const autorizarOrden = async (autorizado) => {
    setAutorizandoId(id)
    try {
      await api.post(`/ordenes-trabajo/${id}/autorizar`, { autorizado })
      showSuccess(autorizado ? 'Orden autorizada' : 'Orden rechazada')
      cargar()
    } catch (err) {
      showError(err, 'Error al autorizar')
    } finally {
      setAutorizandoId(null)
    }
  }

  const iniciarOrden = async () => {
    try {
      await api.post(`/ordenes-trabajo/${id}/iniciar`, {})
      showSuccess('Orden iniciada')
      cargar()
    } catch (err) {
      showError(err, 'Error al iniciar')
    }
  }

  const finalizarOrden = async () => {
    try {
      await api.post(`/ordenes-trabajo/${id}/finalizar`, {})
      showSuccess('Orden finalizada')
      cargar()
    } catch (err) {
      showError(err, 'Error al finalizar')
    }
  }

  const entregarOrden = async () => {
    try {
      await api.post(`/ordenes-trabajo/${id}/entregar`, { observaciones_entrega: null })
      showSuccess('Orden entregada')
      cargar()
    } catch (err) {
      showError(err, 'Error al entregar')
    }
  }

  const marcarCotizacionEnviada = async () => {
    try {
      await api.post(`/ordenes-trabajo/marcar-cotizacion-enviada`, {}, { params: { orden_id: id } })
      showSuccess('Cotización marcada como enviada')
      cargar()
    } catch (err) {
      const status = err?.response?.status
      const detail = normalizeDetail(err?.response?.data?.detail)
      const msg = status === 404
        ? (detail && detail !== 'Not Found' ? detail : 'Ruta no encontrada. Prueba actualizar la página o hacer un nuevo deploy del backend.')
        : (detail || 'Error al marcar cotización enviada')
      showError(msg, 'Error al actualizar')
    }
  }

  const crearVenta = async () => {
    try {
      const res = await api.post(`/ventas/desde-orden/${id}`, null, { params: { requiere_factura: false } })
      const idVenta = res.data?.id_venta
      navigate(`/ventas?id=${idVenta}`)
    } catch (err) {
      showError(err, 'Error al crear venta')
    }
  }

  const descargarHojaTecnico = async () => {
    try {
      const res = await api.get(`/ordenes-trabajo/${id}/hoja-tecnico`, { responseType: 'blob' })
      const contentType = res.headers?.['content-type'] || ''
      if (contentType.includes('application/json')) {
        const text = await res.data.text()
        const json = JSON.parse(text)
        showError(json?.detail || 'Error al descargar hoja', 'Error')
        return
      }
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `hoja-tecnico-${orden?.numero_orden || id}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      let msg = 'Error al descargar hoja de trabajo'
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text()
          const json = JSON.parse(text)
          msg = json?.detail || msg
        } catch (_) {}
      } else if (err?.response?.data?.detail != null) {
        msg = typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail)
      }
      showError(msg, 'Error')
    }
  }

  const descargarCotizacion = async () => {
    try {
      const res = await api.get(`/ordenes-trabajo/${id}/cotizacion`, { responseType: 'blob' })
      const contentType = res.headers?.['content-type'] || ''
      if (contentType.includes('application/json')) {
        const text = await res.data.text()
        const json = JSON.parse(text)
        showError(json?.detail || 'Error al descargar cotización', 'Error')
        return
      }
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `cotizacion-${orden?.numero_orden || id}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      let msg = 'Error al descargar cotización'
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text()
          const json = JSON.parse(text)
          msg = json?.detail || msg
        } catch (_) {}
      } else if (err?.response?.data?.detail != null) {
        msg = typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail)
      }
      showError(msg, 'Error')
    }
  }

  const confirmarCancelar = async () => {
    if (!motivoCancelacion?.trim() || motivoCancelacion.trim().length < 10) {
      showError('El motivo debe tener al menos 10 caracteres')
      return
    }
    setEnviandoCancelar(true)
    try {
      const params = { motivo: motivoCancelacion.trim() }
      let body = null
      const repuestosConInventario = (orden?.detalles_repuesto || []).filter((r) => r.repuesto_id)
      if (orden?.estado === 'EN_PROCESO' && repuestosConInventario.length > 0 && Object.keys(devolucionPorRepuesto).length > 0) {
        body = {
          devolucion_repuestos: repuestosConInventario.map((r) => {
            const devolver = devolucionPorRepuesto[r.id] !== false
            const cant = cantidadDevolverPorRepuesto[r.id]
            const item = { id_detalle: r.id, devolver }
            if (devolver && cant != null && String(cant).trim() !== '') {
              const n = Number(cant)
              if (!isNaN(n) && n >= 0) item.cantidad_a_devolver = n
            }
            return item
          }),
        }
      } else if (orden?.estado === 'EN_PROCESO') {
        params.devolver_repuestos = true
      }
      const res = await api.post(`/ordenes-trabajo/${id}/cancelar`, body, { params })
      setModalCancelar(false)
      cargar()
      const idVentaNueva = res.data?.id_venta_nueva
      if (idVentaNueva) {
        showSuccess(`Orden cancelada. Se creó venta #${idVentaNueva} con los repuestos utilizados.`)
        navigate(`/ventas?id=${idVentaNueva}`)
      }
    } catch (err) {
      showError(err, 'Error al cancelar')
    } finally {
      setEnviandoCancelar(false)
    }
  }

  const reactivarOrden = async () => {
    setEnviandoReactivar(true)
    try {
      await api.post(`/ordenes-trabajo/${id}/reactivar`)
      showSuccess('Orden reactivada')
      cargar()
    } catch (err) {
      showError(err, 'Error al reactivar')
    } finally {
      setEnviandoReactivar(false)
    }
  }

  if (loading) return <PageLoading mensaje="Cargando orden..." />
  if (error || !orden) {
    return (
      <div className="max-w-3xl mx-auto p-8">
        <p className="text-red-600 mb-4">{error || 'Orden no encontrada'}</p>
        <Link to="/ordenes-trabajo" className="text-primary-600 hover:underline">← Volver a órdenes</Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <Link to="/ordenes-trabajo" className="text-slate-600 hover:text-slate-800 font-medium">
            ← Volver a órdenes
          </Link>
          <h1 className="text-2xl font-bold text-slate-800">Detalle — {orden.numero_orden}</h1>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <p><span className="font-medium text-slate-600">Cliente:</span> {orden.cliente?.nombre ?? orden.cliente_nombre ?? '-'}</p>
            <p><span className="font-medium text-slate-600">Vehículo:</span> {orden.vehiculo ? `${orden.vehiculo.marca} ${orden.vehiculo.modelo} ${orden.vehiculo.anio}` : orden.vehiculo_info ?? '-'}</p>
            <p>
              <span className="font-medium text-slate-600">Estado:</span>{' '}
              <span className={`px-2 py-0.5 rounded text-xs ${
                orden.estado === 'ENTREGADA' ? 'bg-blue-100 text-blue-800' :
                orden.estado === 'COMPLETADA' ? 'bg-blue-100 text-blue-800' :
                orden.estado === 'EN_PROCESO' ? 'bg-green-100 text-green-800' :
                orden.estado === 'ESPERANDO_REPUESTOS' ? 'bg-green-100 text-green-800' :
                orden.estado === 'ESPERANDO_AUTORIZACION' ? 'bg-orange-100 text-orange-800' :
                orden.estado === 'PENDIENTE' ? 'bg-orange-100 text-orange-800' :
                orden.estado === 'COTIZADA' ? 'bg-orange-100 text-orange-800' :
                orden.estado === 'COTIZADA' ? 'bg-orange-100 text-orange-800' :
                orden.estado === 'CANCELADA' ? 'bg-slate-200 text-slate-700' : 'bg-slate-100'
              }`}>
                {orden.estado || '-'}
              </span>
            </p>
            <p><span className="font-medium text-slate-600">Prioridad:</span> {orden.prioridad || '-'}</p>
            <p><span className="font-medium text-slate-600">Total:</span> ${(Number(orden.total) || 0).toFixed(2)}</p>
            <p><span className="font-medium text-slate-600">Técnico:</span> {orden.tecnico?.nombre ?? orden.tecnico?.email ?? '-'}</p>
            <p><span className="font-medium text-slate-600">Creado por:</span> {orden.usuario_creo?.nombre ?? '-'}</p>
            {orden.cliente_proporciono_refacciones && <p className="col-span-2"><span className="font-medium text-slate-600">Cliente proporcionó refacciones:</span> Sí</p>}
          </div>

          {/* Historial de confirmaciones */}
          <div className="border-t border-slate-200 pt-4">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Historial de confirmaciones</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className={`p-3 rounded-lg ${orden.usuario_cotizacion_enviada ? 'bg-amber-50 border border-amber-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Cotización enviada:</span>
                {orden.usuario_cotizacion_enviada ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_cotizacion_enviada.nombre} — {formatearFecha(orden.usuario_cotizacion_enviada.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente o no aplica</p>
                )}
              </div>
              <div className={`p-3 rounded-lg ${orden.usuario_autorizacion ? 'bg-green-50 border border-green-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Autorizar:</span>
                {orden.usuario_autorizacion ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_autorizacion.nombre} — {formatearFecha(orden.usuario_autorizacion.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente o no aplica</p>
                )}
              </div>
              <div className={`p-3 rounded-lg ${orden.usuario_inicio ? 'bg-blue-50 border border-blue-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Iniciar:</span>
                {orden.usuario_inicio ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_inicio.nombre} — {formatearFecha(orden.usuario_inicio.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente</p>
                )}
              </div>
              <div className={`p-3 rounded-lg ${orden.usuario_finalizacion ? 'bg-indigo-50 border border-indigo-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Finalizar:</span>
                {orden.usuario_finalizacion ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_finalizacion.nombre} — {formatearFecha(orden.usuario_finalizacion.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente</p>
                )}
              </div>
              <div className={`p-3 rounded-lg ${orden.usuario_creacion_venta ? 'bg-violet-50 border border-violet-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Crear venta:</span>
                {orden.usuario_creacion_venta ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_creacion_venta.nombre} — {formatearFecha(orden.usuario_creacion_venta.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente</p>
                )}
              </div>
              <div className={`p-3 rounded-lg ${orden.usuario_cobro ? 'bg-teal-50 border border-teal-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Cobrar:</span>
                {orden.usuario_cobro ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_cobro.nombre} — {formatearFecha(orden.usuario_cobro.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente</p>
                )}
              </div>
              <div className={`p-3 rounded-lg ${orden.usuario_entrega ? 'bg-emerald-50 border border-emerald-100' : 'bg-slate-50 border border-slate-100'}`}>
                <span className="font-medium text-slate-700">Entregar:</span>
                {orden.usuario_entrega ? (
                  <p className="text-slate-600 mt-1">{orden.usuario_entrega.nombre} — {formatearFecha(orden.usuario_entrega.fecha)}</p>
                ) : (
                  <p className="text-slate-500 mt-1">Pendiente</p>
                )}
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-1">Diagnóstico inicial</h3>
            <p className="text-slate-600 whitespace-pre-wrap">{orden.diagnostico_inicial?.trim() || '-'}</p>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-1">Observaciones del cliente</h3>
            <p className="text-slate-600 whitespace-pre-wrap">{orden.observaciones_cliente?.trim() || '-'}</p>
          </div>
          {orden.observaciones_tecnico?.trim() && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-1">Comentarios del técnico</h3>
              <p className="text-slate-600 whitespace-pre-wrap">{orden.observaciones_tecnico.trim()}</p>
            </div>
          )}

          {(orden.ordenes_compra?.length || 0) > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes de compra generadas</h3>
              <div className="border rounded-lg divide-y text-sm">
                {orden.ordenes_compra.map((oc) => (
                  <Link key={oc.id_orden_compra} to={`/ordenes-compra?ver=${oc.id_orden_compra}`} className="block px-3 py-2 flex justify-between items-center hover:bg-slate-50">
                    <span>{oc.numero}</span>
                    <span className="text-slate-600">${(Number(oc.total_estimado) || 0).toFixed(2)} — {oc.estado}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {(orden.detalles_servicio?.length || orden.detalles_repuesto?.length) > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Servicios y repuestos</h3>
              <div className="border rounded-lg divide-y text-sm">
                {(orden.detalles_servicio || []).map((d) => (
                  <div key={d.id} className="px-3 py-2 flex justify-between">
                    <span>🔧 {d.descripcion || `Servicio #${d.servicio_id}`} x{d.cantidad}</span>
                    <span>${(Number(d.subtotal) || 0).toFixed(2)}</span>
                  </div>
                ))}
                {(orden.detalles_repuesto || []).map((d) => {
                  const nombre = d.repuesto_nombre || d.descripcion_libre || `Repuesto #${d.repuesto_id || 'N/A'}`
                  const codigo = d.repuesto_codigo ? `[${d.repuesto_codigo}] ` : ''
                  return (
                    <div key={d.id} className="px-3 py-2 flex justify-between">
                      <span>📦 {codigo}{nombre} x{d.cantidad}</span>
                      <span>${(Number(d.subtotal) || 0).toFixed(2)}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-4 border-t border-slate-200">
            <Link to={`/ordenes-trabajo?edit=${orden.id}`} className="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm hover:bg-slate-700">
              Editar
            </Link>
            {orden.estado === 'PENDIENTE' && !orden.usuario_autorizacion && (user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (
              <button onClick={marcarCotizacionEnviada} className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600" title="Marcar que ya enviaste la cotización al cliente">
                Marcar cotización enviada
              </button>
            )}
            {orden.estado !== 'CANCELADA' && (
              <>
                <button onClick={descargarCotizacion} className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm hover:bg-orange-700" title="Cotización (naranja)">
                  Cotización PDF
                </button>
                <button onClick={descargarHojaTecnico} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700" title="Hoja para técnico (verde)">
                  Hoja técnico PDF
                </button>
              </>
            )}
            {puedeAutorizar && (orden.estado === 'ESPERANDO_AUTORIZACION' || (orden.estado === 'PENDIENTE' && orden.requiere_autorizacion && !orden.autorizado)) && (
              <>
                <button onClick={() => autorizarOrden(true)} disabled={autorizandoId} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">Autorizar</button>
                <button onClick={() => autorizarOrden(false)} disabled={autorizandoId} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50">Rechazar</button>
              </>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && (orden.estado === 'PENDIENTE' || orden.estado === 'COTIZADA') && (
              <button onClick={iniciarOrden} disabled={!orden.tecnico_id && user?.rol === 'ADMIN'} title={!orden.tecnico_id ? 'Asigna un técnico antes (Editar)' : ''} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50">
                Iniciar
              </button>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && orden.estado === 'EN_PROCESO' && (
              <button onClick={finalizarOrden} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Finalizar</button>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && orden.estado === 'COMPLETADA' && (
              (() => {
                const sinVenta = !orden.id_venta
                const ventaNoPagada = orden.id_venta && (orden.venta_saldo_pendiente ?? 0) > 0
                const bloquearEntregar = sinVenta || ventaNoPagada
                const mensaje = sinVenta
                  ? 'Debes crear la venta (💰) y pagarla antes de entregar.'
                  : 'La venta aún no ha sido pagada. Registra el pago en menú Ventas antes de entregar.'
                return (
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={entregarOrden}
                      disabled={bloquearEntregar}
                      title={bloquearEntregar ? mensaje : ''}
                      className={`px-4 py-2 rounded-lg text-sm ${bloquearEntregar ? 'bg-slate-400 cursor-not-allowed text-white' : 'bg-green-600 text-white hover:bg-green-700'}`}
                    >
                      Entregar
                    </button>
                    {bloquearEntregar && (
                      <p className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">{mensaje}</p>
                    )}
                  </div>
                )
              })()
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (orden.estado === 'ENTREGADA' || orden.estado === 'COMPLETADA') && (
              orden.id_venta ? (
                <button onClick={() => navigate(`/ventas?id=${orden.id_venta}`)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">💰 Cobrar en venta</button>
              ) : (
                <button onClick={crearVenta} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">💰 Crear venta</button>
              )
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && orden.estado !== 'ENTREGADA' && orden.estado !== 'CANCELADA' && (
              <button
                onClick={() => {
                  const repuestos = (orden.detalles_repuesto || []).filter((r) => r.repuesto_id)
                  const map = {}
                  repuestos.forEach((r) => { map[r.id] = true })
                  setDevolucionPorRepuesto(map)
                  setCantidadDevolverPorRepuesto({})
                  setModalCancelar(true)
                }}
                className="px-4 py-2 border border-red-300 text-red-600 rounded-lg text-sm hover:bg-red-50"
              >
                Cancelar orden
              </button>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && orden.estado === 'CANCELADA' && (
              <button onClick={reactivarOrden} disabled={enviandoReactivar} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">
                {enviandoReactivar ? 'Reactivando...' : 'Reactivar orden'}
              </button>
            )}
          </div>
        </div>
      </div>

      <Modal titulo="Cancelar orden" abierto={modalCancelar} onCerrar={() => { setModalCancelar(false); setDevolucionPorRepuesto({}); setCantidadDevolverPorRepuesto({}) }}>
        <div className="space-y-4">
          <p className="text-slate-600">Indica el motivo de la cancelación (mínimo 10 caracteres).</p>
          <textarea value={motivoCancelacion} onChange={(e) => setMotivoCancelacion(e.target.value)} rows={3} placeholder="Motivo..." className="w-full px-4 py-2 border border-slate-300 rounded-lg" minLength={10} />
          {orden?.estado === 'EN_PROCESO' && (orden?.detalles_repuesto || []).filter((r) => r.repuesto_id).length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
              <p className="text-sm font-medium text-amber-900">Indica por cada repuesto: ¿devolver al inventario o se utilizó (cobrar)?</p>
              <div className="space-y-2">
                {(orden.detalles_repuesto || []).filter((r) => r.repuesto_id).map((r) => {
                  const devolver = devolucionPorRepuesto[r.id] !== false
                  const cantDec = Number(r.cantidad) % 1 !== 0
                  return (
                    <div key={r.id} className="flex flex-wrap items-center gap-2 p-2 bg-white rounded border border-amber-100">
                      <label className="flex items-center gap-2 cursor-pointer flex-1 min-w-[180px]">
                        <input
                          type="checkbox"
                          checked={devolver}
                          onChange={(e) => setDevolucionPorRepuesto((prev) => ({ ...prev, [r.id]: e.target.checked }))}
                        />
                        <span className="text-sm text-amber-900">{r.repuesto_codigo ? `[${r.repuesto_codigo}] ` : ''}{r.repuesto_nombre || `Repuesto #${r.repuesto_id}`} x{r.cantidad}</span>
                      </label>
                      {devolver ? <span className="text-xs text-green-700">→ Inventario</span> : <span className="text-xs text-amber-700 font-medium">→ Se cobrará</span>}
                      {devolver && cantDec && (
                        <div className="flex items-center gap-1">
                          <label className="text-xs text-slate-600">Cant. a devolver:</label>
                          <input
                            type="number"
                            min={0}
                            max={Number(r.cantidad) || 1}
                            step={0.001}
                            placeholder={String(r.cantidad)}
                            value={cantidadDevolverPorRepuesto[r.id] ?? ''}
                            onChange={(e) => setCantidadDevolverPorRepuesto((prev) => ({ ...prev, [r.id]: e.target.value }))}
                            className="w-20 px-2 py-1 text-sm border border-slate-300 rounded"
                          />
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
              {Object.values(devolucionPorRepuesto).some((v) => v === false) && (
                <p className="text-xs text-amber-800">Los repuestos marcados como utilizados se cobrarán al cliente.</p>
              )}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCancelar(false)} className="px-4 py-2 border border-slate-300 rounded-lg">Cerrar</button>
            <button type="button" onClick={confirmarCancelar} disabled={enviandoCancelar || !motivoCancelacion?.trim() || motivoCancelacion.trim().length < 10} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
              {enviandoCancelar ? 'Cancelando...' : 'Confirmar cancelación'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
