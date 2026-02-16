import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { aNumero, aEntero } from '../utils/numeros'
import { normalizeDetail, showError, showSuccess } from '../utils/toast'

export default function OrdenesTrabajo() {
  const { user } = useAuth()
  const [ordenes, setOrdenes] = useState([])
  const [loading, setLoading] = useState(true)
  const [tecnicos, setTecnicos] = useState([])
  const [servicios, setServicios] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const limit = 20
  const puedeAutorizar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'
  const [autorizandoId, setAutorizandoId] = useState(null)
  const [filtroEstado, setFiltroEstado] = useState('')
  const [buscar, setBuscar] = useState('')
  const [modalCancelar, setModalCancelar] = useState(false)
  const [ordenACancelar, setOrdenACancelar] = useState(null)
  const [ordenACancelarRepuestos, setOrdenACancelarRepuestos] = useState([])
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const [devolverRepuestos, setDevolverRepuestos] = useState(false)
  const [motivoNoDevolucion, setMotivoNoDevolucion] = useState('')
  const [enviandoCancelar, setEnviandoCancelar] = useState(false)
  const [modalEditar, setModalEditar] = useState(false)
  const [ordenEditando, setOrdenEditando] = useState(null)
  const [formEditar, setFormEditar] = useState({ tecnico_id: '', prioridad: 'NORMAL', fecha_promesa: '', diagnostico_inicial: '', observaciones_cliente: '', requiere_autorizacion: false, cliente_proporciono_refacciones: false, servicios: [], repuestos: [] })
  const [detalleActualEditar, setDetalleActualEditar] = useState({ tipo: 'SERVICIO', id_item: '', cantidad: 1, precio_unitario: 0 })
  const [enviandoEditar, setEnviandoEditar] = useState(false)
  const [modalCrearVenta, setModalCrearVenta] = useState(false)
  const [ordenParaVenta, setOrdenParaVenta] = useState(null)
  const [requiereFacturaVenta, setRequiereFacturaVenta] = useState(false)
  const [enviandoCrearVenta, setEnviandoCrearVenta] = useState(false)
  const [config, setConfig] = useState({ iva_porcentaje: 8 })
  const [errorCargar, setErrorCargar] = useState('')
  const [errorConfig, setErrorConfig] = useState('')
  const [errorModal, setErrorModal] = useState('')
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    api.get('/config')
      .then((r) => { setConfig(r.data || { iva_porcentaje: 8 }); setErrorConfig('') })
      .catch((err) => { setErrorConfig(normalizeDetail(err.response?.data?.detail) || 'No se pudo cargar configuración') })
  }, [])

  const cargar = () => {
    setErrorCargar('')
    const params = { skip: (pagina - 1) * limit, limit }
    if (filtroEstado) params.estado = filtroEstado === 'EN_PROCESO_FINALIZAR' ? 'EN_PROCESO' : filtroEstado
    if (buscar.trim()) params.buscar = buscar.trim()
    api.get('/ordenes-trabajo/', { params })
      .then((res) => {
        const d = res.data
        setOrdenes(d?.ordenes ?? [])
        setTotalPaginas(d?.total_paginas ?? 1)
      })
      .catch((err) => {
        setOrdenes([])
        setErrorCargar(normalizeDetail(err.response?.data?.detail) || 'Error al cargar órdenes')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, filtroEstado, buscar])

  const editId = searchParams.get('edit')
  useEffect(() => {
    if (editId && ordenes.length > 0 && !modalEditar) {
      const o = ordenes.find((x) => String(x.id) === editId)
      if (o) {
        abrirEditar(o)
        setSearchParams({})
      }
    }
  }, [editId, ordenes])

  useEffect(() => {
    if (modalEditar) {
      setErrorModal('')
      if (tecnicos.length === 0) {
        api.get('/usuarios/')
          .then((r) => {
            const users = Array.isArray(r.data) ? r.data : []
            setTecnicos(users.filter((u) => u.rol === 'TECNICO'))
          })
          .catch((err) => { setErrorModal(normalizeDetail(err.response?.data?.detail) || 'Error al cargar técnicos') })
      }
      if (ordenEditando?.estado === 'PENDIENTE' && servicios.length === 0) {
        api.get('/servicios/', { params: { limit: 100 } })
          .then((r) => setServicios(r.data?.servicios ?? r.data ?? []))
          .catch((err) => { setErrorModal(normalizeDetail(err.response?.data?.detail) || 'Error al cargar servicios') })
        api.get('/repuestos/', { params: { limit: 500 } })
          .then((r) => {
            const d = r.data
            setRepuestos(Array.isArray(d) ? d : d?.items ?? d?.repuestos ?? [])
          })
          .catch((err) => { setErrorModal(normalizeDetail(err.response?.data?.detail) || 'Error al cargar repuestos') })
      }
    }
  }, [modalEditar, ordenEditando?.estado])

  const autorizarOrden = async (ordenId, autorizado) => {
    setAutorizandoId(ordenId)
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/autorizar`, { autorizado })
      cargar()
    } catch (err) {
      showError(err, 'Error al autorizar')
    } finally {
      setAutorizandoId(null)
    }
  }

  const abrirDetalle = (o) => {
    navigate(`/ordenes-trabajo/${o.id}`)
  }

  const iniciarOrden = async (ordenId) => {
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/iniciar`, {})
      cargar()
    } catch (err) {
      showError(err, 'Error al iniciar')
    }
  }

  const finalizarOrden = async (ordenId) => {
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/finalizar`, {})
      cargar()
    } catch (err) {
      showError(err, 'Error al finalizar')
    }
  }

  const entregarOrden = async (ordenId) => {
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/entregar`, {})
      cargar()
    } catch (err) {
      showError(err, 'Error al entregar')
    }
  }

  const abrirModalCrearVenta = (o) => {
    setOrdenParaVenta(o)
    setRequiereFacturaVenta(false)
    setModalCrearVenta(true)
  }

  const confirmarCrearVenta = async () => {
    if (!ordenParaVenta) return
    setEnviandoCrearVenta(true)
    try {
      const res = await api.post(`/ventas/desde-orden/${ordenParaVenta.id}`, null, { params: { requiere_factura: requiereFacturaVenta } })
      setModalCrearVenta(false)
      setOrdenParaVenta(null)
      cargar()
      const idVenta = res.data?.id_venta
      if (idVenta) {
        navigate(`/ventas?id=${idVenta}`)
      }
      showSuccess(`Venta #${idVenta} creada. Total: $${(res.data?.total ?? 0).toFixed(2)}`)
    } catch (err) {
      showError(err, 'Error al crear venta')
    } finally {
      setEnviandoCrearVenta(false)
    }
  }

  const abrirModalCancelar = async (o) => {
    setOrdenACancelar(o)
    setMotivoCancelacion('')
    setDevolverRepuestos(false)
    setMotivoNoDevolucion('')
    setOrdenACancelarRepuestos([])
    setModalCancelar(true)
    if (o?.estado === 'EN_PROCESO') {
      try {
        const res = await api.get(`/ordenes-trabajo/${o.id}`)
        const datos = res.data
        if (!datos.cliente_proporciono_refacciones && (datos.detalles_repuesto?.length || 0) > 0) {
          setOrdenACancelarRepuestos(datos.detalles_repuesto || [])
        }
      } catch {
        setOrdenACancelarRepuestos([])
      }
    }
  }

  const abrirEditar = async (orden) => {
    setOrdenEditando(orden)
    const esPendiente = orden.estado === 'PENDIENTE'
    let datos = orden
    if (esPendiente) {
      try {
        const res = await api.get(`/ordenes-trabajo/${orden.id}`)
        datos = res.data
      } catch {
        datos = orden
      }
    }
    const fp = datos.fecha_promesa
    const fpStr = typeof fp === 'string' ? fp.slice(0, 16) : ''
    const serviciosMap = (datos.detalles_servicio || []).map((d) => ({ servicio_id: d.servicio_id, cantidad: d.cantidad || 1, precio_unitario: d.precio_unitario ?? null, descripcion: d.descripcion || null }))
    const repuestosMap = (datos.detalles_repuesto || []).map((d) => ({ repuesto_id: d.repuesto_id, cantidad: d.cantidad || 1, precio_unitario: d.precio_unitario ?? null }))
    setFormEditar({
      tecnico_id: datos.tecnico_id ? String(datos.tecnico_id) : '',
      prioridad: datos.prioridad || 'NORMAL',
      fecha_promesa: fpStr || '',
      diagnostico_inicial: datos.diagnostico_inicial || '',
      observaciones_cliente: datos.observaciones_cliente || '',
      requiere_autorizacion: !!datos.requiere_autorizacion,
      cliente_proporciono_refacciones: !!datos.cliente_proporciono_refacciones,
      servicios: serviciosMap,
      repuestos: repuestosMap
    })
    setDetalleActualEditar({ tipo: 'SERVICIO', id_item: '', cantidad: 1, precio_unitario: 0 })
    setModalEditar(true)
  }

  const handleEditarSubmit = async (e) => {
    e.preventDefault()
    if (!ordenEditando) return
    const esPendiente = ordenEditando.estado === 'PENDIENTE'
    const diag = (formEditar.diagnostico_inicial || '').trim()
    const obs = (formEditar.observaciones_cliente || '').trim()
    if (esPendiente) {
      if (!diag) { showError('El diagnóstico inicial es obligatorio.'); return }
      if (!obs) { showError('Las observaciones del cliente son obligatorias.'); return }
      if (!formEditar.servicios?.length && !formEditar.repuestos?.length) { showError('Debes agregar al menos un producto o servicio.'); return }
      if (requiereAdvertenciaRepuestosEditar && !window.confirm('Hay servicios que suelen requerir repuestos, pero no has agregado repuestos ni marcado "Cliente proporcionó refacciones". ¿Continuar de todos modos?')) return
    }
    setEnviandoEditar(true)
    try {
      const payload = {
        tecnico_id: formEditar.tecnico_id ? aEntero(formEditar.tecnico_id) : null,
        prioridad: formEditar.prioridad,
        fecha_promesa: formEditar.fecha_promesa || null
      }
      if (esPendiente) {
        payload.diagnostico_inicial = diag || null
        payload.observaciones_cliente = obs || null
        payload.requiere_autorizacion = formEditar.requiere_autorizacion
        payload.cliente_proporciono_refacciones = formEditar.cliente_proporciono_refacciones
        payload.servicios = (formEditar.servicios || []).map((s) => ({ servicio_id: s.servicio_id, cantidad: s.cantidad || 1, precio_unitario: s.precio_unitario ?? null, descripcion: s.descripcion || null }))
        payload.repuestos = (formEditar.repuestos || []).map((r) => ({ repuesto_id: r.repuesto_id, cantidad: r.cantidad || 1, precio_unitario: r.precio_unitario ?? null }))
      }
      await api.put(`/ordenes-trabajo/${ordenEditando.id}`, payload)
      cargar()
      setModalEditar(false)
      setOrdenEditando(null)
    } catch (err) {
      showError(err, 'Error al actualizar')
    } finally {
      setEnviandoEditar(false)
    }
  }

  const hayServiciosEditarQueRequierenRepuestos = (formEditar.servicios || []).some((fs) => {
    const s = servicios.find(x => (x.id ?? x.id_servicio) === fs.servicio_id)
    return !!s?.requiere_repuestos
  })
  const requiereAdvertenciaRepuestosEditar = hayServiciosEditarQueRequierenRepuestos && (formEditar.repuestos?.length || 0) === 0 && !formEditar.cliente_proporciono_refacciones
  const servicioEditarSeleccionadoRequiereRepuestos = detalleActualEditar.tipo === 'SERVICIO' && detalleActualEditar.id_item && (() => {
    const s = servicios.find(x => (x.id ?? x.id_servicio) === aEntero(detalleActualEditar.id_item))
    return !!s?.requiere_repuestos
  })()

  const agregarDetalleEditar = () => {
    if (!detalleActualEditar.id_item || aEntero(detalleActualEditar.cantidad, 1) < 1) return
    const idItem = aEntero(detalleActualEditar.id_item)
    const cantidad = aEntero(detalleActualEditar.cantidad, 1)
    const precio = Number(detalleActualEditar.precio_unitario) || 0
    if (detalleActualEditar.tipo === 'SERVICIO') {
      const s = servicios.find((x) => (x.id ?? x.id_servicio) === idItem)
      if (s?.requiere_repuestos && (formEditar.repuestos?.length || 0) === 0 && !formEditar.cliente_proporciono_refacciones) {
        if (!window.confirm(`"${s.nombre}" suele requerir repuestos. ¿Deseas agregar repuestos después o el cliente los proporciona? ¿Agregar el servicio de todos modos?`)) return
      }
      setFormEditar({ ...formEditar, servicios: [...(formEditar.servicios || []), { servicio_id: idItem, cantidad, precio_unitario: precio || (s ? Number(s.precio_base) : 0), descripcion: s?.nombre || null }] })
    } else {
      const r = repuestos.find((x) => (x.id_repuesto ?? x.id) === idItem)
      setFormEditar({ ...formEditar, repuestos: [...(formEditar.repuestos || []), { repuesto_id: idItem, cantidad, precio_unitario: precio || (r ? Number(r.precio_venta) : 0) }] })
    }
    setDetalleActualEditar({ tipo: detalleActualEditar.tipo, id_item: '', cantidad: 1, precio_unitario: 0 })
  }

  const quitarServicioEditar = (idx) => setFormEditar({ ...formEditar, servicios: (formEditar.servicios || []).filter((_, i) => i !== idx) })
  const quitarRepuestoEditar = (idx) => setFormEditar({ ...formEditar, repuestos: (formEditar.repuestos || []).filter((_, i) => i !== idx) })

  const puedeEditar = (o) => o.estado !== 'ENTREGADA' && o.estado !== 'CANCELADA'

  const confirmarCancelar = async () => {
    if (!ordenACancelar) return
    if (!motivoCancelacion.trim() || motivoCancelacion.trim().length < 10) {
      showError('El motivo debe tener al menos 10 caracteres.')
      return
    }
    setEnviandoCancelar(true)
    try {
      const params = { motivo: motivoCancelacion.trim() }
      if (ordenACancelar.estado === 'EN_PROCESO') {
        params.devolver_repuestos = devolverRepuestos
        if (!devolverRepuestos && motivoNoDevolucion) params.motivo_no_devolucion = motivoNoDevolucion
      }
      await api.post(`/ordenes-trabajo/${ordenACancelar.id}/cancelar`, null, { params })
      cargar()
      setModalCancelar(false)
      setOrdenACancelar(null)
      setOrdenACancelarRepuestos([])
      setMotivoCancelacion('')
      setDevolverRepuestos(false)
      setMotivoNoDevolucion('')
      setModalDetalle(false)
    } catch (err) {
      showError(err, 'Error al cancelar')
    } finally {
      setEnviandoCancelar(false)
    }
  }

  if (loading) return <div className="py-6"><p className="text-slate-500">Cargando...</p></div>
  if (errorCargar) return <div className="p-4 rounded-lg bg-red-50 text-red-700"><p>{errorCargar}</p><button onClick={cargar} className="mt-2 min-h-[44px] px-4 py-2 bg-red-100 rounded-lg hover:bg-red-200 active:bg-red-300 text-sm touch-manipulation">Reintentar</button></div>

  return (
    <div className="min-h-0">
      {errorConfig && (
        <div className="p-3 rounded-lg bg-amber-50 text-amber-800 mb-4 text-sm">
          {errorConfig}. Se usará IVA 8% por defecto.
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Órdenes de trabajo</h1>
        {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (
          <button type="button" onClick={() => navigate('/ordenes-trabajo/nueva')} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation self-start sm:self-center">Nueva orden</button>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs text-slate-500 mb-1">Buscar</label>
            <input type="text" placeholder="Por número..." value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div className="min-w-[160px] flex-1 sm:flex-initial">
            <label className="block text-xs text-slate-500 mb-1">Estado</label>
            <select value={filtroEstado} onChange={(e) => { setFiltroEstado(e.target.value); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
              <option value="">Todos los estados</option>
              <option value="PENDIENTE">Pendiente</option>
              <option value="COTIZADA">Cotizada</option>
              <option value="COTIZADA">Cotizada</option>
              <option value="EN_PROCESO">En proceso</option>
              <option value="EN_PROCESO_FINALIZAR">Pend. finalizar</option>
              <option value="ESPERANDO_REPUESTOS">Esperando repuestos</option>
              <option value="ESPERANDO_AUTORIZACION">Esperando autorización</option>
              <option value="COMPLETADA">Completada</option>
              <option value="ENTREGADA">Entregada</option>
              <option value="CANCELADA">Cancelada</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nº</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Cliente</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Vehículo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Estado</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Total</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {ordenes.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">No hay órdenes</td></tr>
            ) : (
              ordenes.map((o) => (
                <tr key={o.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{o.numero_orden}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{o.cliente_nombre ?? o.cliente?.nombre ?? '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{o.vehiculo_info ?? (o.vehiculo ? `${o.vehiculo.marca} ${o.vehiculo.modelo}` : '-')}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      o.estado === 'ENTREGADA' ? 'bg-blue-100 text-blue-800' :
                      o.estado === 'COMPLETADA' ? 'bg-blue-100 text-blue-800' :
                      o.estado === 'EN_PROCESO' ? 'bg-green-100 text-green-800' :
                      o.estado === 'ESPERANDO_REPUESTOS' ? 'bg-green-100 text-green-800' :
                      o.estado === 'ESPERANDO_AUTORIZACION' ? 'bg-orange-100 text-orange-800' :
                      o.estado === 'PENDIENTE' ? 'bg-orange-100 text-orange-800' :
                      o.estado === 'COTIZADA' ? 'bg-orange-100 text-orange-800' :
                      o.estado === 'COTIZADA' ? 'bg-orange-100 text-orange-800' :
                      o.estado === 'CANCELADA' ? 'bg-slate-200 text-slate-700' :
                      'bg-slate-100 text-slate-800'
                    }`}>
                      {o.estado || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium">${(o.total ?? 0).toFixed(2)}</td>
                  <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                    <div className="flex gap-1 justify-end flex-wrap">
                      <button type="button" onClick={() => abrirDetalle(o)} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation" title="Ver detalle">📋</button>
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA' || (user?.rol === 'TECNICO' && o.tecnico_id === user?.id_usuario)) && puedeEditar(o) && (
                        <button type="button" onClick={() => abrirEditar(o)} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation" title={!o.tecnico_id ? 'Debes agregar técnico' : 'Editar'}>✏️</button>
                      )}
                      {puedeAutorizar && (o.estado === 'ESPERANDO_AUTORIZACION' || (o.estado === 'PENDIENTE' && o.requiere_autorizacion && !o.autorizado)) && (
                        <>
                          <button type="button" onClick={() => autorizarOrden(o.id, true)} disabled={autorizandoId === o.id} className="min-h-[36px] px-2 py-1 text-sm text-green-600 hover:text-green-700 active:bg-green-50 rounded touch-manipulation">✓</button>
                          <button type="button" onClick={() => autorizarOrden(o.id, false)} disabled={autorizandoId === o.id} className="min-h-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation">✗</button>
                        </>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && o.estado === 'PENDIENTE' && (
                        <button type="button" onClick={() => iniciarOrden(o.id)} disabled={!o.tecnico_id && user?.rol === 'ADMIN'} title={!o.tecnico_id && user?.rol === 'ADMIN' ? 'Asigna técnico (Editar)' : ''} className={`min-h-[36px] px-2 py-1 text-sm rounded touch-manipulation ${!o.tecnico_id && user?.rol === 'ADMIN' ? 'text-slate-400 cursor-not-allowed' : 'text-primary-600 hover:text-primary-700 active:bg-primary-50'}`}>Iniciar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && o.estado === 'EN_PROCESO' && (
                        <button type="button" onClick={() => finalizarOrden(o.id)} className="min-h-[36px] px-2 py-1 text-sm text-blue-600 hover:text-blue-700 active:bg-blue-50 rounded touch-manipulation">Finalizar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && o.estado === 'COMPLETADA' && (
                        <button type="button" onClick={() => entregarOrden(o.id)} className="min-h-[36px] px-2 py-1 text-sm text-green-600 hover:text-green-700 active:bg-green-50 rounded touch-manipulation">Entregar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (o.estado === 'ENTREGADA' || o.estado === 'COMPLETADA') && (
                        o.id_venta ? (
                          <button type="button" onClick={() => navigate(`/ventas?id=${o.id_venta}`)} className="min-h-[36px] px-2 py-1 text-sm text-emerald-600 hover:text-emerald-700 active:bg-emerald-50 rounded touch-manipulation">💰</button>
                        ) : (
                          <button type="button" onClick={() => abrirModalCrearVenta(o)} className="min-h-[36px] px-2 py-1 text-sm text-emerald-600 hover:text-emerald-700 active:bg-emerald-50 rounded touch-manipulation">💰</button>
                        )
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && o.estado !== 'ENTREGADA' && o.estado !== 'CANCELADA' && (
                        <button type="button" onClick={() => abrirModalCancelar(o)} className="min-h-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation">Cancelar</button>
                      )}
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
          <p className="text-sm text-slate-600 order-2 sm:order-1">Pág. {pagina} de {totalPaginas}</p>
          <div className="flex gap-2 justify-center sm:justify-end order-1 sm:order-2">
            <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 touch-manipulation active:bg-slate-50">Anterior</button>
            <span className="min-h-[44px] px-3 py-2 flex items-center justify-center text-sm text-slate-700">{pagina} / {totalPaginas}</span>
            <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 touch-manipulation active:bg-slate-50">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={`Editar orden — ${ordenEditando?.numero_orden || ''}`} abierto={modalEditar} onCerrar={() => { setModalEditar(false); setOrdenEditando(null); setErrorModal('') }}>
        <form onSubmit={handleEditarSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto">
          {errorModal && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{errorModal}</div>}
          {ordenEditando?.estado === 'PENDIENTE' ? (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Diagnóstico inicial *</label>
                <textarea value={formEditar.diagnostico_inicial} onChange={(e) => setFormEditar({ ...formEditar, diagnostico_inicial: e.target.value })} rows={2} className="w-full px-4 py-3 min-h-[72px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" placeholder="Qué reporta el cliente o lo detectado en revisión inicial" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones del cliente *</label>
                <textarea value={formEditar.observaciones_cliente} onChange={(e) => setFormEditar({ ...formEditar, observaciones_cliente: e.target.value })} rows={2} className="w-full px-4 py-3 min-h-[72px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" placeholder="Preferencias, restricciones, urgencias" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Agregar producto o servicio</label>
                <div className="flex gap-2 flex-wrap items-end">
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Tipo</label>
                    <select value={detalleActualEditar.tipo} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, tipo: e.target.value, id_item: '' })} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
                      <option value="SERVICIO">Servicio</option>
                      <option value="PRODUCTO">Producto</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">{detalleActualEditar.tipo === 'SERVICIO' ? 'Servicio' : 'Producto'}</label>
                    <select value={detalleActualEditar.id_item} onChange={(e) => {
                      const id = e.target.value
                      const idNum = aEntero(id)
                      const item = detalleActualEditar.tipo === 'SERVICIO' ? servicios.find((s) => (s.id ?? s.id_servicio) === idNum) : repuestos.find((r) => (r.id_repuesto ?? r.id) === idNum)
                      const precio = item ? (detalleActualEditar.tipo === 'SERVICIO' ? Number(item.precio_base) : Number(item.precio_venta)) : 0
                      setDetalleActualEditar({ ...detalleActualEditar, id_item: id, precio_unitario: precio })
                    }} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation min-w-[140px]">
                      <option value="">Seleccionar...</option>
                      {(detalleActualEditar.tipo === 'SERVICIO' ? servicios : repuestos).map((x) => (
                        <option key={x.id ?? x.id_servicio ?? x.id_repuesto} value={x.id ?? x.id_servicio ?? x.id_repuesto}>{x.codigo || ''} {x.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Cant.</label>
                    <input type="number" min={1} value={detalleActualEditar.cantidad} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, cantidad: aEntero(e.target.value, 1) })} className="w-14 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Precio</label>
                    <input type="number" min={0} step={0.01} value={detalleActualEditar.precio_unitario || ''} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, precio_unitario: aNumero(e.target.value) })} className="w-18 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                  </div>
                  <button type="button" onClick={agregarDetalleEditar} disabled={!detalleActualEditar.id_item} className="min-h-[44px] px-3 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300 active:bg-slate-400 disabled:opacity-50 touch-manipulation">+ Agregar</button>
                </div>
                {servicioEditarSeleccionadoRequiereRepuestos && (
                  <p className="text-xs text-amber-700 mt-1 bg-amber-50 px-2 py-1 rounded">⚠️ Este servicio suele requerir repuestos. Considera agregar los repuestos necesarios o marcar "Cliente proporcionó refacciones" si aplica.</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Productos y servicios agregados *</label>
                {requiereAdvertenciaRepuestosEditar && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg mb-2">⚠️ Hay servicios que suelen requerir repuestos. Agrega los repuestos necesarios o marca "Cliente proporcionó refacciones" si el cliente los trae.</p>
                )}
                <div className="border border-slate-200 rounded-lg divide-y max-h-28 overflow-y-auto text-sm">
                  {(formEditar.servicios || []).length === 0 && (formEditar.repuestos || []).length === 0 ? (
                    <p className="px-3 py-3 text-slate-500 text-center">Ninguno. Agrega al menos uno.</p>
                  ) : (
                    <>
                      {(formEditar.servicios || []).map((s, i) => {
                        const serv = servicios.find((x) => (x.id ?? x.id_servicio) === s.servicio_id)
                        return (
                          <div key={`es-${i}`} className="px-3 py-2 flex justify-between items-center">
                            <span>🔧 {serv?.nombre ?? `Servicio #${s.servicio_id}`} x{s.cantidad} @ ${(Number(s.precio_unitario) || 0).toFixed(2)}</span>
                            <button type="button" onClick={() => quitarServicioEditar(i)} className="text-red-600 hover:text-red-700 text-xs">Quitar</button>
                          </div>
                        )
                      })}
                      {(formEditar.repuestos || []).map((r, i) => {
                        const rep = repuestos.find((x) => (x.id_repuesto ?? x.id) === r.repuesto_id)
                        return (
                          <div key={`er-${i}`} className="px-3 py-2 flex justify-between items-center">
                            <span>📦 {rep?.nombre ?? `Repuesto #${r.repuesto_id}`} x{r.cantidad} @ ${(Number(r.precio_unitario) || 0).toFixed(2)}</span>
                            <button type="button" onClick={() => quitarRepuestoEditar(i)} className="text-red-600 hover:text-red-700 text-xs">Quitar</button>
                          </div>
                        )
                      })}
                    </>
                  )}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={!!formEditar.requiere_autorizacion} onChange={(e) => setFormEditar({ ...formEditar, requiere_autorizacion: e.target.checked })} /><span>Requiere autorización del cliente</span></label>
                <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={!!formEditar.cliente_proporciono_refacciones} onChange={(e) => setFormEditar({ ...formEditar, cliente_proporciono_refacciones: e.target.checked })} /><span>Cliente proporcionó refacciones</span></label>
              </div>
            </>
          ) : null}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Técnico</label>
            <select value={formEditar.tecnico_id} onChange={(e) => setFormEditar({ ...formEditar, tecnico_id: e.target.value })} className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation">
              <option value="">Sin asignar</option>
              {(tecnicos || []).map((t) => (
                <option key={t.id_usuario ?? t.id} value={t.id_usuario ?? t.id}>{t.nombre || t.email}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label>
            <select value={formEditar.prioridad} onChange={(e) => setFormEditar({ ...formEditar, prioridad: e.target.value })} className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation">
              <option value="BAJA">Baja</option>
              <option value="NORMAL">Normal</option>
              <option value="ALTA">Alta</option>
              <option value="URGENTE">Urgente</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha promesa</label>
            <input type="datetime-local" value={formEditar.fecha_promesa} onChange={(e) => setFormEditar({ ...formEditar, fecha_promesa: e.target.value })} className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2 border-t">
            <button type="button" onClick={() => { setModalEditar(false); setOrdenEditando(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviandoEditar} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviandoEditar ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo={`Crear venta desde orden — ${ordenParaVenta?.numero_orden || ''}`} abierto={modalCrearVenta} onCerrar={() => { setModalCrearVenta(false); setOrdenParaVenta(null) }}>
        <div className="space-y-4">
          {ordenParaVenta && (
            <>
              <p className="text-sm text-slate-600">Se creará una venta con el total de la orden (${(Number(ordenParaVenta.total) || 0).toFixed(2)}) y los mismos servicios y repuestos.</p>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={requiereFacturaVenta} onChange={(e) => setRequiereFacturaVenta(e.target.checked)} />
                <span className="text-sm text-slate-700">Requiere factura (aplica {config.iva_porcentaje ?? 8}% IVA)</span>
              </label>
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setModalCrearVenta(false); setOrdenParaVenta(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
                <button type="button" onClick={confirmarCrearVenta} disabled={enviandoCrearVenta} className="min-h-[44px] px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-50 touch-manipulation">{enviandoCrearVenta ? 'Creando...' : 'Crear venta'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>

      <Modal titulo={`Cancelar orden — ${ordenACancelar?.numero_orden || ''}`} abierto={modalCancelar} onCerrar={() => { setModalCancelar(false); setOrdenACancelar(null); setOrdenACancelarRepuestos([]); setMotivoCancelacion(''); setDevolverRepuestos(false); setMotivoNoDevolucion('') }}>
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Indica el motivo de la cancelación (mínimo 10 caracteres).</p>
          <textarea value={motivoCancelacion} onChange={(e) => setMotivoCancelacion(e.target.value)} placeholder="Ej: Cliente no autorizó el trabajo, vehículo retirado..." rows={3} className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          {ordenACancelar?.estado === 'EN_PROCESO' && ordenACancelarRepuestos.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-3">
              <p className="text-sm font-medium text-amber-900">⚠️ Esta orden tiene repuestos que se descontaron del inventario:</p>
              <ul className="text-sm text-amber-800 list-disc list-inside space-y-0.5">
                {ordenACancelarRepuestos.map((r, i) => {
                  const nombre = r.repuesto_nombre || r.repuesto_codigo ? `${r.repuesto_codigo ? `[${r.repuesto_codigo}] ` : ''}${r.repuesto_nombre || ''}`.trim() || `Repuesto #${r.repuesto_id}` : `Repuesto #${r.repuesto_id}`
                  return <li key={r.id || i}>{nombre} x{r.cantidad}</li>
                })}
              </ul>
              <label className="flex items-center gap-2 cursor-pointer" title="Marca si los repuestos no se utilizaron y pueden volver al inventario">
                <input type="checkbox" checked={devolverRepuestos} onChange={(e) => { setDevolverRepuestos(e.target.checked); if (e.target.checked) setMotivoNoDevolucion('') }} />
                <span className="text-sm text-amber-900">Devolver estos repuestos al inventario (no se utilizaron)</span>
              </label>
              {!devolverRepuestos && (
                <div>
                  <label className="block text-sm font-medium text-amber-900 mb-1">Si no se devuelven, indica el motivo (para registro y contabilización):</label>
                  <select value={motivoNoDevolucion} onChange={(e) => setMotivoNoDevolucion(e.target.value)} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-amber-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 touch-manipulation">
                    <option value="">Seleccionar...</option>
                    <option value="DAÑADO">Dañado durante instalación</option>
                    <option value="USADO">Usado en trabajo parcial</option>
                    <option value="MERMA">Merma / no reutilizable</option>
                    <option value="OTRO">Otro motivo</option>
                  </select>
                  <p className="text-xs text-amber-700 mt-0.5">Se registrará en la orden para auditoría y reportes. El inventario ya fue descontado al iniciar.</p>
                </div>
              )}
            </div>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => { setModalCancelar(false); setOrdenACancelar(null); setMotivoCancelacion('') }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">No cancelar</button>
            <button type="button" onClick={confirmarCancelar} disabled={enviandoCancelar || !motivoCancelacion.trim() || motivoCancelacion.trim().length < 10} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">Cancelar orden</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
