import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function OrdenesTrabajo() {
  const { user } = useAuth()
  const [ordenes, setOrdenes] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [clientes, setClientes] = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [tecnicos, setTecnicos] = useState([])
  const [servicios, setServicios] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [form, setForm] = useState({ cliente_id: '', vehiculo_id: '', tecnico_id: '', fecha_promesa: '', prioridad: 'NORMAL', diagnostico_inicial: '', observaciones_cliente: '', requiere_autorizacion: false, servicios: [], repuestos: [] })
  const [detalleActual, setDetalleActual] = useState({ tipo: 'SERVICIO', id_item: '', cantidad: 1, precio_unitario: 0 })
  const [clienteBuscar, setClienteBuscar] = useState('')
  const [mostrarDropdownCliente, setMostrarDropdownCliente] = useState(false)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
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
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const [enviandoCancelar, setEnviandoCancelar] = useState(false)

  const cargar = () => {
    const params = { skip: (pagina - 1) * limit, limit }
    if (filtroEstado) params.estado = filtroEstado
    if (buscar.trim()) params.buscar = buscar.trim()
    api.get('/ordenes-trabajo/', { params }).then((res) => {
      const d = res.data
      setOrdenes(d?.ordenes ?? [])
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => setOrdenes([]))
    .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, filtroEstado, buscar])

  const abrirNueva = async () => {
    setForm({ cliente_id: '', vehiculo_id: '', tecnico_id: '', fecha_promesa: '', prioridad: 'NORMAL', diagnostico_inicial: '', observaciones_cliente: '', requiere_autorizacion: false, servicios: [], repuestos: [] })
    setDetalleActual({ tipo: 'SERVICIO', id_item: '', cantidad: 1, precio_unitario: 0 })
    setClienteBuscar('')
    setMostrarDropdownCliente(false)
    setError('')
    const [rClientes, rServicios, rRepuestos, rUsuarios] = await Promise.allSettled([
      api.get('/clientes/', { params: { limit: 500 } }),
      api.get('/servicios/', { params: { limit: 100 } }),
      api.get('/repuestos/', { params: { limit: 500 } }),
      api.get('/usuarios/'),
    ])
    if (rClientes.status === 'fulfilled') {
      const d = rClientes.value?.data
      setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
    } else setClientes([])
    if (rServicios.status === 'fulfilled') {
      const d = rServicios.value?.data
      setServicios(d?.servicios ?? d ?? [])
    } else setServicios([])
    if (rRepuestos.status === 'fulfilled') {
      const d = rRepuestos.value?.data
      setRepuestos(Array.isArray(d) ? d : d?.items ?? d?.repuestos ?? [])
    } else setRepuestos([])
    if (rUsuarios.status === 'fulfilled') {
      const users = Array.isArray(rUsuarios.value?.data) ? rUsuarios.value.data : []
      setTecnicos(users.filter((u) => u.rol === 'TECNICO'))
    } else setTecnicos([])
    setModalAbierto(true)
  }

  useEffect(() => {
    if (form.cliente_id && modalAbierto) {
      api.get(`/vehiculos/cliente/${form.cliente_id}`).then((r) => setVehiculos(Array.isArray(r.data) ? r.data : [])).catch(() => setVehiculos([]))
    } else {
      setVehiculos([])
    }
  }, [form.cliente_id, modalAbierto])

  const puedeAgregar = detalleActual.id_item && (parseInt(detalleActual.cantidad) || 0) >= 1
  const agregarDetalle = () => {
    if (!puedeAgregar) return
    const idItem = parseInt(detalleActual.id_item)
    const cantidad = parseInt(detalleActual.cantidad) || 1
    const precio = Number(detalleActual.precio_unitario) || 0
    if (detalleActual.tipo === 'SERVICIO') {
      const s = servicios.find(x => (x.id ?? x.id_servicio) === idItem)
      setForm({
        ...form,
        servicios: [...form.servicios, { servicio_id: idItem, cantidad, precio_unitario: precio || (s ? Number(s.precio_base) : 0) }]
      })
    } else {
      const r = repuestos.find(x => (x.id_repuesto ?? x.id) === idItem)
      setForm({
        ...form,
        repuestos: [...form.repuestos, { repuesto_id: idItem, cantidad, precio_unitario: precio || (r ? Number(r.precio_venta) : 0) }]
      })
    }
    setDetalleActual({ tipo: detalleActual.tipo, id_item: '', cantidad: 1, precio_unitario: 0 })
  }
  const quitarServicio = (idx) => setForm({ ...form, servicios: form.servicios.filter((_, i) => i !== idx) })
  const quitarRepuesto = (idx) => setForm({ ...form, repuestos: form.repuestos.filter((_, i) => i !== idx) })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.vehiculo_id || !form.cliente_id) {
      setError('Selecciona cliente y vehículo')
      return
    }
    setEnviando(true)
    try {
      await api.post('/ordenes-trabajo/', {
        vehiculo_id: parseInt(form.vehiculo_id),
        cliente_id: parseInt(form.cliente_id),
        tecnico_id: form.tecnico_id ? parseInt(form.tecnico_id) : null,
        fecha_promesa: form.fecha_promesa || null,
        prioridad: form.prioridad,
        diagnostico_inicial: form.diagnostico_inicial || null,
        observaciones_cliente: form.observaciones_cliente || null,
        requiere_autorizacion: form.requiere_autorizacion,
        servicios: form.servicios.length ? form.servicios.map((s) => ({ servicio_id: s.servicio_id, cantidad: s.cantidad || 1, precio_unitario: s.precio_unitario || null })) : [],
        repuestos: form.repuestos.length ? form.repuestos.map((r) => ({ repuesto_id: r.repuesto_id, cantidad: r.cantidad || 1, precio_unitario: r.precio_unitario || null })) : [],
      })
      cargar()
      setModalAbierto(false)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg.map((m) => m.msg).join(', ') : msg)
    } finally {
      setEnviando(false)
    }
  }

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

  const abrirModalCancelar = (o) => {
    setOrdenACancelar(o)
    setMotivoCancelacion('')
    setModalCancelar(true)
  }

  const confirmarCancelar = async () => {
    if (!ordenACancelar) return
    if (!motivoCancelacion.trim() || motivoCancelacion.trim().length < 10) {
      alert('El motivo debe tener al menos 10 caracteres.')
      return
    }
    setEnviandoCancelar(true)
    try {
      await api.post(`/ordenes-trabajo/${ordenACancelar.id}/cancelar`, null, { params: { motivo: motivoCancelacion.trim() } })
      cargar()
      setModalCancelar(false)
      setOrdenACancelar(null)
      setMotivoCancelacion('')
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
            <option value="ESPERANDO_AUTORIZACION">Esperando autorización</option>
            <option value="COMPLETADA">Completada</option>
            <option value="ENTREGADA">Entregada</option>
            <option value="CANCELADA">Cancelada</option>
          </select>
          <button onClick={abrirNueva} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Nueva orden</button>
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
                      {puedeAutorizar && o.estado === 'ESPERANDO_AUTORIZACION' && (
                        <>
                          <button onClick={() => autorizarOrden(o.id, true)} disabled={autorizandoId === o.id} className="text-sm text-green-600 hover:text-green-700">Autorizar</button>
                          <button onClick={() => autorizarOrden(o.id, false)} disabled={autorizandoId === o.id} className="text-sm text-red-600 hover:text-red-700">Rechazar</button>
                        </>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && o.estado === 'PENDIENTE' && (
                        <button onClick={() => iniciarOrden(o.id)} className="text-sm text-primary-600 hover:text-primary-700">Iniciar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && o.estado === 'EN_PROCESO' && (
                        <button onClick={() => finalizarOrden(o.id)} className="text-sm text-blue-600 hover:text-blue-700">Finalizar</button>
                      )}
                      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && o.estado === 'COMPLETADA' && (
                        <button onClick={() => entregarOrden(o.id)} className="text-sm text-green-600 hover:text-green-700">Entregar</button>
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

      <Modal titulo="Nueva orden de trabajo" abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div className="relative">
            <label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label>
            <div className="flex gap-1">
              <input
                type="text"
                value={form.cliente_id ? (clientes.find(c => c.id_cliente === parseInt(form.cliente_id))?.nombre ?? '') : clienteBuscar}
                onChange={(e) => {
                  const v = e.target.value
                  setClienteBuscar(v)
                  setMostrarDropdownCliente(true)
                  if (!v) setForm({ ...form, cliente_id: '', vehiculo_id: '' })
                }}
                onFocus={() => setMostrarDropdownCliente(true)}
                onBlur={() => setTimeout(() => setMostrarDropdownCliente(false), 150)}
                placeholder="Escribe para buscar (nombre o teléfono)..."
                className="flex-1 px-4 py-2 border border-slate-300 rounded-lg"
                autoComplete="off"
              />
              {form.cliente_id && (
                <button type="button" onClick={() => setForm({ ...form, cliente_id: '', vehiculo_id: '' })} className="px-3 py-2 border border-slate-300 rounded-lg text-slate-500 hover:bg-slate-50" title="Limpiar">✕</button>
              )}
            </div>
            {mostrarDropdownCliente && !form.cliente_id && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                {(clientes || [])
                  .filter(c => !clienteBuscar.trim() || (c.nombre || '').toLowerCase().includes(clienteBuscar.toLowerCase()) || (c.telefono || '').includes(clienteBuscar))
                  .slice(0, 20)
                  .map((c) => (
                    <button
                      key={c.id_cliente}
                      type="button"
                      onClick={() => {
                        setForm({ ...form, cliente_id: String(c.id_cliente), vehiculo_id: '' })
                        setClienteBuscar('')
                        setMostrarDropdownCliente(false)
                      }}
                      className="w-full px-4 py-2 text-left hover:bg-slate-50 text-sm text-slate-700"
                    >
                      {c.nombre} {c.telefono ? `(${c.telefono})` : ''}
                    </button>
                  ))}
                {(!clientes || clientes.length === 0) && (
                  <div className="px-4 py-3 text-sm text-slate-500">No hay clientes. Crea uno en la sección Clientes.</div>
                )}
              </div>
            )}
          </div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Vehículo *</label><select value={form.vehiculo_id || ''} onChange={(e) => setForm({ ...form, vehiculo_id: e.target.value })} required className="w-full px-4 py-2 border border-slate-300 rounded-lg" disabled={!form.cliente_id}><option value="">Seleccionar...</option>{(vehiculos || []).map((v) => <option key={v.id_vehiculo} value={v.id_vehiculo}>{v.marca} {v.modelo} {v.anio}</option>)}</select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Técnico (opcional)</label><select value={form.tecnico_id || ''} onChange={(e) => setForm({ ...form, tecnico_id: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg"><option value="">Sin asignar</option>{(tecnicos || []).map((t) => <option key={t.id_usuario ?? t.id} value={t.id_usuario ?? t.id}>{t.nombre || t.email} (Técnico)</option>)}</select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label><select value={form.prioridad} onChange={(e) => setForm({ ...form, prioridad: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg"><option value="BAJA">Baja</option><option value="NORMAL">Normal</option><option value="ALTA">Alta</option><option value="URGENTE">Urgente</option></select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Fecha promesa</label><input type="datetime-local" value={form.fecha_promesa} onChange={(e) => setForm({ ...form, fecha_promesa: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Diagnóstico inicial</label><textarea value={form.diagnostico_inicial} onChange={(e) => setForm({ ...form, diagnostico_inicial: e.target.value })} rows={2} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Observaciones cliente</label><textarea value={form.observaciones_cliente} onChange={(e) => setForm({ ...form, observaciones_cliente: e.target.value })} rows={2} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Agregar producto o servicio</label>
            <div className="flex gap-2 flex-wrap items-end">
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Tipo</label>
                <select value={detalleActual.tipo} onChange={(e) => setDetalleActual({ ...detalleActual, tipo: e.target.value, id_item: '' })} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
                  <option value="SERVICIO">Servicio</option>
                  <option value="PRODUCTO">Producto</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">{detalleActual.tipo === 'SERVICIO' ? 'Servicio' : 'Producto'} *</label>
                <select value={detalleActual.id_item} onChange={(e) => {
                  const id = e.target.value
                  const item = detalleActual.tipo === 'SERVICIO' ? servicios.find(s => (s.id ?? s.id_servicio) === parseInt(id)) : repuestos.find(r => (r.id_repuesto ?? r.id) === parseInt(id))
                  const precio = item ? (detalleActual.tipo === 'SERVICIO' ? Number(item.precio_base) : Number(item.precio_venta)) : 0
                  setDetalleActual({ ...detalleActual, id_item: id, precio_unitario: precio })
                }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[160px]">
                  <option value="">Seleccionar...</option>
                  {(detalleActual.tipo === 'SERVICIO' ? servicios : repuestos).map((x) => (
                    <option key={x.id ?? x.id_servicio ?? x.id_repuesto} value={x.id ?? x.id_servicio ?? x.id_repuesto}>{x.codigo || ''} {x.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Cantidad</label>
                <input type="number" min={1} value={detalleActual.cantidad} onChange={(e) => setDetalleActual({ ...detalleActual, cantidad: parseInt(e.target.value) || 1 })} className="w-16 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Precio</label>
                <input type="number" min={0} step={0.01} value={detalleActual.precio_unitario || ''} onChange={(e) => setDetalleActual({ ...detalleActual, precio_unitario: parseFloat(e.target.value) || 0 })} placeholder="Auto" className="w-20 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
              </div>
              <button type="button" onClick={agregarDetalle} disabled={!puedeAgregar} className="px-3 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300 disabled:opacity-50 disabled:cursor-not-allowed">+ Agregar</button>
            </div>
            {(!detalleActual.id_item || detalleActual.cantidad < 1) && (
              <p className="text-xs text-slate-500 mt-1">Selecciona tipo, item y cantidad para activar Agregar.</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Productos y servicios agregados</label>
            <div className="border border-slate-200 rounded-lg divide-y max-h-32 overflow-y-auto">
              {form.servicios.length === 0 && form.repuestos.length === 0 ? (
                <p className="px-3 py-4 text-sm text-slate-500 text-center">Ninguno (opcional)</p>
              ) : (
                <>
                  {form.servicios.map((s, i) => {
                    const serv = servicios.find(x => (x.id ?? x.id_servicio) === s.servicio_id)
                    return (
                      <div key={`s-${i}`} className="px-3 py-2 flex justify-between items-center text-sm">
                        <span>🔧 {serv?.nombre ?? `Servicio #${s.servicio_id}`} x{s.cantidad} @ ${(Number(s.precio_unitario) || 0).toFixed(2)}</span>
                        <button type="button" onClick={() => quitarServicio(i)} className="text-red-600 hover:text-red-700 text-xs">Quitar</button>
                      </div>
                    )
                  })}
                  {form.repuestos.map((r, i) => {
                    const rep = repuestos.find(x => (x.id_repuesto ?? x.id) === r.repuesto_id)
                    return (
                      <div key={`r-${i}`} className="px-3 py-2 flex justify-between items-center text-sm">
                        <span>📦 {rep?.nombre ?? `Repuesto #${r.repuesto_id}`} x{r.cantidad} @ ${(Number(r.precio_unitario) || 0).toFixed(2)}</span>
                        <button type="button" onClick={() => quitarRepuesto(i)} className="text-red-600 hover:text-red-700 text-xs">Quitar</button>
                      </div>
                    )
                  })}
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2"><input type="checkbox" checked={form.requiere_autorizacion} onChange={(e) => setForm({ ...form, requiere_autorizacion: e.target.checked })} /><label>Requiere autorización del cliente</label></div>
          <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button><button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Crear orden'}</button></div>
        </form>
      </Modal>

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
            </div>
            {ordenDetalle.diagnostico_inicial && <div><h3 className="text-sm font-semibold text-slate-700 mb-1">Diagnóstico</h3><p className="text-sm text-slate-600">{ordenDetalle.diagnostico_inicial}</p></div>}
            {(ordenDetalle.detalles_servicio?.length || ordenDetalle.detalles_repuesto?.length) > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Servicios y repuestos</h3>
                <div className="border rounded-lg divide-y text-sm">
                  {(ordenDetalle.detalles_servicio || []).map((d) => (
                    <div key={d.id} className="px-3 py-2 flex justify-between"><span>🔧 {d.descripcion || `Servicio #${d.servicio_id}`} x{d.cantidad}</span><span>${(Number(d.subtotal) || 0).toFixed(2)}</span></div>
                  ))}
                  {(ordenDetalle.detalles_repuesto || []).map((d) => (
                    <div key={d.id} className="px-3 py-2 flex justify-between"><span>📦 Repuesto #{d.repuesto_id} x{d.cantidad}</span><span>${(Number(d.subtotal) || 0).toFixed(2)}</span></div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-2 flex-wrap pt-2 border-t">
              {puedeAutorizar && ordenDetalle.estado === 'ESPERANDO_AUTORIZACION' && (
                <>
                  <button onClick={() => autorizarOrden(ordenDetalle.id, true)} disabled={autorizandoId === ordenDetalle.id} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm">Autorizar</button>
                  <button onClick={() => autorizarOrden(ordenDetalle.id, false)} disabled={autorizandoId === ordenDetalle.id} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm">Rechazar</button>
                </>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && ordenDetalle.estado === 'PENDIENTE' && (
                <button onClick={() => iniciarOrden(ordenDetalle.id)} className="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-sm">Iniciar</button>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'TECNICO') && ordenDetalle.estado === 'EN_PROCESO' && (
                <button onClick={() => finalizarOrden(ordenDetalle.id)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm">Finalizar</button>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && ordenDetalle.estado === 'COMPLETADA' && (
                <button onClick={() => entregarOrden(ordenDetalle.id)} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm">Entregar</button>
              )}
              {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && ordenDetalle.estado !== 'ENTREGADA' && ordenDetalle.estado !== 'CANCELADA' && (
                <button onClick={() => { setModalDetalle(false); abrirModalCancelar(ordenDetalle) }} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm">Cancelar orden</button>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo={`Cancelar orden — ${ordenACancelar?.numero_orden || ''}`} abierto={modalCancelar} onCerrar={() => { setModalCancelar(false); setOrdenACancelar(null); setMotivoCancelacion('') }}>
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Indica el motivo de la cancelación (mínimo 10 caracteres).</p>
          <textarea value={motivoCancelacion} onChange={(e) => setMotivoCancelacion(e.target.value)} placeholder="Ej: Cliente no autorizó el trabajo, vehículo retirado..." rows={3} className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm" />
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => { setModalCancelar(false); setOrdenACancelar(null); setMotivoCancelacion('') }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">No cancelar</button>
            <button type="button" onClick={confirmarCancelar} disabled={enviandoCancelar || !motivoCancelacion.trim() || motivoCancelacion.trim().length < 10} className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">Cancelar orden</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
