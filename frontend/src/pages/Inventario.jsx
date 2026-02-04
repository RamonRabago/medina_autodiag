import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
const UNIDADES = ['PZA', 'LT', 'KG', 'CJA', 'PAR', 'SET']

export default function Inventario() {
  const { user } = useAuth()
  const [repuestos, setRepuestos] = useState([])
  const [loading, setLoading] = useState(true)
  const [buscar, setBuscar] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroStockBajo, setFiltroStockBajo] = useState(false)
  const [filtroActivo, setFiltroActivo] = useState('')
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20
  const esAdmin = user?.rol === 'ADMIN'
  const esCaja = user?.rol === 'CAJA'
  const puedeEditar = esAdmin || esCaja

  const [categorias, setCategorias] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
    id_categoria: '',
    id_proveedor: '',
    stock_actual: 0,
    stock_minimo: 5,
    stock_maximo: 100,
    ubicacion: '',
    precio_compra: '',
    precio_venta: '',
    marca: '',
    modelo_compatible: '',
    unidad_medida: 'PZA',
    activo: true,
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalEliminar, setModalEliminar] = useState(false)
  const [repuestoAEliminar, setRepuestoAEliminar] = useState(null)
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [subiendoFoto, setSubiendoFoto] = useState(false)
  const inputFotoRef = useRef(null)
  const [imagenAmpliada, setImagenAmpliada] = useState(null)

  const cargar = () => {
    setLoading(true)
    const params = { skip: (pagina - 1) * limit, limit }
    if (buscar.trim()) params.buscar = buscar.trim()
    if (filtroCategoria) params.id_categoria = parseInt(filtroCategoria)
    if (filtroStockBajo) params.stock_bajo = true
    if (filtroActivo === 'true') params.activo = true
    if (filtroActivo === 'false') params.activo = false
    api.get('/repuestos/', { params })
      .then((res) => {
        const d = res.data
        setRepuestos(d?.repuestos ?? [])
        setTotal(d?.total ?? 0)
        setTotalPaginas(d?.total_paginas ?? 1)
      })
      .catch(() => setRepuestos([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, buscar, filtroCategoria, filtroStockBajo, filtroActivo])

  useEffect(() => {
    api.get('/categorias-repuestos/').then((r) => setCategorias(Array.isArray(r.data) ? r.data : [])).catch(() => setCategorias([]))
    api.get('/proveedores/', { params: { limit: 200 } }).then((r) => setProveedores(Array.isArray(r.data) ? r.data : r.data?.proveedores ?? [])).catch(() => setProveedores([]))
  }, [])

  const abrirNuevo = () => {
    setEditando(null)
    setForm({
      codigo: '',
      nombre: '',
      descripcion: '',
      imagen_url: '',
      id_categoria: '',
      id_proveedor: '',
      stock_actual: 0,
      stock_minimo: 5,
      stock_maximo: 100,
      ubicacion: '',
      precio_compra: '',
      precio_venta: '',
      marca: '',
      modelo_compatible: '',
      unidad_medida: 'PZA',
      activo: true,
    })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (r) => {
    setEditando(r)
    setForm({
      codigo: r.codigo || '',
      nombre: r.nombre || '',
      descripcion: r.descripcion || '',
      imagen_url: r.imagen_url || '',
      id_categoria: r.id_categoria ?? '',
      id_proveedor: r.id_proveedor ?? '',
      stock_minimo: r.stock_minimo ?? 5,
      stock_maximo: r.stock_maximo ?? 100,
      ubicacion: r.ubicacion || '',
      precio_compra: r.precio_compra ?? '',
      precio_venta: r.precio_venta ?? '',
      marca: r.marca || '',
      modelo_compatible: r.modelo_compatible || '',
      unidad_medida: r.unidad_medida || 'PZA',
      activo: r.activo !== false,
    })
    setError('')
    setModalAbierto(true)
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
        stock_minimo: parseInt(form.stock_minimo) || 5,
        stock_maximo: parseInt(form.stock_maximo) || 100,
        ubicacion: form.ubicacion?.trim() || null,
        imagen_url: form.imagen_url?.trim() || null,
        precio_compra: pc,
        precio_venta: pv,
        marca: form.marca?.trim() || null,
        modelo_compatible: form.modelo_compatible?.trim() || null,
        unidad_medida: form.unidad_medida || 'PZA',
        activo: form.activo,
      }
      if (editando) {
        await api.put(`/repuestos/${editando.id_repuesto}`, payload)
      } else {
        payload.stock_actual = parseInt(form.stock_actual) || 0
        await api.post('/repuestos/', payload)
      }
      cargar()
      setModalAbierto(false)
      setEditando(null)
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : (Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : 'Error al guardar'))
    } finally {
      setEnviando(false)
    }
  }

  const abrirModalEliminar = (r) => {
    setRepuestoAEliminar(r)
    setModalEliminar(true)
  }

  const confirmarEliminar = async () => {
    if (!repuestoAEliminar) return
    setEnviandoEliminar(true)
    try {
      await api.delete(`/repuestos/${repuestoAEliminar.id_repuesto}`)
      cargar()
      setModalEliminar(false)
      setRepuestoAEliminar(null)
    } catch (err) {
      const d = err.response?.data?.detail
      alert(typeof d === 'string' ? d : 'Error al desactivar')
    } finally {
      setEnviandoEliminar(false)
    }
  }

  const activarRepuesto = async (r) => {
    try {
      await api.post(`/repuestos/${r.id_repuesto}/activar`)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al reactivar')
    }
  }

  const stockBajo = (r) => (r.stock_actual ?? 0) <= (r.stock_minimo ?? 0)
  const stockCritico = (r) => (r.stock_actual ?? 0) === 0

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
      setError(err.response?.data?.detail || 'Error al subir la imagen')
    } finally {
      setSubiendoFoto(false)
      e.target.value = ''
    }
  }


  if (loading && repuestos.length === 0) return <p className="text-slate-500 py-8">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Inventario</h1>
        <div className="flex gap-2 items-center flex-wrap">
          <input
            type="text"
            placeholder="Buscar por código, nombre o marca..."
            value={buscar}
            onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]"
          />
          <select value={filtroCategoria} onChange={(e) => { setFiltroCategoria(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
            <option value="">Todas las categorías</option>
            {categorias.map((c) => (
              <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
            ))}
          </select>
          {esAdmin && (
            <>
              <Link to="/configuracion?tab=categorias-repuestos" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar categorías de repuestos">
                ⚙️ Categorías
              </Link>
              <Link to="/configuracion?tab=bodegas" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar bodegas">
                🏪 Bodegas
              </Link>
            </>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={filtroStockBajo} onChange={(e) => { setFiltroStockBajo(e.target.checked); setPagina(1) }} />
            Stock bajo
          </label>
          <select value={filtroActivo} onChange={(e) => { setFiltroActivo(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
          {puedeEditar && (
            <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
              + Nuevo repuesto
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-3 text-center text-xs font-medium text-slate-500 uppercase w-14">Foto</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Categoría</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock mín.</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Precio venta</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                {puedeEditar && (
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {repuestos.length === 0 ? (
                <tr>
                  <td colSpan={puedeEditar ? 9 : 8} className="px-4 py-8 text-center text-slate-500">
                    No hay repuestos
                  </td>
                </tr>
              ) : (
                repuestos.map((r) => (
                  <tr key={r.id_repuesto} className={r.activo === false ? 'bg-slate-50' : 'hover:bg-slate-50'}>
                    <td className="px-3 py-2 text-center">
                      {r.imagen_url ? (
                        <div className="relative group inline-block">
                          <button type="button" onClick={() => setImagenAmpliada(r.imagen_url)} className="block mx-auto cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-primary-400 rounded">
                            <img src={r.imagen_url} alt="" className="w-10 h-10 object-contain rounded border border-slate-200 bg-white hover:border-primary-400 transition-colors" onError={(e) => { e.target.onerror = null; e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="40" height="40"%3E%3Crect fill="%23f1f5f9" width="40" height="40"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="12"%3E?%3C/text%3E%3C/svg%3E' }} />
                          </button>
                          <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-20 pointer-events-none">
                            <div className="bg-white rounded-lg shadow-xl border border-slate-200 p-1">
                              <img src={r.imagen_url} alt="" className="w-32 h-32 object-contain" />
                              <p className="text-xs text-slate-500 text-center mt-0.5">Clic para ampliar</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">{r.codigo}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{r.nombre}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{r.categoria_nombre || '-'}</td>
                    <td className="px-4 py-3 text-sm text-right">
                      <span className={stockCritico(r) ? 'text-red-600 font-semibold' : stockBajo(r) ? 'text-amber-600 font-medium' : ''}>
                        {r.stock_actual ?? 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-slate-600">{r.stock_minimo ?? 0}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">${(Number(r.precio_venta) || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 text-center">
                      {r.activo === false ? (
                        <span className="px-2 py-0.5 rounded text-xs bg-slate-200 text-slate-600">Inactivo</span>
                      ) : stockCritico(r) ? (
                        <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">Sin stock</span>
                      ) : stockBajo(r) ? (
                        <span className="px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-800">Stock bajo</span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-800">Activo</span>
                      )}
                    </td>
                    {puedeEditar && (
                      <td className="px-4 py-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {r.activo !== false ? (
                            <>
                              <button onClick={() => abrirEditar(r)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button onClick={() => abrirModalEliminar(r)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </>
                          ) : (
                            <button onClick={() => activarRepuesto(r)} className="text-sm text-green-600 hover:text-green-700" title="Reactivar">✓ Reactivar</button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPaginas > 1 && (
        <div className="mt-4 flex justify-center sm:justify-end gap-3 items-center flex-wrap p-3 bg-slate-50 rounded-lg border border-slate-200">
          <button
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={pagina <= 1}
            className="px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Anterior
          </button>
          <span className="px-4 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-200">
            Página {pagina} de {totalPaginas} ({total} registros)
          </span>
          <button
            onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
            disabled={pagina >= totalPaginas}
            className="px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Siguiente →
          </button>
        </div>
      )}

      <Modal titulo={editando ? 'Editar repuesto' : 'Nuevo repuesto'} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }} size="xl">
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

          {/* Datos básicos */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>
              <input type="text" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="Ej: MOT-001" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
              <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: Aceite Motor 10W-40" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm" required />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción (opcional)</label>
            <textarea value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} rows={2} placeholder="Descripción breve" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" />
          </div>

          {/* Foto */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Foto del producto</label>
            <div className="flex gap-4 items-start">
              {form.imagen_url?.trim() ? (
                <>
                  <div className="flex-shrink-0">
                    <button type="button" onClick={() => setImagenAmpliada(form.imagen_url.trim())} className="block w-24 h-24 rounded-lg border-2 border-slate-200 bg-slate-50 overflow-hidden flex items-center justify-center hover:border-primary-400 cursor-zoom-in transition-colors focus:outline-none focus:ring-2 focus:ring-primary-400">
                      <img src={form.imagen_url.trim()} alt="Foto actual" className="max-w-full max-h-full object-contain" onError={(e) => { e.target.style.display = 'none' }} />
                    </button>
                    <p className="text-xs text-slate-500 mt-1 text-center">Clic para ampliar</p>
                  </div>
                  <div className="flex flex-col gap-2 flex-1">
                    <input type="file" ref={inputFotoRef} accept="image/*" capture="environment" className="hidden" onChange={handleSeleccionarFoto} />
                    <button type="button" onClick={() => inputFotoRef.current?.click()} disabled={subiendoFoto} className="px-4 py-2 bg-primary-100 hover:bg-primary-200 text-primary-700 border border-primary-300 rounded-lg text-sm font-medium disabled:opacity-50 w-fit">
                      {subiendoFoto ? '⏳ Subiendo...' : '📷 Cambiar foto'}
                    </button>
                    <button type="button" onClick={() => setForm((f) => ({ ...f, imagen_url: '' }))} className="px-4 py-2 text-red-600 hover:bg-red-50 border border-red-200 rounded-lg text-sm font-medium w-fit">
                      🗑️ Eliminar foto
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex-1">
                  <input type="file" ref={inputFotoRef} accept="image/*" capture="environment" className="hidden" onChange={handleSeleccionarFoto} />
                  <button type="button" onClick={() => inputFotoRef.current?.click()} disabled={subiendoFoto} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 disabled:opacity-50 flex items-center gap-2">
                    {subiendoFoto ? '⏳ Subiendo...' : '📷 Seleccionar o tomar foto'}
                  </button>
                </div>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">Archivos o cámara • JPG, PNG, WebP, GIF • Máx. 5 MB</p>
          </div>

          {/* Clasificación */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Categoría</label>
              <select value={form.id_categoria} onChange={(e) => setForm({ ...form, id_categoria: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm">
                <option value="">Sin categoría</option>
                {categorias.map((c) => (
                  <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Proveedor</label>
              <select value={form.id_proveedor} onChange={(e) => setForm({ ...form, id_proveedor: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm">
                <option value="">Sin proveedor</option>
                {proveedores.map((p) => (
                  <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Ubicación</label>
              <input type="text" value={form.ubicacion} onChange={(e) => setForm({ ...form, ubicacion: e.target.value })} placeholder="Ej: Estante A-3" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" />
            </div>
          </div>

          {/* Inventario y precios */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4 p-4 bg-slate-50 rounded-lg border border-slate-100">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Stock inicial *</label>
              <input type="number" min={0} value={form.stock_actual} onChange={(e) => setForm({ ...form, stock_actual: parseInt(e.target.value) || 0 })} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" disabled={!!editando} title={editando ? 'El stock se modifica con movimientos' : ''} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Stock mín.</label>
              <input type="number" min={0} value={form.stock_minimo} onChange={(e) => setForm({ ...form, stock_minimo: parseInt(e.target.value) || 5 })} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Stock máx.</label>
              <input type="number" min={1} value={form.stock_maximo} onChange={(e) => setForm({ ...form, stock_maximo: parseInt(e.target.value) || 100 })} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Unidad</label>
              <select value={form.unidad_medida} onChange={(e) => setForm({ ...form, unidad_medida: e.target.value })} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm">
                {UNIDADES.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">P. compra *</label>
              <input type="number" step={0.01} min={0} value={form.precio_compra} onChange={(e) => setForm({ ...form, precio_compra: e.target.value })} placeholder="0.00" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">P. venta *</label>
              <input type="number" step={0.01} min={0} value={form.precio_venta} onChange={(e) => setForm({ ...form, precio_venta: e.target.value })} placeholder="0.00" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" required />
            </div>
          </div>

          {/* Marca y modelo */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Marca</label>
              <input type="text" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} placeholder="Ej: Castrol" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Modelo compatible</label>
              <input type="text" value={form.modelo_compatible} onChange={(e) => setForm({ ...form, modelo_compatible: e.target.value })} placeholder="Ej: Nissan Versa 2015-2020" className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-sm" />
            </div>
          </div>

          {/* Activo */}
          <div className="flex flex-wrap gap-6 py-3 px-4 bg-slate-50 rounded-lg border border-slate-100">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="rounded border-slate-300 text-primary-600 focus:ring-primary-500" />
              <span className="text-sm font-medium text-slate-700">Activo</span>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium text-sm">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium text-sm">{enviando ? 'Guardando...' : editando ? 'Guardar' : 'Crear'}</button>
          </div>
        </form>
      </Modal>

      {/* Lightbox para ver imagen ampliada */}
      {imagenAmpliada && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4"
          onClick={() => setImagenAmpliada(null)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Escape' && setImagenAmpliada(null)}
        >
          <img src={imagenAmpliada} alt="Vista ampliada" className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl" onClick={(e) => e.stopPropagation()} />
          <button type="button" onClick={() => setImagenAmpliada(null)} className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/90 hover:bg-white text-slate-700 flex items-center justify-center text-xl">×</button>
        </div>
      )}

      <Modal titulo="Desactivar repuesto" abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setRepuestoAEliminar(null) }}>
        <div className="space-y-4">
          {repuestoAEliminar && (
            <>
              <p className="text-slate-600">
                ¿Desactivar el repuesto <strong>{repuestoAEliminar.nombre}</strong> ({repuestoAEliminar.codigo})? No se eliminará, solo dejará de aparecer como opción activa.
              </p>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminar(false); setRepuestoAEliminar(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">Cancelar</button>
                <button type="button" onClick={confirmarEliminar} disabled={enviandoEliminar} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">{enviandoEliminar ? 'Desactivando...' : 'Desactivar'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  )
}
