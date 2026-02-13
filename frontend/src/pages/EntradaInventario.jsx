import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { hoyStr } from '../utils/fechas'

export default function EntradaInventario() {
  const navigate = useNavigate()
  const { id } = useParams()
  const inputFotoRef = useRef(null)

  const [repuesto, setRepuesto] = useState(null)
  const [proveedores, setProveedores] = useState([])
  const [loading, setLoading] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [subiendoComprobante, setSubiendoComprobante] = useState(false)

  const [form, setForm] = useState({
    cantidad: 1,
    precio_unitario: '',
    fecha_adquisicion: hoyStr(),
    id_proveedor: '',
    numero_factura: '',
    imagen_comprobante_url: '',
    observaciones: '',
  })

  useEffect(() => {
    if (!id) {
      navigate('/inventario')
      return
    }
    Promise.all([
      api.get(`/repuestos/${id}`),
      api.get('/proveedores/', { params: { limit: 200 } }),
    ])
      .then(([r1, r2]) => {
        const r = r1.data
        setRepuesto(r)
        setForm((f) => ({
          ...f,
          precio_unitario: r.precio_compra ? String(r.precio_compra) : '',
          id_proveedor: r.id_proveedor ? String(r.id_proveedor) : '',
        }))
        const prov = r2.data
        setProveedores(Array.isArray(prov) ? prov : prov?.proveedores ?? [])
      })
      .catch(() => navigate('/inventario'))
      .finally(() => setLoading(false))
  }, [id, navigate])

  const handleSeleccionarComprobante = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSubiendoComprobante(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('archivo', file)
      const res = await api.post('/inventario/movimientos/upload-comprobante', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setForm((f) => ({ ...f, imagen_comprobante_url: res.data?.url ?? '' }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al subir comprobante')
    } finally {
      setSubiendoComprobante(false)
      e.target.value = ''
    }
  }

  const quitarComprobante = () => {
    setForm((f) => ({ ...f, imagen_comprobante_url: '' }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const cantidad = parseFloat(form.cantidad) || 1
    if (cantidad < 0.001) {
      setError('La cantidad debe ser al menos 0.001')
      return
    }
    setEnviando(true)
    try {
      await api.post('/inventario/movimientos/', {
        id_repuesto: parseInt(id),
        tipo_movimiento: 'ENTRADA',
        cantidad,
        precio_unitario: form.precio_unitario ? parseFloat(form.precio_unitario) : repuesto?.precio_compra || null,
        referencia: form.numero_factura?.trim() || null,
        motivo: form.observaciones?.trim() || null,
        id_proveedor: form.id_proveedor ? parseInt(form.id_proveedor) : null,
        imagen_comprobante_url: form.imagen_comprobante_url || null,
        fecha_adquisicion: form.fecha_adquisicion || null,
      })
      navigate('/inventario')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al registrar entrada')
    } finally {
      setEnviando(false)
    }
  }

  const costoTotal = (parseFloat(form.cantidad) || 0) * (parseFloat(form.precio_unitario) || 0)

  if (loading) return <p className="p-8 text-slate-500">Cargando...</p>
  if (!repuesto) return null

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 font-medium text-sm">
          ← Volver a Inventario
        </Link>
      </div>

      <h1 className="text-2xl font-bold text-slate-800 mb-2">Registrar entrada de inventario</h1>
      <p className="text-slate-600 mb-6">Agrega stock con evidencia de adquisición para auditoría.</p>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-4 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
        )}

        {/* Datos del producto */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Producto</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500">Código</p>
              <p className="font-medium text-slate-800">{repuesto.codigo}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Nombre</p>
              <p className="font-medium text-slate-800">{repuesto.nombre}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Stock actual</p>
              <p className="font-medium text-slate-800">{repuesto.stock_actual ?? 0} unidades</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Precio de compra actual</p>
              <p className="font-medium text-slate-800">${(Number(repuesto.precio_compra) || 0).toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Datos de la entrada */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Datos de la entrada</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Cantidad a agregar *</label>
              <input
                type="number"
                min={0.001}
                step="any"
                value={form.cantidad}
                onChange={(e) => setForm({ ...form, cantidad: Math.max(0.001, parseFloat(e.target.value) || 1) })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Precio unitario (costo de adquisición)</label>
              <input
                type="number"
                step={0.01}
                min={0}
                value={form.precio_unitario}
                onChange={(e) => setForm({ ...form, precio_unitario: e.target.value })}
                placeholder={repuesto.precio_compra ? String(repuesto.precio_compra) : '0.00'}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha de adquisición *</label>
              <input
                type="date"
                value={form.fecha_adquisicion}
                onChange={(e) => setForm({ ...form, fecha_adquisicion: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                required
              />
            </div>
            {costoTotal > 0 && (
              <div>
                <p className="text-xs text-slate-500">Costo total</p>
                <p className="font-semibold text-green-700">${costoTotal.toFixed(2)}</p>
              </div>
            )}
          </div>
        </div>

        {/* Origen */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Origen y comprobante</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Proveedor (preferido del repuesto)</label>
              <select
                value={form.id_proveedor}
                onChange={(e) => setForm({ ...form, id_proveedor: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Seleccionar</option>
                {proveedores.filter((p) => p.activo !== false).map((p) => (
                  <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nº factura / documento</label>
              <input
                type="text"
                value={form.numero_factura}
                onChange={(e) => setForm({ ...form, numero_factura: e.target.value })}
                placeholder="Ej: FACT-001, OC-123"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Imagen de comprobante (evidencia)</label>
              <p className="text-xs text-slate-500 mb-2">Foto o PDF de factura, recibo o orden de compra. JPG, PNG, WebP, GIF, PDF • Máx. 5 MB</p>
              {form.imagen_comprobante_url ? (
                <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
                  {form.imagen_comprobante_url.toLowerCase().endsWith('.pdf') ? (
                    <span className="text-2xl">📄</span>
                  ) : (
                    <img src={form.imagen_comprobante_url} alt="Comprobante" className="w-16 h-16 object-cover rounded border" onError={(e) => { e.target.style.display = 'none' }} />
                  )}
                  <span className="text-sm text-slate-600 flex-1 truncate">Comprobante adjunto</span>
                  <button type="button" onClick={quitarComprobante} className="text-sm text-red-600 hover:text-red-700">Eliminar</button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    ref={inputFotoRef}
                    type="file"
                    accept="image/*,.pdf"
                    onChange={handleSeleccionarComprobante}
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => inputFotoRef.current?.click()}
                    disabled={subiendoComprobante}
                    className="px-4 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-200 text-sm font-medium disabled:opacity-50"
                  >
                    {subiendoComprobante ? 'Subiendo...' : '📎 Adjuntar comprobante'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Observaciones */}
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones (opcional)</label>
          <textarea
            value={form.observaciones}
            onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
            rows={3}
            placeholder="Ej: Compra directa, ajuste de inventario físico, devolución de cliente..."
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div className="flex gap-3 justify-end">
          <Link to="/inventario" className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
            Cancelar
          </Link>
          <button
            type="submit"
            disabled={enviando}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50"
          >
            {enviando ? 'Registrando...' : `Registrar entrada (+${form.cantidad})`}
          </button>
        </div>
      </form>
    </div>
  )
}
