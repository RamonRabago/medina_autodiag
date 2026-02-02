import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Clientes() {
  const { user } = useAuth()
  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({ nombre: '', telefono: '', email: '', direccion: '', rfc: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalVehiculo, setModalVehiculo] = useState(false)
  const [clienteParaVehiculo, setClienteParaVehiculo] = useState(null)
  const [formVehiculo, setFormVehiculo] = useState({ marca: '', modelo: '', anio: new Date().getFullYear(), numero_serie: '' })
  const [enviandoVehiculo, setEnviandoVehiculo] = useState(false)
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [totalClientes, setTotalClientes] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [modalHistorial, setModalHistorial] = useState(false)
  const [historialData, setHistorialData] = useState(null)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const limit = 20

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
    }).catch(() => setClientes([]))
  }

  useEffect(() => { cargar() }, [pagina, buscar])
  useEffect(() => {
    setLoading(false)
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
    setModalHistorial(true)
    setCargandoHistorial(true)
    try {
      const res = await api.get(`/clientes/${c.id_cliente}/historial`)
      setHistorialData(res.data)
    } catch (err) {
      setHistorialData(null)
      alert(err.response?.data?.detail || 'Error al cargar historial')
    } finally {
      setCargandoHistorial(false)
    }
  }

  const abrirAgregarVehiculo = (c) => {
    setClienteParaVehiculo(c)
    setFormVehiculo({ marca: '', modelo: '', anio: new Date().getFullYear(), numero_serie: '' })
    setModalVehiculo(true)
  }

  const handleEliminar = async (c) => {
    if (!window.confirm(`¿Eliminar al cliente "${c.nombre}"?`)) return
    try {
      await api.delete(`/clientes/${c.id_cliente}`)
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
      if (editando) {
        await api.put(`/clientes/${editando.id_cliente}`, form)
      } else {
        await api.post('/clientes/', form)
      }
      cargar()
      setModalAbierto(false)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg.map((m) => m.msg).join(', ') : msg)
    } finally {
      setEnviando(false)
    }
  }

  const handleVehiculoSubmit = async (e) => {
    e.preventDefault()
    setEnviandoVehiculo(true)
    try {
      await api.post('/vehiculos/', {
        id_cliente: clienteParaVehiculo.id_cliente,
        marca: formVehiculo.marca.trim(),
        modelo: formVehiculo.modelo.trim(),
        anio: parseInt(formVehiculo.anio),
        numero_serie: formVehiculo.numero_serie?.trim() || null,
      })
      setModalVehiculo(false)
      setClienteParaVehiculo(null)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al agregar vehículo')
    } finally {
      setEnviandoVehiculo(false)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Clientes</h1>
        <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Nuevo cliente</button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <input
          type="text"
          placeholder="Buscar por nombre, teléfono, email o RFC..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm flex-1 min-w-[200px]"
        />
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
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
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1 flex-wrap">
                      <button onClick={() => abrirHistorial(c)} className="text-sm text-slate-600 hover:text-slate-800" title="Ver historial">📋</button>
                      <button onClick={() => abrirAgregarVehiculo(c)} className="text-sm text-slate-600 hover:text-slate-800" title="Agregar vehículo">🚗</button>
                      <button onClick={() => abrirEditar(c)} className="text-sm text-primary-600 hover:text-primary-700">Editar</button>
                      {user?.rol === 'ADMIN' && <button onClick={() => handleEliminar(c)} className="text-sm text-red-600 hover:text-red-800" title="Eliminar cliente">Eliminar</button>}
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
          <p className="text-sm text-slate-600">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, totalClientes)} de {totalClientes}</p>
          <div className="flex gap-2">
            <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Anterior</button>
            <span className="px-3 py-1 text-sm text-slate-700">Página {pagina} de {totalPaginas}</span>
            <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={`Historial — ${historialData?.cliente?.nombre || 'Cliente'}`} abierto={modalHistorial} onCerrar={() => { setModalHistorial(false); setHistorialData(null) }}>
        {cargandoHistorial ? <p className="text-slate-500 py-4">Cargando historial...</p> : historialData ? (
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
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm">
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Ventas:</span> {historialData.resumen?.cantidad_ventas ?? 0}</div>
                <div className="p-2 bg-slate-50 rounded"><span className="text-slate-500">Total $:</span> ${(historialData.resumen?.total_ventas ?? 0).toFixed(2)}</div>
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
                        <tr key={v.id_venta}><td className="py-1">{v.id_venta}</td><td>{v.fecha ? new Date(v.fecha).toLocaleDateString() : '-'}</td><td className="text-right">${(v.total ?? 0).toFixed(2)}</td><td className="text-right">${(v.total_pagado ?? 0).toFixed(2)}</td><td>{v.estado || '-'}</td></tr>
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
                        <tr key={o.id}><td className="py-1">{o.numero_orden}</td><td>{o.vehiculo || '-'}</td><td>{o.estado || '-'}</td><td className="text-right">${(o.total ?? 0).toFixed(2)}</td></tr>
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
                        <tr key={c.id_cita}><td className="py-1">{c.fecha_hora ? new Date(c.fecha_hora).toLocaleString() : '-'}</td><td>{c.tipo || '-'}</td><td>{c.estado || '-'}</td><td>{c.motivo || '-'}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal titulo={editando ? 'Editar cliente' : 'Nuevo cliente'} abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
            <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required minLength={3} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono</label>
            <input type="text" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} placeholder="10 dígitos" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Dirección</label>
            <input type="text" value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">RFC (opcional)</label>
            <input type="text" value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value })} placeholder="12 o 13 caracteres" maxLength={13} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo={`Agregar vehículo para ${clienteParaVehiculo?.nombre || ''}`} abierto={modalVehiculo} onCerrar={() => { setModalVehiculo(false); setClienteParaVehiculo(null) }}>
        <form onSubmit={handleVehiculoSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label>
              <input type="text" value={formVehiculo.marca} onChange={(e) => setFormVehiculo({ ...formVehiculo, marca: e.target.value })} required placeholder="Ej: Nissan" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label>
              <input type="text" value={formVehiculo.modelo} onChange={(e) => setFormVehiculo({ ...formVehiculo, modelo: e.target.value })} required placeholder="Ej: Versa" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Año *</label>
              <input type="number" min={1900} max={2030} value={formVehiculo.anio} onChange={(e) => setFormVehiculo({ ...formVehiculo, anio: e.target.value })} required className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">VIN / Núm. serie</label>
              <input type="text" value={formVehiculo.numero_serie} onChange={(e) => setFormVehiculo({ ...formVehiculo, numero_serie: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalVehiculo(false); setClienteParaVehiculo(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviandoVehiculo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviandoVehiculo ? 'Guardando...' : 'Agregar'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
