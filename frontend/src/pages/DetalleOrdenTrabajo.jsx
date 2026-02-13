import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { normalizeDetail, showError } from '../utils/toast'

const formatearFecha = (f) => {
  if (!f) return '-'
  try {
    const d = new Date(f)
    return d.toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })
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

  const puedeAutorizar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  const cargar = () => {
    if (!id) return
    setLoading(true)
    api.get(`/ordenes-trabajo/${id}`)
      .then((res) => setOrden(res.data))
      .catch((err) => {
        setError(normalizeDetail(err.response?.data?.detail) || 'Error al cargar la orden')
        setOrden(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [id])

  const autorizarOrden = async (autorizado) => {
    setAutorizandoId(id)
    try {
      await api.post(`/ordenes-trabajo/${id}/autorizar`, { autorizado })
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
      cargar()
    } catch (err) {
      showError(err, 'Error al iniciar')
    }
  }

  const finalizarOrden = async () => {
    try {
      await api.post(`/ordenes-trabajo/${id}/finalizar`, {})
      cargar()
    } catch (err) {
      showError(err, 'Error al finalizar')
    }
  }

  const entregarOrden = async () => {
    try {
      await api.post(`/ordenes-trabajo/${id}/entregar`, { observaciones_entrega: null })
      cargar()
    } catch (err) {
      showError(err, 'Error al entregar')
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

  const confirmarCancelar = async () => {
    if (!motivoCancelacion?.trim() || motivoCancelacion.trim().length < 10) {
      showError('El motivo debe tener al menos 10 caracteres')
      return
    }
    setEnviandoCancelar(true)
    try {
      await api.post(`/ordenes-trabajo/${id}/cancelar`, null, { params: { motivo: motivoCancelacion.trim() } })
      setModalCancelar(false)
      cargar()
    } catch (err) {
      showError(err, 'Error al cancelar')
    } finally {
      setEnviandoCancelar(false)
    }
  }

  if (loading) return <p className="p-8 text-slate-500">Cargando...</p>
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
                orden.estado === 'ENTREGADA' ? 'bg-green-100 text-green-800' :
                orden.estado === 'COMPLETADA' ? 'bg-blue-100 text-blue-800' :
                orden.estado === 'EN_PROCESO' ? 'bg-amber-100 text-amber-800' :
                orden.estado === 'ESPERANDO_AUTORIZACION' ? 'bg-orange-100 text-orange-800' :
                orden.estado === 'CANCELADA' ? 'bg-slate-200 text-slate-700' : 'bg-slate-100'
              }`}>
                {orden.estado || '-'}
              </span>
            </p>
            <p><span className="font-medium text-slate-600">Prioridad:</span> {orden.prioridad || '-'}</p>
            <p><span className="font-medium text-slate-600">Total:</span> ${(Number(orden.total) || 0).toFixed(2)}</p>
            <p><span className="font-medium text-slate-600">Técnico:</span> {orden.tecnico?.nombre ?? orden.tecnico?.email ?? '-'}</p>
            {orden.cliente_proporciono_refacciones && <p className="col-span-2"><span className="font-medium text-slate-600">Cliente proporcionó refacciones:</span> Sí</p>}
          </div>

          {/* Historial de confirmaciones */}
          <div className="border-t border-slate-200 pt-4">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Historial de confirmaciones</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
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
                  const nombre = d.repuesto_nombre || `Repuesto #${d.repuesto_id}`
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
            {puedeAutorizar && (orden.estado === 'ESPERANDO_AUTORIZACION' || (orden.estado === 'PENDIENTE' && orden.requiere_autorizacion && !orden.autorizado)) && (
              <>
                <button onClick={() => autorizarOrden(true)} disabled={autorizandoId} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">Autorizar</button>
                <button onClick={() => autorizarOrden(false)} disabled={autorizandoId} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50">Rechazar</button>
              </>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && orden.estado === 'PENDIENTE' && (
              <button onClick={iniciarOrden} disabled={!orden.tecnico_id && user?.rol === 'ADMIN'} title={!orden.tecnico_id ? 'Asigna un técnico antes (Editar)' : ''} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50">
                Iniciar
              </button>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && orden.estado === 'EN_PROCESO' && (
              <button onClick={finalizarOrden} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Finalizar</button>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && orden.estado === 'COMPLETADA' && (
              <button onClick={entregarOrden} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">Entregar</button>
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (orden.estado === 'ENTREGADA' || orden.estado === 'COMPLETADA') && (
              orden.id_venta ? (
                <button onClick={() => navigate(`/ventas?id=${orden.id_venta}`)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">💰 Cobrar en venta</button>
              ) : (
                <button onClick={crearVenta} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">💰 Crear venta</button>
              )
            )}
            {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && orden.estado !== 'ENTREGADA' && orden.estado !== 'CANCELADA' && (
              <button onClick={() => setModalCancelar(true)} className="px-4 py-2 border border-red-300 text-red-600 rounded-lg text-sm hover:bg-red-50">Cancelar orden</button>
            )}
          </div>
        </div>
      </div>

      <Modal titulo="Cancelar orden" abierto={modalCancelar} onCerrar={() => setModalCancelar(false)}>
        <div className="space-y-4">
          <p className="text-slate-600">Indica el motivo de la cancelación (mínimo 10 caracteres).</p>
          <textarea value={motivoCancelacion} onChange={(e) => setMotivoCancelacion(e.target.value)} rows={3} placeholder="Motivo..." className="w-full px-4 py-2 border border-slate-300 rounded-lg" minLength={10} />
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
