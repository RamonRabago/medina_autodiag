import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

const PERIODOS = [
  { value: 'SEMANAL', label: 'Semanal' },
  { value: 'QUINCENAL', label: 'Quincenal' },
  { value: 'MENSUAL', label: 'Mensual' },
]

export default function Prestamos() {
  const { user } = useAuth()
  const [prestamos, setPrestamos] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalNuevo, setModalNuevo] = useState(false)
  const [modalDescuento, setModalDescuento] = useState(false)
  const [prestamoDescuento, setPrestamoDescuento] = useState(null)
  const [prestamoDetalle, setPrestamoDetalle] = useState(null)
  const [form, setForm] = useState({ id_usuario: '', monto_total: '', descuento_por_periodo: '', periodo_descuento: 'SEMANAL', fecha_inicio: new Date().toISOString().slice(0, 10), observaciones: '' })
  const [formDescuento, setFormDescuento] = useState({ monto: '', fecha_periodo: new Date().toISOString().slice(0, 10) })
  const [filtroUsuario, setFiltroUsuario] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  const esAdmin = user?.rol === 'ADMIN'

  const cargar = () => {
    setLoading(true)
    const params = {}
    if (filtroUsuario) params.id_usuario = filtroUsuario
    if (filtroEstado) params.estado = filtroEstado
    api.get('/prestamos-empleados/', { params })
      .then((r) => setPrestamos(Array.isArray(r.data) ? r.data : []))
      .catch(() => setPrestamos([]))
      .finally(() => setLoading(false))
  }

  const cargarUsuarios = () => {
    api.get('/usuarios/').then((r) => setUsuarios(Array.isArray(r.data) ? r.data : [])).catch(() => setUsuarios([]))
  }

  useEffect(() => { cargar() }, [filtroUsuario, filtroEstado])
  useEffect(() => { if (esAdmin) cargarUsuarios() }, [esAdmin])

  const abrirNuevo = () => {
    setForm({ id_usuario: usuarios[0]?.id_usuario || '', monto_total: '', descuento_por_periodo: '', periodo_descuento: 'SEMANAL', fecha_inicio: new Date().toISOString().slice(0, 10), observaciones: '' })
    setError('')
    setModalNuevo(true)
  }

  const guardarPrestamo = async () => {
    setError('')
    if (!form.id_usuario || !form.monto_total || !form.descuento_por_periodo) {
      setError('Empleado, monto total y descuento por periodo son obligatorios')
      return
    }
    if (parseFloat(form.monto_total) <= 0 || parseFloat(form.descuento_por_periodo) <= 0) {
      setError('Montos deben ser mayores a 0')
      return
    }
    setEnviando(true)
    try {
      await api.post('/prestamos-empleados/', {
        id_usuario: parseInt(form.id_usuario),
        monto_total: parseFloat(form.monto_total),
        descuento_por_periodo: parseFloat(form.descuento_por_periodo),
        periodo_descuento: form.periodo_descuento,
        fecha_inicio: form.fecha_inicio,
        observaciones: form.observaciones?.trim() || null,
      })
      setModalNuevo(false)
      cargar()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const abrirAplicarDescuento = (p) => {
    setPrestamoDescuento(p)
    setFormDescuento({ monto: p?.descuento_por_periodo || '', fecha_periodo: new Date().toISOString().slice(0, 10) })
    setError('')
    setModalDescuento(true)
  }

  const aplicarDescuento = async () => {
    if (!prestamoDescuento) return
    setError('')
    if (!formDescuento.monto || parseFloat(formDescuento.monto) <= 0) {
      setError('Monto obligatorio y mayor a 0')
      return
    }
    setEnviando(true)
    try {
      await api.post(`/prestamos-empleados/${prestamoDescuento.id}/aplicar-descuento`, {
        monto: parseFloat(formDescuento.monto),
        fecha_periodo: formDescuento.fecha_periodo,
      })
      setModalDescuento(false)
      setPrestamoDescuento(null)
      cargar()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al aplicar descuento')
    } finally {
      setEnviando(false)
    }
  }

  const verDetalle = (p) => {
    api.get(`/prestamos-empleados/${p.id}`)
      .then((r) => setPrestamoDetalle(r.data))
      .catch(() => setPrestamoDetalle(null))
  }

  const cerrarDetalle = () => setPrestamoDetalle(null)

  const formatearMoneda = (n) => n != null ? `$${Number(n).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '-'
  const formatearFecha = (d) => d ? new Date(d).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' }) : '-'

  if (!esAdmin) {
    return (
      <div className="p-8 text-center text-slate-600">
        No tienes permisos. Ve a <Link to="/mi-nomina" className="text-primary-600 underline">Mi nómina</Link>.
      </div>
    )
  }

  return (
    <div className="min-h-0 flex flex-col">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Préstamos a empleados</h1>
      <div className="bg-white rounded-lg shadow border border-slate-200">
        <div className="p-4 border-b flex flex-wrap justify-between items-center gap-4">
          <div className="flex flex-wrap gap-2">
            <select value={filtroUsuario} onChange={(e) => setFiltroUsuario(e.target.value)} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <option value="">Todos</option>
              {usuarios.filter(u => u.rol !== 'ADMIN').map((u) => <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>)}
            </select>
            <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
              <option value="">Todos</option>
              <option value="ACTIVO">Activos</option>
              <option value="LIQUIDADO">Liquidados</option>
              <option value="CANCELADO">Cancelados</option>
            </select>
          </div>
          <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">+ Nuevo préstamo</button>
        </div>
        {loading ? (
          <p className="p-8 text-center text-slate-500">Cargando...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Empleado</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Monto</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Descuento/periodo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Periodo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Saldo</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {prestamos.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">No hay préstamos.</td></tr>
                ) : prestamos.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">{p.empleado_nombre || '-'}</td>
                    <td className="px-4 py-3 text-sm text-right">{formatearMoneda(p.monto_total)}</td>
                    <td className="px-4 py-3 text-sm text-right">{formatearMoneda(p.descuento_por_periodo)}</td>
                    <td className="px-4 py-3 text-sm">{PERIODOS.find(x => x.value === p.periodo_descuento)?.label || p.periodo_descuento}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">{formatearMoneda(p.saldo_pendiente)}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${p.estado === 'ACTIVO' ? 'bg-green-100 text-green-800' : p.estado === 'LIQUIDADO' ? 'bg-blue-100 text-blue-800' : 'bg-slate-200 text-slate-600'}`}>{p.estado}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => verDetalle(p)} className="px-2 py-1 text-sm text-slate-600 hover:text-slate-800 rounded mr-1">📋</button>
                      {p.estado === 'ACTIVO' && Number(p.saldo_pendiente) > 0 && (
                        <button onClick={() => abrirAplicarDescuento(p)} className="px-2 py-1 text-sm text-primary-600 hover:text-primary-700 font-medium rounded">$</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal titulo="Nuevo préstamo" abierto={modalNuevo} onCerrar={() => setModalNuevo(false)}>
        <div className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Empleado *</label>
            <select value={form.id_usuario} onChange={(e) => setForm({ ...form, id_usuario: e.target.value })} className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" required>
              <option value="">Selecciona empleado</option>
              {usuarios.filter(u => u.rol !== 'ADMIN').map((u) => <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Monto total *</label>
              <input type="number" step="0.01" min="0" value={form.monto_total} onChange={(e) => setForm({ ...form, monto_total: e.target.value })} placeholder="0.00" className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Descuento por periodo *</label>
              <input type="number" step="0.01" min="0" value={form.descuento_por_periodo} onChange={(e) => setForm({ ...form, descuento_por_periodo: e.target.value })} placeholder="0.00" className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Periodo</label>
              <select value={form.periodo_descuento} onChange={(e) => setForm({ ...form, periodo_descuento: e.target.value })} className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm">
                {PERIODOS.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha inicio</label>
              <input type="date" value={form.fecha_inicio} onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })} className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <input type="text" value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} placeholder="Opcional" className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalNuevo(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="button" onClick={guardarPrestamo} disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Crear'}</button>
          </div>
        </div>
      </Modal>

      <Modal titulo={prestamoDescuento ? `Aplicar descuento - ${prestamoDescuento.empleado_nombre}` : 'Aplicar descuento'} abierto={modalDescuento} onCerrar={() => { setModalDescuento(false); setPrestamoDescuento(null) }}>
        <div className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <p className="text-sm text-slate-600">Registra el descuento aplicado. Si faltó, se descuenta igual.</p>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step="0.01" min="0" value={formDescuento.monto} onChange={(e) => setFormDescuento({ ...formDescuento, monto: e.target.value })} className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha periodo (primer día)</label>
            <input type="date" value={formDescuento.fecha_periodo} onChange={(e) => setFormDescuento({ ...formDescuento, fecha_periodo: e.target.value })} className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalDescuento(false); setPrestamoDescuento(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="button" onClick={aplicarDescuento} disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Aplicando...' : 'Aplicar'}</button>
          </div>
        </div>
      </Modal>

      <Modal titulo="Detalle préstamo" abierto={!!prestamoDetalle} onCerrar={cerrarDetalle} size="lg">
        {prestamoDetalle && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-slate-500">Empleado:</span> {prestamoDetalle.empleado_nombre}</div>
              <div><span className="text-slate-500">Monto:</span> {formatearMoneda(prestamoDetalle.monto_total)}</div>
              <div><span className="text-slate-500">Descuento/periodo:</span> {formatearMoneda(prestamoDetalle.descuento_por_periodo)}</div>
              <div><span className="text-slate-500">Saldo pendiente:</span> <span className="font-semibold">{formatearMoneda(prestamoDetalle.saldo_pendiente)}</span></div>
            </div>
            {prestamoDetalle.descuentos?.length > 0 && (
              <div>
                <h3 className="font-medium mb-2">Historial descuentos</h3>
                <div className="max-h-40 overflow-y-auto border rounded">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-50"><tr><th className="px-3 py-2 text-left">Fecha</th><th className="px-3 py-2 text-right">Monto</th></tr></thead>
                    <tbody>
                      {prestamoDetalle.descuentos.map((d) => (
                        <tr key={d.id} className="border-t"><td className="px-3 py-2">{formatearFecha(d.fecha_periodo)}</td><td className="px-3 py-2 text-right">{formatearMoneda(d.monto_descontado)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
