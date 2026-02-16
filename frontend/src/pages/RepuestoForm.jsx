import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { normalizeDetail } from '../utils/toast'

const UNIDADES = ['PZA', 'LT', 'KG', 'CJA', 'PAR', 'SET']

export default function RepuestoForm() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { id } = useParams()
  const editando = !!id
  const puedeEditar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  const [form, setForm] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
    imagen_url: '',
    comprobante_url: '',
    id_categoria: '',
    id_proveedor: '',
    stock_actual: 0,
    stock_minimo: 5,
    stock_maximo: 100,
    ubicacion: '',
    id_estante: '',
    id_nivel: '',
    id_fila: '',
    precio_compra: '',
    precio_venta: '',
    marca: '',
    modelo_compatible: '',
    unidad_medida: 'PZA',
    activo: true,
    es_consumible: false,
  })
  const [categorias, setCategorias] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [ubicaciones, setUbicaciones] = useState([])
  const [estantes, setEstantes] = useState([])
  const [niveles, setNiveles] = useState([])
  const [filas, setFilas] = useState([])
  const [bodegaSeleccionada, setBodegaSeleccionada] = useState('')
  const [ubicacionSeleccionada, setUbicacionSeleccionada] = useState('')
  const [loading, setLoading] = useState(editando)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [subiendoFoto, setSubiendoFoto] = useState(false)
  const [subiendoComprobante, setSubiendoComprobante] = useState(false)
  const inputFotoRef = useRef(null)
  const inputComprobanteRef = useRef(null)
  const [imagenAmpliada, setImagenAmpliada] = useState(null)
  const [compatibilidades, setCompatibilidades] = useState([])
  const [nuevaCompat, setNuevaCompat] = useState({ marca: '', modelo: '', anio_desde: '', anio_hasta: '', motor: '' })
  const [config, setConfig] = useState({ markup_porcentaje: 20 })

  useEffect(() => {
    api.get('/config').then((r) => setConfig(r.data || { markup_porcentaje: 20 })).catch(() => {})
  }, [])

  const aplicarMarkup = () => {
    const pc = parseFloat(form.precio_compra)
    if (!pc || pc <= 0) return
    const markup = 1 + (config.markup_porcentaje || 20) / 100
    const pv = Math.round(pc * markup * 100) / 100
    setForm((f) => ({ ...f, precio_venta: String(pv) }))
  }

  useEffect(() => {
    Promise.all([
      api.get('/categorias-repuestos/'),
      api.get('/proveedores/', { params: { limit: 200 } }),
      api.get('/bodegas/', { params: { limit: 200 } }),
      api.get('/ubicaciones/', { params: { limit: 500 } }),
      api.get('/estantes/', { params: { limit: 500 } }),
      api.get('/niveles/', { params: { limit: 100 } }),
      api.get('/filas/', { params: { limit: 100 } }),
    ]).then(([r1, r2, r3, r4, r5, r6, r7]) => {
      setError('')
      setCategorias(Array.isArray(r1.data) ? r1.data : [])
      setProveedores(Array.isArray(r2.data) ? r2.data : r2.data?.proveedores ?? [])
      setBodegas(Array.isArray(r3.data) ? r3.data : [])
      setUbicaciones(Array.isArray(r4.data) ? r4.data : [])
      setEstantes(Array.isArray(r5.data) ? r5.data : [])
      setNiveles(Array.isArray(r6.data) ? r6.data : [])
      setFilas(Array.isArray(r7.data) ? r7.data : [])
    }).catch((err) => { setError(normalizeDetail(err.response?.data?.detail) || 'Error al cargar datos') })
  }, [])

  const cargarCompatibilidades = () => {
    if (editando && id) {
      api.get(`/repuestos/${id}/compatibilidad`)
        .then((r) => { setCompatibilidades(Array.isArray(r.data) ? r.data : []); setError('') })
        .catch((err) => { setError(normalizeDetail(err.response?.data?.detail) || 'Error al cargar compatibilidades') })
    }
  }

  useEffect(() => {
    if (editando && id) {
      setLoading(true)
      api.get(`/repuestos/${id}`)
        .then((r) => {
          const x = r.data
          setForm({
            codigo: x.codigo || '',
            nombre: x.nombre || '',
            descripcion: x.descripcion || '',
            imagen_url: x.imagen_url || '',
            comprobante_url: x.comprobante_url || '',
            id_categoria: x.id_categoria ?? '',
            id_proveedor: x.id_proveedor ?? '',
            stock_actual: x.stock_actual ?? 0,
            stock_minimo: x.stock_minimo ?? 5,
            stock_maximo: x.stock_maximo ?? 100,
            ubicacion: x.ubicacion || '',
            id_estante: x.id_estante ?? '',
            id_nivel: x.id_nivel ?? '',
            id_fila: x.id_fila ?? '',
            precio_compra: x.precio_compra ?? '',
            precio_venta: x.precio_venta ?? '',
            marca: x.marca || '',
            modelo_compatible: x.modelo_compatible || '',
            unidad_medida: x.unidad_medida || 'PZA',
            activo: x.activo !== false,
            es_consumible: !!x.es_consumible,
          })
          if (x.id_ubicacion) setUbicacionSeleccionada(String(x.id_ubicacion))
        })
        .catch(() => navigate('/inventario'))
        .finally(() => setLoading(false))
      cargarCompatibilidades()
    }
  }, [editando, id, navigate])

  const agregarCompatibilidad = async (e) => {
    e?.preventDefault()
    if (!nuevaCompat.marca?.trim() || !nuevaCompat.modelo?.trim()) return
    try {
      await api.post(`/repuestos/${id}/compatibilidad`, {
        marca: nuevaCompat.marca.trim(),
        modelo: nuevaCompat.modelo.trim(),
        anio_desde: nuevaCompat.anio_desde ? parseInt(nuevaCompat.anio_desde) : null,
        anio_hasta: nuevaCompat.anio_hasta ? parseInt(nuevaCompat.anio_hasta) : null,
        motor: nuevaCompat.motor?.trim() || null,
      })
      setNuevaCompat({ marca: '', modelo: '', anio_desde: '', anio_hasta: '', motor: '' })
      cargarCompatibilidades()
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al agregar compatibilidad')
    }
  }

  const quitarCompatibilidad = async (idCompat) => {
    try {
      await api.delete(`/repuestos/${id}/compatibilidad/${idCompat}`)
      cargarCompatibilidades()
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al quitar')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.codigo.trim() || !form.nombre.trim()) {
      setError('Código y nombre son obligatorios')
      return
    }
    const pc = parseFloat(form.precio_compra)
    const pv = parseFloat(form.precio_venta)
    if (isNaN(pc) || pc < 0 || isNaN(pv) || pv < 0) {
      setError('Precios deben ser números válidos ≥ 0')
      return
    }
    if (pv < pc) {
      setError('El precio de venta debe ser mayor o igual al de compra')
      return
    }
    setEnviando(true)
    try {
      const payload = {
        codigo: form.codigo.trim().toUpperCase(),
        nombre: form.nombre.trim(),
        descripcion: form.descripcion?.trim() || null,
        id_categoria: form.id_categoria ? parseInt(form.id_categoria) : null,
        id_proveedor: form.id_proveedor ? parseInt(form.id_proveedor) : null,
        stock_minimo: parseFloat(form.stock_minimo) || 5,
        stock_maximo: parseFloat(form.stock_maximo) || 100,
        ubicacion: form.ubicacion?.trim() || null,
        id_ubicacion: ubicacionSeleccionada ? parseInt(ubicacionSeleccionada) : null,
        id_estante: form.id_estante ? parseInt(form.id_estante) : null,
        id_nivel: form.id_nivel ? parseInt(form.id_nivel) : null,
        id_fila: form.id_fila ? parseInt(form.id_fila) : null,
        imagen_url: form.imagen_url?.trim() || null,
        comprobante_url: form.comprobante_url?.trim() || null,
        precio_compra: pc,
        precio_venta: pv,
        marca: form.marca?.trim() || null,
        modelo_compatible: form.modelo_compatible?.trim() || null,
        unidad_medida: form.unidad_medida || 'PZA',
        activo: form.activo,
        es_consumible: !!form.es_consumible,
      }
      if (editando) {
        await api.put(`/repuestos/${id}`, payload)
      } else {
        payload.stock_actual = parseFloat(form.stock_actual) || 0
        await api.post('/repuestos/', payload)
      }
      navigate('/inventario')
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const handleSeleccionarFoto = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !file.type.startsWith('image/')) return
    setSubiendoFoto(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('archivo', file)
      const res = await api.post('/repuestos/upload-imagen', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setForm((f) => ({ ...f, imagen_url: res.data?.url ?? '' }))
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al subir la imagen')
    } finally {
      setSubiendoFoto(false)
      e.target.value = ''
    }
  }

  const handleSeleccionarComprobante = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const ext = (file.name || '').toLowerCase().split('.').pop()
    const permitidos = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf']
    if (!permitidos.includes(ext)) {
      setError('Formato no permitido. Use JPG, PNG, WebP, GIF o PDF.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('El archivo no debe superar 5 MB')
      return
    }
    setSubiendoComprobante(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('archivo', file)
      const res = await api.post('/repuestos/upload-comprobante', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setForm((f) => ({ ...f, comprobante_url: res.data?.url ?? '' }))
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al subir el comprobante')
    } finally {
      setSubiendoComprobante(false)
      e.target.value = ''
    }
  }

  useEffect(() => {
    if (editando && form.id_estante && estantes.length > 0 && ubicaciones.length > 0) {
      const e = estantes.find(ee => ee.id === parseInt(form.id_estante))
      if (e && e.id_ubicacion) {
        const u = ubicaciones.find(uu => uu.id === e.id_ubicacion)
        if (u) {
          setBodegaSeleccionada(String(u.id_bodega))
          setUbicacionSeleccionada(String(e.id_ubicacion))
        }
      }
    }
  }, [editando, form.id_estante, estantes, ubicaciones])

  if (!puedeEditar) {
    navigate('/inventario')
    return null
  }

  if (loading && editando) return <p className="p-8 text-slate-500">Cargando...</p>

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6 flex items-center gap-4">
        <Link
          to="/inventario"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-100 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-200 hover:border-slate-400 transition-colors shadow-sm"
        >
          ← Volver a Inventario
        </Link>
        <h1 className="text-2xl font-bold text-slate-800">
          {editando ? 'Editar repuesto' : 'Nuevo repuesto'}
        </h1>
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Datos básicos</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>
                <input type="text" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="Ej: MOT-001" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
                <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: Aceite Motor 10W-40" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Descripción (opcional)</label>
                <textarea value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} rows={2} placeholder="Descripción breve" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 placeholder-slate-400" />
              </div>
            </div>

          {/* Foto */}
          <div className="pt-4 border-t border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Foto del producto</h2>
            <div className="flex flex-wrap gap-6 items-start">
            {form.imagen_url?.trim() ? (
              <>
                <div>
                  <button type="button" onClick={() => setImagenAmpliada(form.imagen_url.trim())} className="block w-28 h-28 rounded-xl border-2 border-slate-200 bg-slate-50 overflow-hidden flex items-center justify-center hover:border-primary-400 cursor-zoom-in transition-colors focus:outline-none focus:ring-2 focus:ring-primary-400">
                    <img src={form.imagen_url.trim()} alt="Foto actual" className="max-w-full max-h-full object-contain" onError={(e) => { e.target.style.display = 'none' }} />
                  </button>
                  <p className="text-xs text-slate-500 mt-2 text-center">Clic para ampliar</p>
                </div>
                <div className="flex flex-col gap-3">
                  <input type="file" ref={inputFotoRef} accept="image/*" capture="environment" className="hidden" onChange={handleSeleccionarFoto} />
                  <button type="button" onClick={() => inputFotoRef.current?.click()} disabled={subiendoFoto} className="px-5 py-2.5 bg-primary-100 hover:bg-primary-200 text-primary-700 border border-primary-300 rounded-lg font-medium disabled:opacity-50 w-fit">
                    {subiendoFoto ? '⏳ Subiendo...' : '📷 Cambiar foto'}
                  </button>
                  <button type="button" onClick={() => setForm((f) => ({ ...f, imagen_url: '' }))} className="px-5 py-2.5 text-red-600 hover:bg-red-50 border border-red-200 rounded-lg font-medium w-fit">
                    🗑️ Eliminar foto
                  </button>
                </div>
              </>
            ) : (
              <div>
                <input type="file" ref={inputFotoRef} accept="image/*" capture="environment" className="hidden" onChange={handleSeleccionarFoto} />
                <button type="button" onClick={() => inputFotoRef.current?.click()} disabled={subiendoFoto} className="px-5 py-3 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg font-medium text-slate-700 disabled:opacity-50 flex items-center gap-2">
                  {subiendoFoto ? '⏳ Subiendo...' : '📷 Seleccionar o tomar foto'}
                </button>
              </div>
            )}
            </div>
            <p className="text-xs text-slate-500 mt-1">JPG, PNG, WebP, GIF • Máx. 5 MB</p>
          </div>

          {/* Comprobante */}
          <div className="pt-4 border-t border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800 mb-2">Imagen de comprobante (evidencia)</h2>
            <p className="text-sm text-slate-500 mb-3">Foto o PDF de factura, recibo o orden de compra. JPG, PNG, WebP, GIF, PDF • Máx. 5 MB</p>
            <div className="flex flex-wrap gap-4 items-center">
              {form.comprobante_url?.trim() ? (
                <>
                  <div className="flex items-center gap-2">
                    <a href={form.comprobante_url.trim()} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg text-slate-700 font-medium text-sm inline-flex items-center gap-2">
                      📎 Ver comprobante
                    </a>
                    <button type="button" onClick={() => setForm((f) => ({ ...f, comprobante_url: '' }))} className="px-4 py-2 text-red-600 hover:bg-red-50 border border-red-200 rounded-lg font-medium text-sm">
                      Eliminar
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <input type="file" ref={inputComprobanteRef} accept="image/*,.pdf" className="hidden" onChange={handleSeleccionarComprobante} />
                  <button type="button" onClick={() => inputComprobanteRef.current?.click()} disabled={subiendoComprobante} className="px-5 py-3 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg font-medium text-slate-700 disabled:opacity-50 flex items-center gap-2">
                    {subiendoComprobante ? '⏳ Subiendo...' : '📎 Adjuntar comprobante'}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Clasificación */}
          <div className="pt-4 border-t border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Clasificación y ubicación</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Categoría</label>
                <select value={form.id_categoria} onChange={(e) => setForm({ ...form, id_categoria: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="">Sin categoría</option>
                  {categorias.map((c) => (
                    <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Proveedor preferido</label>
                <p className="text-xs text-slate-500 mb-1">Se usa al crear órdenes de compra o registrar entradas</p>
                <select value={form.id_proveedor} onChange={(e) => setForm({ ...form, id_proveedor: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="">Sin proveedor</option>
                  {proveedores.map((p) => (
                    <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
                  ))}
                </select>
              </div>
            </div>
            <p className="text-sm font-medium text-slate-700 mt-4 mb-2">Ubicación: Bodega → Zona/Pasillo → Estante → Nivel → Fila</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Bodega</label>
                <select value={bodegaSeleccionada} onChange={(e) => { setBodegaSeleccionada(e.target.value); setUbicacionSeleccionada(''); setForm({ ...form, id_estante: '', id_nivel: '', id_fila: '' }); }} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="">Seleccionar</option>
                  {bodegas.filter(b => b.activo !== false).map((b) => (
                    <option key={b.id} value={b.id}>{b.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Ubicación (zona/pasillo)</label>
                <select value={ubicacionSeleccionada} onChange={(e) => { setUbicacionSeleccionada(e.target.value); setForm({ ...form, id_estante: '', id_nivel: '', id_fila: '' }); }} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 disabled:bg-slate-50" disabled={!bodegaSeleccionada}>
                  <option value="">Seleccionar</option>
                  {ubicaciones.filter(u => Number(u.id_bodega) === Number(bodegaSeleccionada) && u.activo !== false).map((u) => (
                    <option key={u.id} value={u.id}>{u.codigo} - {u.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Estante</label>
                <select value={form.id_estante} onChange={(e) => setForm({ ...form, id_estante: e.target.value, id_nivel: '', id_fila: '' })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 disabled:bg-slate-50" disabled={!ubicacionSeleccionada}>
                  <option value="">Seleccionar</option>
                  {estantes.filter(e => e.id_ubicacion === parseInt(ubicacionSeleccionada) && e.activo !== false).map((e) => (
                    <option key={e.id} value={e.id}>{e.codigo} - {e.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nivel</label>
                <select value={form.id_nivel} onChange={(e) => setForm({ ...form, id_nivel: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="">Seleccionar</option>
                  {niveles.filter(n => n.activo !== false).map((n) => (
                    <option key={n.id} value={n.id}>{n.codigo} - {n.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Fila</label>
                <select value={form.id_fila} onChange={(e) => setForm({ ...form, id_fila: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="">Seleccionar</option>
                  {filas.filter(f => f.activo !== false).map((f) => (
                    <option key={f.id} value={f.id}>{f.codigo} - {f.nombre}</option>
                  ))}
                </select>
              </div>
              <div className="lg:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Notas (texto libre)</label>
                <input type="text" value={form.ubicacion} onChange={(e) => setForm({ ...form, ubicacion: e.target.value })} placeholder="Ej: Lado derecho del estante, caja superior, etiqueta visible u otro detalle para localizar rápido el producto" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
              </div>
            </div>
          </div>

          {/* Inventario y precios */}
          <div className="pt-4 border-t border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Inventario y precios</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Stock inicial *</label>
                <input type="number" min={0} step="any" value={form.stock_actual} onChange={(e) => setForm({ ...form, stock_actual: parseFloat(e.target.value) || 0 })} onFocus={(e) => { if (form.stock_actual === 0) e.target.select(); }} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" disabled={!!editando} title={editando ? 'El stock se modifica con movimientos' : 'Ej: 37.6 para litros'} placeholder="Ej: 37.6" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-0.5">Stock mín.</label>
              <input type="number" min={0} step="any" value={form.stock_minimo} onChange={(e) => setForm({ ...form, stock_minimo: parseFloat(e.target.value) || 5 })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-0.5">Stock máx.</label>
              <input type="number" min={0} step="any" value={form.stock_maximo} onChange={(e) => setForm({ ...form, stock_maximo: parseFloat(e.target.value) || 100 })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-0.5">Unidad</label>
              <select value={form.unidad_medida} onChange={(e) => setForm({ ...form, unidad_medida: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                {UNIDADES.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-0.5">P. compra *</label>
              <input type="number" step={0.01} min={0} value={form.precio_compra} onChange={(e) => setForm({ ...form, precio_compra: e.target.value })} placeholder="0.00" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-0.5">P. venta *</label>
              <div className="flex gap-2">
                <input type="number" step={0.01} min={0} value={form.precio_venta} onChange={(e) => setForm({ ...form, precio_venta: e.target.value })} placeholder="0.00" className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required />
                <button type="button" onClick={aplicarMarkup} disabled={!form.precio_compra || parseFloat(form.precio_compra) <= 0} title={`Aplicar ${config.markup_porcentaje ?? 20}% de markup sobre precio compra`} className="px-3 py-2 bg-amber-100 text-amber-800 rounded-lg text-sm font-medium hover:bg-amber-200 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap">
                  +{config.markup_porcentaje ?? 20}%
                </button>
              </div>
            </div>
          </div>
          </div>

          {/* Marca y modelo */}
          <div className="pt-4 border-t border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Marca y compatibilidad</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Marca</label>
                <input type="text" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} placeholder="Ej: Castrol" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Modelo compatible (texto libre)</label>
                <input type="text" value={form.modelo_compatible} onChange={(e) => setForm({ ...form, modelo_compatible: e.target.value })} placeholder="Ej: Nissan Versa 2015-2020" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
              </div>
            </div>
          </div>

          {/* Vehículos compatibles (solo al editar) */}
          {editando && id && (
            <div className="pt-4 border-t border-slate-200">
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Vehículos compatibles</h2>
              <p className="text-sm text-slate-500 mb-4">Indica a qué vehículos aplica este repuesto. Se usará para filtrar inventario por vehículo (ej. orden de compra).</p>
              <div className="space-y-3">
                {compatibilidades.map((c) => (
                  <div key={c.id} className="flex items-center justify-between gap-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-sm">
                      {c.marca} {c.modelo}
                      {(c.anio_desde || c.anio_hasta) && ` (${c.anio_desde ?? '?'}-${c.anio_hasta ?? '?'})`}
                      {c.motor ? ` · ${c.motor}` : ''}
                    </span>
                    <button type="button" onClick={() => quitarCompatibilidad(c.id)} className="text-red-600 hover:bg-red-50 px-2 py-1 rounded text-sm">Quitar</button>
                  </div>
                ))}
                <form onSubmit={agregarCompatibilidad} className="flex flex-wrap gap-2 items-end p-3 bg-white rounded-lg border border-slate-200">
                  <input type="text" value={nuevaCompat.marca} onChange={(e) => setNuevaCompat({ ...nuevaCompat, marca: e.target.value })} placeholder="Marca" className="w-28 px-2 py-2 border rounded-lg text-sm" />
                  <input type="text" value={nuevaCompat.modelo} onChange={(e) => setNuevaCompat({ ...nuevaCompat, modelo: e.target.value })} placeholder="Modelo" className="w-32 px-2 py-2 border rounded-lg text-sm" />
                  <input type="number" min={1900} max={2030} value={nuevaCompat.anio_desde} onChange={(e) => setNuevaCompat({ ...nuevaCompat, anio_desde: e.target.value })} placeholder="Año desde" className="w-24 px-2 py-2 border rounded-lg text-sm" />
                  <input type="number" min={1900} max={2030} value={nuevaCompat.anio_hasta} onChange={(e) => setNuevaCompat({ ...nuevaCompat, anio_hasta: e.target.value })} placeholder="Año hasta" className="w-24 px-2 py-2 border rounded-lg text-sm" />
                  <input type="text" value={nuevaCompat.motor} onChange={(e) => setNuevaCompat({ ...nuevaCompat, motor: e.target.value })} placeholder="Motor (opc.)" className="w-24 px-2 py-2 border rounded-lg text-sm" />
                  <button type="submit" className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700">Agregar</button>
                </form>
              </div>
            </div>
          )}

          {/* Activo */}
          <div className="pt-4 border-t border-slate-200 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
              <span className="text-sm text-slate-700">Producto activo</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={!!form.es_consumible} onChange={(e) => setForm({ ...form, es_consumible: e.target.checked })} className="rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
              <span className="text-sm text-slate-700">Consumible</span>
              <span className="text-xs text-slate-500">(aceite, filtros; al cancelar ventas pagadas se sugiere merma)</span>
            </label>
          </div>
        </div>

        {/* Navegación */}
        <div className="flex justify-between items-center pt-4 mt-6 border-t border-slate-200">
          <div>
            <Link to="/inventario" className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium text-sm inline-block">
              Cancelar
            </Link>
          </div>
          <div>
            <button type="submit" disabled={enviando} className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm">
              {enviando ? 'Guardando...' : editando ? 'Guardar cambios' : 'Crear repuesto'}
            </button>
          </div>
        </div>
      </form>

      {imagenAmpliada && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4" onClick={() => setImagenAmpliada(null)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Escape' && setImagenAmpliada(null)}>
          <img src={imagenAmpliada} alt="Vista ampliada" className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl" onClick={(e) => e.stopPropagation()} />
          <button type="button" onClick={() => setImagenAmpliada(null)} className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/90 hover:bg-white text-slate-700 flex items-center justify-center text-xl">×</button>
        </div>
      )}
    </div>
  )
}
