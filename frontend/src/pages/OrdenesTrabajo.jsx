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

  const cargar = () => {
    api.get('/ordenes-trabajo/', { params: { skip: (pagina - 1) * limit, limit } }).then((res) => {
      const d = res.data
      setOrdenes(d?.ordenes ?? [])
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => setOrdenes([]))
    .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina])

  const abrirNueva = async () => {
    setForm({ cliente_id: '', vehiculo_id: '', tecnico_id: '', fecha_promesa: '', prioridad: 'NORMAL', diagnostico_inicial: '', observaciones_cliente: '', requiere_autorizacion: false, servicios: [], repuestos: [] })
    setDetalleActual({ tipo: 'SERVICIO', id_item: '', cantidad: 1, precio_unitario: 0 })
    setClienteBuscar('')
    setMostrarDropdownCliente(false)
    setError('')
    const [rClientes, rServicios, rRepuestos, rUsuarios] = await Promise.allSettled([
      api.get('/clientes/'),
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
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al autorizar')
    } finally {
      setAutorizandoId(null)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-slate-800">Órdenes de trabajo</h1>
        <button onClick={abrirNueva} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Nueva orden</button>
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
                    <span className={`px-2 py-1 rounded text-xs font-medium ${o.estado === 'ESPERANDO_AUTORIZACION' ? 'bg-amber-100 text-amber-800' : o.estado === 'ENTREGADA' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'}`}>
                      {o.estado || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium">${(o.total ?? 0).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    {puedeAutorizar && o.estado === 'ESPERANDO_AUTORIZACION' && (
                      <>
                        <button onClick={() => autorizarOrden(o.id, true)} disabled={autorizandoId === o.id} className="text-sm text-green-600 hover:text-green-700 mr-2">Autorizar</button>
                        <button onClick={() => autorizarOrden(o.id, false)} disabled={autorizandoId === o.id} className="text-sm text-red-600 hover:text-red-700">Rechazar</button>
                      </>
                    )}
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
    </div>
  )
}
