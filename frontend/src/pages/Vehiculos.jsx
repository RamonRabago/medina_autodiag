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
  const [modalEliminar, setModalEliminar] = useState(false)
  const [vehiculoAEliminar, setVehiculoAEliminar] = useState(null)
  const [datosEliminar, setDatosEliminar] = useState(null)
  const [motivoEliminacion, setMotivoEliminacion] = useState('')
  const [errorEliminar, setErrorEliminar] = useState('')
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [procesandoOrdenId, setProcesandoOrdenId] = useState(null)
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
      setErrorEliminar(err.response?.data?.detail || 'Error al cargar datos')
    }
  }

  const cancelarOrden = async (orden) => {
    if (orden.estado === 'ENTREGADA') return
    if (orden.estado === 'CANCELADA') return
    const motivo = window.prompt('Motivo de la cancelación (mín. 10 caracteres):', '')
    if (!motivo || motivo.trim().length < 10) {
      if (motivo !== null) alert('El motivo debe tener al menos 10 caracteres.')
      return
    }
    setProcesandoOrdenId(orden.id)
    try {
      await api.post(`/ordenes-trabajo/${orden.id}/cancelar`, null, { params: { motivo: motivo.trim() } })
      const res = await api.get(`/vehiculos/${vehiculoAEliminar.id_vehiculo}/historial`)
      setDatosEliminar(res.data)
    } catch (err) {
      const d = err.response?.data?.detail
      alert(Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : (typeof d === 'string' ? d : 'Error al cancelar'))
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
      const d = err.response?.data?.detail
      alert(Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : (typeof d === 'string' ? d : 'Error al eliminar orden'))
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
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      setErrorEliminar(Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : (typeof d === 'string' ? d : 'Error al eliminar'))
    } finally {
      setEnviandoEliminar(false)
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
                      {user?.rol === 'ADMIN' && <button onClick={() => abrirModalEliminar(v)} className="text-sm text-red-600 hover:text-red-700">Eliminar</button>}
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
              className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Órdenes de trabajo asociadas ({(datosEliminar?.ordenes_trabajo?.length ?? 0)})</h3>
            {!datosEliminar ? <p className="text-slate-500 text-sm">Cargando...</p> : (datosEliminar.ordenes_trabajo?.length ?? 0) === 0 ? (
              <p className="text-slate-500 text-sm">No hay órdenes asociadas.</p>
            ) : (
              <div className="border rounded-lg overflow-hidden">
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
                        <td className="px-3 py-2 text-slate-600">{o.fecha_ingreso ? new Date(o.fecha_ingreso).toLocaleDateString() : '-'}</td>
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
          <div className="flex justify-end gap-2 pt-2 border-t">
            <button type="button" onClick={() => { setModalEliminar(false); setVehiculoAEliminar(null); setDatosEliminar(null); setMotivoEliminacion('') }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">No eliminar</button>
            <button
              type="button"
              onClick={confirmarEliminarVehiculo}
              disabled={enviandoEliminar || !motivoEliminacion.trim() || motivoEliminacion.trim().length < 10 || (datosEliminar?.ordenes_trabajo?.length ?? 0) > 0}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {enviandoEliminar ? 'Eliminando...' : 'Eliminar vehículo'}
            </button>
          </div>
        </div>
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
