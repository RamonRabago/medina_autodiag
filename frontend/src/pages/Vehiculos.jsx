import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Vehiculos() {
  const { user } = useAuth()
  const [vehiculos, setVehiculos] = useState([])
  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [filtroCliente, setFiltroCliente] = useState('')
  const [form, setForm] = useState({ id_cliente: null, marca: '', modelo: '', anio: new Date().getFullYear(), numero_serie: '', color: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [totalVehiculos, setTotalVehiculos] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [modalHistorial, setModalHistorial] = useState(false)
  const [historialData, setHistorialData] = useState(null)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const limit = 20

  const cargar = () => {
    const params = { skip: (pagina - 1) * limit, limit }
    if (filtroCliente) params.id_cliente = filtroCliente
    if (buscar.trim()) params.buscar = buscar.trim()
    api.get('/vehiculos/', { params }).then((res) => {
      const d = res.data
      if (d?.vehiculos) {
        setVehiculos(d.vehiculos)
        setTotalVehiculos(d.total ?? d.vehiculos.length)
        setTotalPaginas(d.total_paginas ?? 1)
      } else {
        setVehiculos(Array.isArray(d) ? d : [])
        setTotalVehiculos(Array.isArray(d) ? d.length : 0)
        setTotalPaginas(1)
      }
    }).catch(() => setVehiculos([]))
    .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [filtroCliente, pagina, buscar])
  useEffect(() => {
    api.get('/clientes/', { params: { limit: 500 } }).then((res) => {
      const d = res.data
      setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
    }).catch(() => setClientes([]))
  }, [])

  const abrirNuevo = (clientePre = null) => {
    const cliente = clientePre || (filtroCliente ? clientes.find((c) => c.id_cliente === parseInt(filtroCliente)) : null)
    setEditando(null)
    setForm({ id_cliente: cliente?.id_cliente || null, marca: '', modelo: '', anio: new Date().getFullYear(), numero_serie: '', color: '' })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (v) => {
    setEditando(v)
    setForm({ id_cliente: v.id_cliente, marca: v.marca || '', modelo: v.modelo || '', anio: v.anio || new Date().getFullYear(), numero_serie: v.numero_serie || v.vin || '', color: v.color || v.motor || '' })
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
      alert(err.response?.data?.detail || 'Error al cargar historial')
    } finally {
      setCargandoHistorial(false)
    }
  }

  const eliminarVehiculo = async (v) => {
    if (!confirm(`¿Eliminar el vehículo ${v.marca} ${v.modelo} (${v.anio})?`)) return
    try {
      await api.delete(`/vehiculos/${v.id_vehiculo}`)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      const payload = { id_cliente: form.id_cliente, marca: form.marca.trim(), modelo: form.modelo.trim(), anio: parseInt(form.anio), numero_serie: form.numero_serie?.trim() || null, color: form.color?.trim() || null }
      if (editando) await api.put(`/vehiculos/${editando.id_vehiculo}`, payload)
      else await api.post('/vehiculos/', payload)
      cargar()
      setModalAbierto(false)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg.map((m) => m.msg).join(', ') : msg)
    } finally {
      setEnviando(false)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Vehículos</h1>
        <div className="flex gap-2 items-center flex-wrap">
          <input type="text" placeholder="Buscar marca, modelo, VIN..." value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]" />
          <select value={filtroCliente} onChange={(e) => { setFiltroCliente(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
            <option value="">Todos los clientes</option>
            {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
          </select>
          <button onClick={() => abrirNuevo()} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Nuevo vehículo</button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Cliente</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Marca / Modelo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Año</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Color</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">VIN / Serie</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {vehiculos.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">No hay vehículos.</td></tr>
            ) : (
              vehiculos.map((v) => (
                <tr key={v.id_vehiculo} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-800">{clientes.find((c) => c.id_cliente === v.id_cliente)?.nombre || `ID ${v.id_cliente}`}</td>
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{v.marca} {v.modelo}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{v.anio}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{v.color || v.motor || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{v.numero_serie || v.vin || '-'}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex gap-2 justify-end">
                      <button onClick={() => abrirHistorial(v)} className="text-sm text-slate-600 hover:text-slate-800" title="Ver historial">📋</button>
                      <button onClick={() => abrirEditar(v)} className="text-sm text-primary-600 hover:text-primary-700">Editar</button>
                      {user?.rol === 'ADMIN' && <button onClick={() => eliminarVehiculo(v)} className="text-sm text-red-600 hover:text-red-700">Eliminar</button>}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPaginas > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-slate-600">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, totalVehiculos)} de {totalVehiculos}</p>
          <div className="flex gap-2">
            <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Anterior</button>
            <span className="px-3 py-1 text-sm text-slate-700">Página {pagina} de {totalPaginas}</span>
            <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={`Historial — ${historialData?.vehiculo?.marca || ''} ${historialData?.vehiculo?.modelo || ''} ${historialData?.vehiculo?.anio || ''}`} abierto={modalHistorial} onCerrar={() => { setModalHistorial(false); setHistorialData(null) }}>
        {cargandoHistorial ? <p className="text-slate-500 py-4">Cargando historial...</p> : historialData ? (
          <div className="space-y-6 max-h-[70vh] overflow-y-auto">
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Datos</h3><div className="text-sm text-slate-600"><p><span className="font-medium">Cliente:</span> {historialData.vehiculo?.cliente_nombre || '-'}</p><p><span className="font-medium">Color:</span> {historialData.vehiculo?.color || '-'}</p><p><span className="font-medium">VIN:</span> {historialData.vehiculo?.vin || '-'}</p></div></div>
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Resumen</h3><div className="grid grid-cols-2 gap-2 text-sm"><div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Órdenes:</span> {historialData.resumen?.cantidad_ordenes ?? 0}</div><div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Ventas:</span> {historialData.resumen?.cantidad_ventas ?? 0}</div></div></div>
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes ({historialData.ordenes_trabajo?.length ?? 0})</h3>{(historialData.ordenes_trabajo?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin órdenes</p> : <table className="min-w-full text-sm"><thead><tr><th className="text-left py-1">Nº</th><th className="text-left py-1">Fecha</th><th className="text-left py-1">Estado</th><th className="text-right py-1">Total</th></tr></thead><tbody>{historialData.ordenes_trabajo.map((o) => <tr key={o.id}><td className="py-1">{o.numero_orden}</td><td>{o.fecha_ingreso ? new Date(o.fecha_ingreso).toLocaleDateString() : '-'}</td><td>{o.estado || '-'}</td><td className="text-right">${(o.total ?? 0).toFixed(2)}</td></tr>)}</tbody></table>}</div>
            <div><h3 className="text-sm font-semibold text-slate-700 mb-2">Ventas ({historialData.ventas?.length ?? 0})</h3>{(historialData.ventas?.length ?? 0) === 0 ? <p className="text-slate-500 text-sm">Sin ventas</p> : <table className="min-w-full text-sm"><thead><tr><th className="text-left py-1">ID</th><th className="text-left py-1">Fecha</th><th className="text-right py-1">Total</th><th className="text-right py-1">Pagado</th><th className="text-left py-1">Estado</th></tr></thead><tbody>{historialData.ventas.map((v) => <tr key={v.id_venta}><td className="py-1">{v.id_venta}</td><td>{v.fecha ? new Date(v.fecha).toLocaleDateString() : '-'}</td><td className="text-right">${(v.total ?? 0).toFixed(2)}</td><td className="text-right">${(v.total_pagado ?? 0).toFixed(2)}</td><td>{v.estado || '-'}</td></tr>)}</tbody></table>}</div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo={editando ? 'Editar vehículo' : 'Nuevo vehículo'} abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label><select value={form.id_cliente || ''} onChange={(e) => setForm({ ...form, id_cliente: e.target.value ? parseInt(e.target.value) : null })} required disabled={!!editando} className="w-full px-4 py-2 border border-slate-300 rounded-lg disabled:opacity-60"><option value="">Seleccionar cliente...</option>{clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}</select></div>
          <div className="grid grid-cols-2 gap-4"><div><label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label><input type="text" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} required placeholder="Ej: Nissan" className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div><div><label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label><input type="text" value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value })} required placeholder="Ej: Versa" className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div></div>
          <div className="grid grid-cols-2 gap-4"><div><label className="block text-sm font-medium text-slate-700 mb-1">Año *</label><input type="number" min={1900} max={2030} value={form.anio} onChange={(e) => setForm({ ...form, anio: e.target.value })} required className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div><div><label className="block text-sm font-medium text-slate-700 mb-1">VIN / Núm. serie</label><input type="text" value={form.numero_serie} onChange={(e) => setForm({ ...form, numero_serie: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div></div>
          <div><label className="block text-sm font-medium text-slate-700 mb-1">Color</label><input type="text" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} placeholder="Ej: Blanco, Negro" className="w-full px-4 py-2 border border-slate-300 rounded-lg" /></div>
          <div className="flex justify-end gap-2 pt-2"><button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button><button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Guardar'}</button></div>
        </form>
      </Modal>
    </div>
  )
}
