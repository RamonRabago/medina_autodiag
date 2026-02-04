import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

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
  const [modalDetalle, setModalDetalle] = useState(false)
  const [ordenDetalle, setOrdenDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
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
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/config').then((r) => setConfig(r.data || { iva_porcentaje: 8 })).catch(() => {})
  }, [])

  const cargar = () => {
    const params = { skip: (pagina - 1) * limit, limit }
    if (filtroEstado) params.estado = filtroEstado === 'EN_PROCESO_FINALIZAR' ? 'EN_PROCESO' : filtroEstado
    if (buscar.trim()) params.buscar = buscar.trim()
    api.get('/ordenes-trabajo/', { params }).then((res) => {
      const d = res.data
      setOrdenes(d?.ordenes ?? [])
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => setOrdenes([]))
    .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, filtroEstado, buscar])

  useEffect(() => {
    if (modalEditar) {
      if (tecnicos.length === 0) {
        api.get('/usuarios/').then((r) => {
          const users = Array.isArray(r.data) ? r.data : []
          setTecnicos(users.filter((u) => u.rol === 'TECNICO'))
        }).catch(() => {})
      }
      if (ordenEditando?.estado === 'PENDIENTE' && servicios.length === 0) {
        api.get('/servicios/', { params: { limit: 100 } }).then((r) => setServicios(r.data?.servicios ?? r.data ?? [])).catch(() => {})
        api.get('/repuestos/', { params: { limit: 500 } }).then((r) => {
          const d = r.data
          setRepuestos(Array.isArray(d) ? d : d?.items ?? d?.repuestos ?? [])
        }).catch(() => {})
      }
    }
  }, [modalEditar, ordenEditando?.estado])

  const autorizarOrden = async (ordenId, autorizado) => {
    setAutorizandoId(ordenId)
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/autorizar`, { autorizado })
      cargar()
      if (ordenDetalle?.id === ordenId) setModalDetalle(false)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al autorizar')
    } finally {
      setAutorizandoId(null)
    }
  }

  const abrirDetalle = async (o) => {
    setOrdenDetalle(null)
    setModalDetalle(true)
    setCargandoDetalle(true)
    try {
      const res = await api.get(`/ordenes-trabajo/${o.id}`)
      setOrdenDetalle(res.data)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al cargar detalle')
      setModalDetalle(false)
    } finally {
      setCargandoDetalle(false)
    }
  }

  const iniciarOrden = async (ordenId) => {
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/iniciar`, {})
      cargar()
      if (ordenDetalle?.id === ordenId) abrirDetalle({ id: ordenId })
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al iniciar')
    }
  }

  const finalizarOrden = async (ordenId) => {
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/finalizar`, {})
      cargar()
      if (ordenDetalle?.id === ordenId) abrirDetalle({ id: ordenId })
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al finalizar')
    }
  }

  const entregarOrden = async (ordenId) => {
    try {
      await api.post(`/ordenes-trabajo/${ordenId}/entregar`, {})
      cargar()
      setModalDetalle(false)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al entregar')
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
      setModalDetalle(false)
      cargar()
      const idVenta = res.data?.id_venta
      if (idVenta) {
        navigate(`/ventas?id=${idVenta}`)
      }
      alert(`Venta #${idVenta} creada. Total: $${(res.data?.total ?? 0).toFixed(2)}`)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al crear venta')
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
      if (!diag) { alert('El diagnóstico inicial es obligatorio.'); return }
      if (!obs) { alert('Las observaciones del cliente son obligatorias.'); return }
      if (!formEditar.servicios?.length && !formEditar.repuestos?.length) { alert('Debes agregar al menos un producto o servicio.'); return }
      if (requiereAdvertenciaRepuestosEditar && !window.confirm('Hay servicios que suelen requerir repuestos, pero no has agregado repuestos ni marcado "Cliente proporcionó refacciones". ¿Continuar de todos modos?')) return
    }
    setEnviandoEditar(true)
    try {
      const payload = {
        tecnico_id: formEditar.tecnico_id ? parseInt(formEditar.tecnico_id) : null,
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
      alert(err.response?.data?.detail || 'Error al actualizar')
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
    const s = servicios.find(x => (x.id ?? x.id_servicio) === parseInt(detalleActualEditar.id_item))
    return !!s?.requiere_repuestos
  })()

  const agregarDetalleEditar = () => {
    if (!detalleActualEditar.id_item || (parseInt(detalleActualEditar.cantidad) || 0) < 1) return
    const idItem = parseInt(detalleActualEditar.id_item)
    const cantidad = parseInt(detalleActualEditar.cantidad) || 1
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
      alert('El motivo debe tener al menos 10 caracteres.')
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
      alert(err.response?.data?.detail || 'Error al cancelar')
    } finally {
      setEnviandoCancelar(false)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Órdenes de trabajo</h1>
        <div className="flex gap-2 items-center flex-wrap">
          <input type="text" placeholder="Buscar por número..." value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[160px]" />
          <select value={filtroEstado} onChange={(e) => { setFiltroEstado(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
            <option value="">Todos los estados</option>
            <option value="PENDIENTE">Pendiente</option>
            <option value="EN_PROCESO">En proceso</option>
            <option value="EN_PROCESO_FINALIZAR">Pendiente de finalizar</option>
            <option value="ESPERANDO_REPUESTOS">Esperando repuestos</option>
            <option value="ESPERANDO_AUTORIZACION">Esperando autorización</option>
            <option value="COMPLETADA">Completada</option>
            <option value="ENTREGADA">Entregada</option>
            <option value="CANCELADA">Cancelada</option>
          </select>
          <button onClick={() => navigate('/ordenes-trabajo/nueva')} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Nueva orden</button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
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
                      o.estado === 'ENTREGADA' ? 'bg-green-100 text-green-800' :
                      o.estado === 'COMPLETADA' ? 'bg-blue-100 text-blue-800' :
                      o.estado === 'EN_PROCESO' ? 'bg-amber-100 text-amber-800' :
                      o.estado === 'ESPERANDO_AUTORIZACION' ? 'bg-orange-100 text-orange-800' :
                      o.estado === 'CANCELADA' ? 'bg-slate-200 text-slate-700' :
                      'bg-slate-100 text-slate-800'
                    }`}>
                      {o.estado || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium">${(o.total ?? 0).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-1 justify-end flex-wrap">
                      <button onClick={() => abrirDetalle(o)} className="text-sm text-slate-600 hover:text-slate-800" title="Ver detalle">📋</button>
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA' || (user?.rol === 'TECNICO' && o.tecnico_id === user?.id_usuario)) && puedeEditar(o) && (
                        <button onClick={() => abrirEditar(o)} className="text-sm text-slate-600 hover:text-slate-800" title={!o.tecnico_id ? 'Debes agregar técnico' : 'Editar (asignar técnico, etc.)'}>✏️</button>
                      )}
                      {puedeAutorizar && (o.estado === 'ESPERANDO_AUTORIZACION' || (o.estado === 'PENDIENTE' && o.requiere_autorizacion && !o.autorizado)) && (
                        <>
                          <button onClick={() => autorizarOrden(o.id, true)} disabled={autorizandoId === o.id} className="text-sm text-green-600 hover:text-green-700">Autorizar</button>
                          <button onClick={() => autorizarOrden(o.id, false)} disabled={autorizandoId === o.id} className="text-sm text-red-600 hover:text-red-700">Rechazar</button>
                        </>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && o.estado === 'PENDIENTE' && (
                        <button onClick={() => iniciarOrden(o.id)} disabled={!o.tecnico_id && user?.rol === 'ADMIN'} title={!o.tecnico_id && user?.rol === 'ADMIN' ? 'Asigna un técnico antes de iniciar (Editar)' : ''} className={`text-sm ${!o.tecnico_id && user?.rol === 'ADMIN' ? 'text-slate-400 cursor-not-allowed' : 'text-primary-600 hover:text-primary-700'}`}>Iniciar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && o.estado === 'EN_PROCESO' && (
                        <button onClick={() => finalizarOrden(o.id)} className="text-sm text-blue-600 hover:text-blue-700">Finalizar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && o.estado === 'COMPLETADA' && (
                        <button onClick={() => entregarOrden(o.id)} className="text-sm text-green-600 hover:text-green-700">Entregar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (o.estado === 'ENTREGADA' || o.estado === 'COMPLETADA') && (
                        o.id_venta ? (
                          <button onClick={() => navigate(`/ventas?id=${o.id_venta}`)} className="text-sm text-emerald-600 hover:text-emerald-700" title="Ir a cobrar en venta">💰 Cobrar en venta</button>
                        ) : (
                          <button onClick={() => abrirModalCrearVenta(o)} className="text-sm text-emerald-600 hover:text-emerald-700" title="Crear venta desde esta orden">💰 Crear venta</button>
                        )
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && o.estado !== 'ENTREGADA' && o.estado !== 'CANCELADA' && (
                        <button onClick={() => abrirModalCancelar(o)} className="text-sm text-red-600 hover:text-red-700">Cancelar</button>
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
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-3 py-1 border rounded-lg text-sm disabled:opacity-50">Anterior</button>
          <span className="px-3 py-1 text-sm">Página {pagina} de {totalPaginas}</span>
          <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-3 py-1 border rounded-lg text-sm disabled:opacity-50">Siguiente</button>
        </div>
      )}

      <Modal titulo={`Detalle — ${ordenDetalle?.numero_orden || 'Orden'}`} abierto={modalDetalle} onCerrar={() => { setModalDetalle(false); setOrdenDetalle(null) }}>
        {cargandoDetalle ? (
          <p className="text-slate-500 py-4">Cargando...</p>
        ) : ordenDetalle ? (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <p><span className="font-medium text-slate-600">Cliente:</span> {ordenDetalle.cliente?.nombre ?? ordenDetalle.cliente_nombre ?? '-'}</p>
              <p><span className="font-medium text-slate-600">Vehículo:</span> {ordenDetalle.vehiculo ? `${ordenDetalle.vehiculo.marca} ${ordenDetalle.vehiculo.modelo} ${ordenDetalle.vehiculo.anio}` : ordenDetalle.vehiculo_info ?? '-'}</p>
              <p><span className="font-medium text-slate-600">Estado:</span> <span className={`px-2 py-0.5 rounded text-xs ${ordenDetalle.estado === 'ENTREGADA' ? 'bg-green-100 text-green-800' : ordenDetalle.estado === 'COMPLETADA' ? 'bg-blue-100 text-blue-800' : ordenDetalle.estado === 'EN_PROCESO' ? 'bg-amber-100 text-amber-800' : ordenDetalle.estado === 'CANCELADA' ? 'bg-slate-200 text-slate-700' : 'bg-slate-100'}`}>{ordenDetalle.estado || '-'}</span></p>
              <p><span className="font-medium text-slate-600">Prioridad:</span> {ordenDetalle.prioridad || '-'}</p>
              <p><span className="font-medium text-slate-600">Total:</span> ${(Number(ordenDetalle.total) || 0).toFixed(2)}</p>
              <p><span className="font-medium text-slate-600">Técnico:</span> {ordenDetalle.tecnico?.nombre ?? ordenDetalle.tecnico?.email ?? '-'}</p>
              {ordenDetalle.cliente_proporciono_refacciones && <p><span className="font-medium text-slate-600">Cliente proporcionó refacciones:</span> Sí</p>}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-1">Diagnóstico inicial</h3>
              <p className="text-sm text-slate-600 whitespace-pre-wrap">{ordenDetalle.diagnostico_inicial?.trim() || '-'}</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-1">Observaciones del cliente</h3>
              <p className="text-sm text-slate-600 whitespace-pre-wrap">{ordenDetalle.observaciones_cliente?.trim() || '-'}</p>
            </div>
            {ordenDetalle.estado === 'CANCELADA' && ordenDetalle.observaciones_tecnico?.trim() && (
              <div className="p-3 bg-slate-100 border border-slate-200 rounded-lg">
                <h3 className="text-sm font-semibold text-slate-700 mb-1">Detalle de cancelación</h3>
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{ordenDetalle.observaciones_tecnico?.trim() || '-'}</p>
              </div>
            )}
            {(ordenDetalle.detalles_servicio?.length || ordenDetalle.detalles_repuesto?.length) > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Servicios y repuestos</h3>
                <div className="border rounded-lg divide-y text-sm">
                  {(ordenDetalle.detalles_servicio || []).map((d) => (
                    <div key={d.id} className="px-3 py-2 flex justify-between"><span>🔧 {d.descripcion || `Servicio #${d.servicio_id}`} x{d.cantidad}</span><span>${(Number(d.subtotal) || 0).toFixed(2)}</span></div>
                  ))}
                  {(ordenDetalle.detalles_repuesto || []).map((d) => {
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
            <div className="flex gap-2 flex-wrap pt-2 border-t">
              {(user?.rol === 'ADMIN' || user?.rol === 'CAJA' || (user?.rol === 'TECNICO' && ordenDetalle.tecnico_id === user?.id_usuario)) && puedeEditar(ordenDetalle) && (
                <button onClick={() => { setModalDetalle(false); abrirEditar(ordenDetalle) }} title={!ordenDetalle.tecnico_id ? 'Debes agregar técnico' : ''} className="px-3 py-1.5 bg-slate-600 text-white rounded-lg text-sm hover:bg-slate-700">Editar</button>
              )}
              {puedeAutorizar && (ordenDetalle.estado === 'ESPERANDO_AUTORIZACION' || (ordenDetalle.estado === 'PENDIENTE' && ordenDetalle.requiere_autorizacion && !ordenDetalle.autorizado)) && (
                <>
                  <button onClick={() => autorizarOrden(ordenDetalle.id, true)} disabled={autorizandoId === ordenDetalle.id} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm">Autorizar</button>
                  <button onClick={() => autorizarOrden(ordenDetalle.id, false)} disabled={autorizandoId === ordenDetalle.id} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm">Rechazar</button>
                </>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && ordenDetalle.estado === 'PENDIENTE' && (
                <button onClick={() => iniciarOrden(ordenDetalle.id)} disabled={!ordenDetalle.tecnico_id && user?.rol === 'ADMIN'} title={!ordenDetalle.tecnico_id && user?.rol === 'ADMIN' ? 'Asigna un técnico antes de iniciar (Editar)' : ''} className={`px-3 py-1.5 rounded-lg text-sm ${!ordenDetalle.tecnico_id && user?.rol === 'ADMIN' ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-primary-600 text-white hover:bg-primary-700'}`}>Iniciar</button>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && ordenDetalle.estado === 'EN_PROCESO' && (
                <button onClick={() => finalizarOrden(ordenDetalle.id)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm">Finalizar</button>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && ordenDetalle.estado === 'COMPLETADA' && (
                <button onClick={() => entregarOrden(ordenDetalle.id)} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm">Entregar</button>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (ordenDetalle.estado === 'ENTREGADA' || ordenDetalle.estado === 'COMPLETADA') && (
                ordenDetalle.id_venta ? (
                  <button onClick={() => navigate(`/ventas?id=${ordenDetalle.id_venta}`)} className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">💰 Cobrar en venta</button>
                ) : (
                  <button onClick={() => abrirModalCrearVenta(ordenDetalle)} className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">💰 Crear venta</button>
                )
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && ordenDetalle.estado !== 'ENTREGADA' && ordenDetalle.estado !== 'CANCELADA' && (
                <button onClick={() => { setModalDetalle(false); abrirModalCancelar(ordenDetalle) }} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm">Cancelar orden</button>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo={`Editar orden — ${ordenEditando?.numero_orden || ''}`} abierto={modalEditar} onCerrar={() => { setModalEditar(false); setOrdenEditando(null) }}>
        <form onSubmit={handleEditarSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto">
          {ordenEditando?.estado === 'PENDIENTE' ? (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Diagnóstico inicial *</label>
                <textarea value={formEditar.diagnostico_inicial} onChange={(e) => setFormEditar({ ...formEditar, diagnostico_inicial: e.target.value })} rows={2} className="w-full px-4 py-2 border border-slate-300 rounded-lg" placeholder="Qué reporta el cliente o lo detectado en revisión inicial" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones del cliente *</label>
                <textarea value={formEditar.observaciones_cliente} onChange={(e) => setFormEditar({ ...formEditar, observaciones_cliente: e.target.value })} rows={2} className="w-full px-4 py-2 border border-slate-300 rounded-lg" placeholder="Preferencias, restricciones, urgencias" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Agregar producto o servicio</label>
                <div className="flex gap-2 flex-wrap items-end">
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Tipo</label>
                    <select value={detalleActualEditar.tipo} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, tipo: e.target.value, id_item: '' })} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
                      <option value="SERVICIO">Servicio</option>
                      <option value="PRODUCTO">Producto</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">{detalleActualEditar.tipo === 'SERVICIO' ? 'Servicio' : 'Producto'}</label>
                    <select value={detalleActualEditar.id_item} onChange={(e) => {
                      const id = e.target.value
                      const item = detalleActualEditar.tipo === 'SERVICIO' ? servicios.find((s) => (s.id ?? s.id_servicio) === parseInt(id)) : repuestos.find((r) => (r.id_repuesto ?? r.id) === parseInt(id))
                      const precio = item ? (detalleActualEditar.tipo === 'SERVICIO' ? Number(item.precio_base) : Number(item.precio_venta)) : 0
                      setDetalleActualEditar({ ...detalleActualEditar, id_item: id, precio_unitario: precio })
                    }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[140px]">
                      <option value="">Seleccionar...</option>
                      {(detalleActualEditar.tipo === 'SERVICIO' ? servicios : repuestos).map((x) => (
                        <option key={x.id ?? x.id_servicio ?? x.id_repuesto} value={x.id ?? x.id_servicio ?? x.id_repuesto}>{x.codigo || ''} {x.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Cant.</label>
                    <input type="number" min={1} value={detalleActualEditar.cantidad} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, cantidad: parseInt(e.target.value) || 1 })} className="w-14 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Precio</label>
                    <input type="number" min={0} step={0.01} value={detalleActualEditar.precio_unitario || ''} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, precio_unitario: parseFloat(e.target.value) || 0 })} className="w-18 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                  </div>
                  <button type="button" onClick={agregarDetalleEditar} disabled={!detalleActualEditar.id_item} className="px-3 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300 disabled:opacity-50">+ Agregar</button>
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
            <select value={formEditar.tecnico_id} onChange={(e) => setFormEditar({ ...formEditar, tecnico_id: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="">Sin asignar</option>
              {(tecnicos || []).map((t) => (
                <option key={t.id_usuario ?? t.id} value={t.id_usuario ?? t.id}>{t.nombre || t.email}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label>
            <select value={formEditar.prioridad} onChange={(e) => setFormEditar({ ...formEditar, prioridad: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="BAJA">Baja</option>
              <option value="NORMAL">Normal</option>
              <option value="ALTA">Alta</option>
              <option value="URGENTE">Urgente</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha promesa</label>
            <input type="datetime-local" value={formEditar.fecha_promesa} onChange={(e) => setFormEditar({ ...formEditar, fecha_promesa: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t">
            <button type="button" onClick={() => { setModalEditar(false); setOrdenEditando(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">Cancelar</button>
            <button type="submit" disabled={enviandoEditar} className="px-4 py-2 bg-primary-600 text-white rounded-lg disabled:opacity-50">{enviandoEditar ? 'Guardando...' : 'Guardar'}</button>
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
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setModalCrearVenta(false); setOrdenParaVenta(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">Cancelar</button>
                <button type="button" onClick={confirmarCrearVenta} disabled={enviandoCrearVenta} className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50">{enviandoCrearVenta ? 'Creando...' : 'Crear venta'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>

      <Modal titulo={`Cancelar orden — ${ordenACancelar?.numero_orden || ''}`} abierto={modalCancelar} onCerrar={() => { setModalCancelar(false); setOrdenACancelar(null); setOrdenACancelarRepuestos([]); setMotivoCancelacion(''); setDevolverRepuestos(false); setMotivoNoDevolucion('') }}>
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Indica el motivo de la cancelación (mínimo 10 caracteres).</p>
          <textarea value={motivoCancelacion} onChange={(e) => setMotivoCancelacion(e.target.value)} placeholder="Ej: Cliente no autorizó el trabajo, vehículo retirado..." rows={3} className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm" />
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
                  <select value={motivoNoDevolucion} onChange={(e) => setMotivoNoDevolucion(e.target.value)} className="w-full px-3 py-2 border border-amber-300 rounded-lg text-sm bg-white">
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
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => { setModalCancelar(false); setOrdenACancelar(null); setMotivoCancelacion('') }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">No cancelar</button>
            <button type="button" onClick={confirmarCancelar} disabled={enviandoCancelar || !motivoCancelacion.trim() || motivoCancelacion.trim().length < 10} className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">Cancelar orden</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
