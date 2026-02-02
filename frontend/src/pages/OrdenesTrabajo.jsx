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
    setError('')
    try {
      const [rClientes, rServicios, rRepuestos] = await Promise.all([
        api.get('/clientes/'),
        api.get('/servicios/', { params: { limit: 100 } }),
        api.get('/repuestos/', { params: { limit: 200 } }),
      ])
      setClientes(Array.isArray(rClientes.data) ? rClientes.data : rClientes.data?.clientes ?? [])
      setServicios(rServicios.data?.servicios ?? rServicios.data ?? [])
      setRepuestos(Array.isArray(rRepuestos.data) ? rRepuestos.data : rRepuestos.data?.items ?? rRepuestos.data?.repuestos ?? [])
      api.get('/usuarios/').then((r) => {
        const users = Array.isArray(r.data) ? r.data : []
        setTecnicos(users.filter((u) => u.rol === 'TECNICO'))
      }).catch(() => setTecnicos([]))
    } catch {
      setClientes([])
      setServicios([])
      setRepuestos([])
      setTecnicos([])
    }
    setModalAbierto(true)
  }

  useEffect(() => {
    if (form.cliente_id && modalAbierto) {
      api.get(`/vehiculos/cliente/${form.cliente_id}`).then((r) => setVehiculos(Array.isArray(r.data) ? r.data : [])).catch(() => setVehiculos([]))
    } else {
      setVehiculos([])
    }
  }, [form.cliente_id, modalAbierto])

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
        servicios: form.servicios.length ? form.servicios.map((s) => ({ servicio_id: s.servicio_id, cantidad: s.cantidad || 1, precio_unitario: s.precio_unitario })) : [],
        repuestos: form.repuestos.length ? form.repuestos.map((r) => ({ repuesto_id: r.repuesto_id, cantidad: r.cantidad || 1 })) : [],
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
                      {typeof o.estado === 'object' ? o.estado?.value ?? o.estado : o.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium">${(o.total ?? 0).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    {puedeAutorizar && (typeof o.estado === 'object' ? o.estado?.value : o.estado) === 'ESPERANDO_AUTORIZACION' && (
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
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label><select value={form.cliente_id || ''} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })} required className="w-full px-4 py-2 border border-slate-300 rounded-lg"><option value="">Seleccionar...</option>{(clientes || []).map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}</select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Vehículo *</label><select value={form.vehiculo_id || ''} onChange={(e) => setForm({ ...form, vehiculo_id: e.target.value })} required className="w-full px-4 py-2 border border-slate-300 rounded-lg" disabled={!form.cliente_id}><option value="">Seleccionar...</option>{(vehiculos || []).map((v) => <option key={v.id_vehiculo} value={v.id_vehiculo}>{v.marca} {v.modelo} {v.anio}</option>)}</select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Técnico (opcional)</label><select value={form.tecnico_id || ''} onChange={(e) => setForm({ ...form, tecnico_id: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg"><option value="">Sin asignar</option>{(tecnicos || []).map((t) => <option key={t.id_usuario ?? t.id} value={t.id_usuario ?? t.id}>{t.nombre || t.email} (Técnico)</option>)}</select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label><select value={form.prioridad} onChange={(e) => setForm({ ...form, prioridad: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg"><option value="BAJA">Baja</option><option value="NORMAL">Normal</option><option value="ALTA">Alta</option><option value="URGENTE">Urgente</option></select></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Fecha promesa</label><input type="datetime-local" value={form.fecha_promesa} onChange={(e) => setForm({ ...form, fecha_promesa: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Diagnóstico inicial</label><textarea value={form.diagnostico_inicial} onChange={(e) => setForm({ ...form, diagnostico_inicial: e.target.value })} rows={2} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Observaciones cliente</label><textarea value={form.observaciones_cliente} onChange={(e) => setForm({ ...form, observaciones_cliente: e.target.value })} rows={2} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>
          <div className="flex items-center gap-2"><input type="checkbox" checked={form.requiere_autorizacion} onChange={(e) => setForm({ ...form, requiere_autorizacion: e.target.checked })} /><label>Requiere autorización del cliente</label></div>
          <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button><button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Crear orden'}</button></div>
        </form>
      </Modal>
    </div>
  )
}
