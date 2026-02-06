import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useInvalidateQueries } from '../hooks/useApi'
import SearchableRepuestoSelect from '../components/SearchableRepuestoSelect'

const ALLOWED_EXT = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf']

export default function NuevaOrdenCompra() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const invalidate = useInvalidateQueries()

  const [proveedores, setProveedores] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [form, setForm] = useState({
    id_proveedor: '',
    observaciones: '',
    items: [{ tipo: 'existente', id_repuesto: '', codigo_nuevo: '', nombre_nuevo: '', cantidad_solicitada: 1, precio_unitario_estimado: 0 }],
    comprobante: null,
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const puedeGestionar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  useEffect(() => {
    Promise.all([
      api.get('/proveedores/', { params: { limit: 500, activo: true } }),
      api.get('/repuestos/', { params: { limit: 500, activo: true } }),
    ]).then(([rProv, rRep]) => {
      setProveedores(rProv.data?.proveedores ?? rProv.data ?? [])
      setRepuestos(rRep.data?.repuestos ?? rRep.data ?? [])
      const p = rProv.data?.proveedores ?? rProv.data ?? []
      if (p.length && !form.id_proveedor) setForm((f) => ({ ...f, id_proveedor: p[0]?.id_proveedor ?? '' }))
    }).catch(() => {})
  }, [])

  const agregarItem = () => {
    setForm((f) => ({ ...f, items: [...f.items, { tipo: 'existente', id_repuesto: '', codigo_nuevo: '', nombre_nuevo: '', cantidad_solicitada: 1, precio_unitario_estimado: 0 }] }))
  }

  const quitarItem = (idx) => {
    setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== idx) }))
  }

  const actualizarItem = (idx, campo, valor) => {
    setForm((f) => ({
      ...f,
      items: f.items.map((it, i) => (i === idx ? { ...it, [campo]: valor } : it)),
    }))
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) {
      setForm((f) => ({ ...f, comprobante: null }))
      return
    }
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED_EXT.includes(ext)) {
      setError(`Formato no permitido. Use: ${ALLOWED_EXT.join(', ')}`)
      setForm((f) => ({ ...f, comprobante: null }))
      e.target.value = ''
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('El archivo no debe superar 5 MB')
      setForm((f) => ({ ...f, comprobante: null }))
      e.target.value = ''
      return
    }
    setError('')
    setForm((f) => ({ ...f, comprobante: file }))
  }

  const crearOrden = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.id_proveedor) {
      setError('Selecciona un proveedor')
      return
    }
    const items = form.items
      .filter((it) => {
        const tieneRepuesto = it.tipo === 'existente' ? it.id_repuesto : (it.codigo_nuevo?.trim() && it.nombre_nuevo?.trim())
        return tieneRepuesto && it.cantidad_solicitada > 0 && (it.precio_unitario_estimado ?? 0) >= 0
      })
    if (items.length === 0) {
      setError('Agrega al menos un repuesto con cantidad y precio')
      return
    }

    setEnviando(true)
    try {
      let comprobanteUrl = null
      if (form.comprobante) {
        const fd = new FormData()
        fd.append('archivo', form.comprobante)
        const up = await api.post('/inventario/movimientos/upload-comprobante', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        comprobanteUrl = up.data?.url ?? null
      }

      await api.post('/ordenes-compra/', {
        id_proveedor: parseInt(form.id_proveedor),
        observaciones: form.observaciones?.trim() || null,
        comprobante_url: comprobanteUrl,
        items: items.map((it) => {
          const base = {
            cantidad_solicitada: parseInt(it.cantidad_solicitada) || 1,
            precio_unitario_estimado: parseFloat(it.precio_unitario_estimado) || 0,
          }
          if (it.tipo === 'existente') {
            return { ...base, id_repuesto: parseInt(it.id_repuesto) }
          }
          return { ...base, codigo_nuevo: it.codigo_nuevo?.trim() || '', nombre_nuevo: it.nombre_nuevo?.trim() || '' }
        }),
      })
      invalidate(['ordenes-compra'])
      navigate('/ordenes-compra')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear orden')
    } finally {
      setEnviando(false)
    }
  }

  if (!puedeGestionar) {
    return (
      <div>
        <p className="text-slate-500">No tienes permiso para crear órdenes de compra.</p>
        <Link to="/ordenes-compra" className="text-primary-600 hover:underline">Volver a órdenes</Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/ordenes-compra" className="text-slate-600 hover:text-slate-800">← Órdenes de compra</Link>
        <h1 className="text-2xl font-bold text-slate-800">Nueva orden de compra</h1>
      </div>

      <form onSubmit={crearOrden} className="bg-white rounded-lg shadow p-6 space-y-6">
        {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Proveedor *</label>
          <select
            value={form.id_proveedor}
            onChange={(e) => setForm({ ...form, id_proveedor: e.target.value })}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            required
          >
            <option value="">Seleccionar...</option>
            {proveedores.map((p) => (
              <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
          <textarea
            value={form.observaciones}
            onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
            rows={3}
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="Notas adicionales sobre la orden"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Comprobante de compra (imagen o PDF)</label>
          <div className="flex flex-wrap gap-3 items-center">
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.gif,.pdf"
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
            />
            {form.comprobante && (
              <span className="text-sm text-slate-600">
                {form.comprobante.name}
                <button type="button" onClick={() => setForm((f) => ({ ...f, comprobante: null }))} className="ml-2 text-red-500 hover:text-red-700">
                  ✕ Quitar
                </button>
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">Formatos: JPG, PNG, PDF. Máx. 5 MB</p>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-sm font-medium text-slate-700">Repuestos *</label>
            <button type="button" onClick={agregarItem} className="text-sm text-primary-600 hover:text-primary-700 font-medium">+ Agregar repuesto</button>
          </div>
          <div className="space-y-3 border border-slate-200 rounded-lg p-4 bg-slate-50/50">
            {form.items.map((it, idx) => (
              <div key={idx} className="space-y-2 p-3 bg-white rounded-lg border border-slate-100">
                <div className="flex gap-2 items-center flex-wrap">
                  <select
                    value={it.tipo}
                    onChange={(e) => actualizarItem(idx, 'tipo', e.target.value)}
                    className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  >
                    <option value="existente">Del catálogo</option>
                    <option value="nuevo">Repuesto nuevo</option>
                  </select>
                  {it.tipo === 'existente' ? (
                    <SearchableRepuestoSelect
                      repuestos={repuestos}
                      value={it.id_repuesto}
                      onChange={(v) => actualizarItem(idx, 'id_repuesto', v)}
                      placeholder="Escribe para buscar repuesto..."
                      required={idx === 0}
                    />
                  ) : (
                    <>
                      <input
                        type="text"
                        placeholder="Código"
                        value={it.codigo_nuevo}
                        onChange={(e) => actualizarItem(idx, 'codigo_nuevo', e.target.value)}
                        className="flex-1 min-w-[100px] px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                      <input
                        type="text"
                        placeholder="Nombre"
                        value={it.nombre_nuevo}
                        onChange={(e) => actualizarItem(idx, 'nombre_nuevo', e.target.value)}
                        className="flex-1 min-w-[180px] px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                    </>
                  )}
                  <input
                    type="number"
                    min={1}
                    value={it.cantidad_solicitada}
                    onChange={(e) => actualizarItem(idx, 'cantidad_solicitada', parseInt(e.target.value) || 1)}
                    className="w-20 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                  <input
                    type="number"
                    step={0.01}
                    min={0}
                    placeholder="Precio est."
                    value={it.precio_unitario_estimado}
                    onChange={(e) => actualizarItem(idx, 'precio_unitario_estimado', parseFloat(e.target.value) || 0)}
                    className="w-28 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                  <button type="button" onClick={() => quitarItem(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded" title="Quitar">✕</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
          <Link to="/ordenes-compra" className="px-5 py-2.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium">
            Cancelar
          </Link>
          <button type="submit" disabled={enviando} className="px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium">
            {enviando ? 'Creando...' : 'Crear orden'}
          </button>
        </div>
      </form>
    </div>
  )
}
