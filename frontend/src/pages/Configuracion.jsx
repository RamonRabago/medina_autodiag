import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Configuracion() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const [tab, setTab] = useState(tabParam === 'ubicaciones' ? 'ubicaciones' : tabParam === 'bodegas' ? 'bodegas' : tabParam === 'categorias-repuestos' ? 'categorias-repuestos' : 'categorias-servicios')
  const [categoriasServicios, setCategoriasServicios] = useState([])
  const [categoriasRepuestos, setCategoriasRepuestos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [ubicaciones, setUbicaciones] = useState([])
  const [estantes, setEstantes] = useState([])
  const [niveles, setNiveles] = useState([])
  const [filas, setFilas] = useState([])
  const [filtroBodega, setFiltroBodega] = useState('')
  const [loading, setLoading] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({ nombre: '', descripcion: '', activo: true })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalEliminar, setModalEliminar] = useState(false)
  const [categoriaAEliminar, setCategoriaAEliminar] = useState(null)
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const esAdmin = user?.rol === 'ADMIN'

  const cargarServicios = () => {
    api.get('/categorias-servicios/', { params: { limit: 500 } })
      .then((r) => setCategoriasServicios(Array.isArray(r.data) ? r.data : []))
      .catch(() => setCategoriasServicios([]))
  }

  const cargarRepuestos = () => {
    api.get('/categorias-repuestos/', { params: { limit: 500 } })
      .then((r) => setCategoriasRepuestos(Array.isArray(r.data) ? r.data : []))
      .catch(() => setCategoriasRepuestos([]))
  }

  const cargarBodegas = () => {
    api.get('/bodegas/', { params: { limit: 500 } })
      .then((r) => setBodegas(Array.isArray(r.data) ? r.data : []))
      .catch(() => setBodegas([]))
  }

  const cargar = () => {
    setLoading(true)
    Promise.all([
      api.get('/categorias-servicios/', { params: { limit: 500 } }),
      api.get('/categorias-repuestos/', { params: { limit: 500 } }),
      api.get('/bodegas/', { params: { limit: 500 } }),
      api.get('/ubicaciones/', { params: { limit: 500 } }),
      api.get('/estantes/', { params: { limit: 500 } }),
      api.get('/niveles/', { params: { limit: 100 } }),
      api.get('/filas/', { params: { limit: 100 } }),
    ])
      .then(([r1, r2, r3, r4, r5, r6, r7]) => {
        setCategoriasServicios(Array.isArray(r1.data) ? r1.data : [])
        setCategoriasRepuestos(Array.isArray(r2.data) ? r2.data : [])
        setBodegas(Array.isArray(r3.data) ? r3.data : [])
        setUbicaciones(Array.isArray(r4.data) ? r4.data : [])
        setEstantes(Array.isArray(r5.data) ? r5.data : [])
        setNiveles(Array.isArray(r6.data) ? r6.data : [])
        setFilas(Array.isArray(r7.data) ? r7.data : [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [])
  useEffect(() => {
    if (tabParam === 'estantes') setTab('estantes')
    else if (tabParam === 'niveles') setTab('niveles')
    else if (tabParam === 'filas') setTab('filas')
    else if (tabParam === 'ubicaciones') setTab('ubicaciones')
    else if (tabParam === 'categorias-repuestos') setTab('categorias-repuestos')
    else if (tabParam === 'categorias-servicios') setTab('categorias-servicios')
    else if (tabParam === 'bodegas') setTab('bodegas')
  }, [tabParam])

  const abrirNuevo = () => {
    setEditando(null)
    if (tab === 'ubicaciones') setForm({ id_bodega: bodegas[0]?.id || '', codigo: '', nombre: '', descripcion: '', activo: true })
    else if (tab === 'estantes') setForm({ id_bodega: bodegas[0]?.id || '', id_ubicacion: ubicaciones[0]?.id || '', codigo: '', nombre: '', descripcion: '', activo: true })
    else if (tab === 'niveles') setForm({ codigo: '', nombre: '', activo: true })
    else if (tab === 'filas') setForm({ codigo: '', nombre: '', activo: true })
    else if (tab === 'categorias-repuestos') setForm({ nombre: '', descripcion: '' })
    else setForm({ nombre: '', descripcion: '', activo: true })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (c) => {
    setEditando(c)
    if (tab === 'ubicaciones') {
      setForm({
        id_bodega: c.id_bodega || '',
        codigo: c.codigo || '',
        nombre: c.nombre || '',
        descripcion: c.descripcion || '',
        activo: c.activo !== false,
      })
    } else if (tab === 'estantes') {
      const ubi = ubicaciones.find(u => u.id === c.id_ubicacion)
      setForm({
        id_bodega: ubi?.id_bodega || '',
        id_ubicacion: c.id_ubicacion || '',
        codigo: c.codigo || '',
        nombre: c.nombre || '',
        descripcion: c.descripcion || '',
        activo: c.activo !== false,
      })
    } else if (tab === 'niveles' || tab === 'filas') {
      setForm({
        codigo: c.codigo || '',
        nombre: c.nombre || '',
        activo: c.activo !== false,
      })
    } else if (tab === 'categorias-repuestos') {
      setForm({ nombre: c.nombre || '', descripcion: c.descripcion || '' })
    } else {
      setForm({ nombre: c.nombre || '', descripcion: c.descripcion || '', activo: c.activo !== false })
    }
    setError('')
    setModalAbierto(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (tab === 'ubicaciones') {
      if (!form.id_bodega || !form.codigo?.trim() || !form.nombre?.trim()) {
        setError('Bodega, código y nombre son obligatorios')
        return
      }
    } else if (tab === 'estantes') {
      if (!form.id_ubicacion || !form.codigo?.trim() || !form.nombre?.trim()) {
        setError('Ubicación, código y nombre son obligatorios')
        return
      }
    } else if ((tab === 'niveles' || tab === 'filas') && (!form.codigo?.trim() || !form.nombre?.trim())) {
      setError('Código y nombre son obligatorios')
      return
    } else if (!form.nombre.trim()) {
      setError('El nombre es obligatorio')
      return
    }
    setEnviando(true)
    try {
      if (tab === 'categorias-servicios') {
        if (editando) {
          await api.put(`/categorias-servicios/${editando.id}`, {
            nombre: form.nombre.trim(),
            descripcion: form.descripcion?.trim() || null,
            activo: form.activo,
          })
        } else {
          await api.post('/categorias-servicios/', {
            nombre: form.nombre.trim(),
            descripcion: form.descripcion?.trim() || null,
            activo: form.activo,
          })
        }
      } else if (tab === 'categorias-repuestos') {
        if (editando) {
          await api.put(`/categorias-repuestos/${editando.id_categoria}`, {
            nombre: form.nombre.trim(),
            descripcion: form.descripcion?.trim() || null,
          })
        } else {
          await api.post('/categorias-repuestos/', {
            nombre: form.nombre.trim(),
            descripcion: form.descripcion?.trim() || null,
          })
        }
      } else if (tab === 'bodegas') {
        if (editando) {
          await api.put(`/bodegas/${editando.id}`, {
            nombre: form.nombre.trim(),
            descripcion: form.descripcion?.trim() || null,
            activo: form.activo,
          })
        } else {
          await api.post('/bodegas/', {
            nombre: form.nombre.trim(),
            descripcion: form.descripcion?.trim() || null,
            activo: form.activo,
          })
        }
      } else if (tab === 'ubicaciones') {
        const payload = {
          id_bodega: Number(form.id_bodega),
          codigo: form.codigo.trim(),
          nombre: form.nombre.trim(),
          descripcion: form.descripcion?.trim() || null,
          activo: form.activo,
        }
        if (editando) {
          await api.put(`/ubicaciones/${editando.id}`, payload)
        } else {
          await api.post('/ubicaciones/', payload)
        }
      } else if (tab === 'estantes') {
        const payload = {
          id_ubicacion: Number(form.id_ubicacion),
          codigo: form.codigo.trim(),
          nombre: form.nombre.trim(),
          descripcion: form.descripcion?.trim() || null,
          activo: form.activo,
        }
        if (editando) {
          await api.put(`/estantes/${editando.id}`, payload)
        } else {
          await api.post('/estantes/', payload)
        }
      } else if (tab === 'niveles') {
        const payload = { codigo: form.codigo.trim(), nombre: form.nombre.trim(), activo: form.activo }
        if (editando) {
          await api.put(`/niveles/${editando.id}`, payload)
        } else {
          await api.post('/niveles/', payload)
        }
      } else if (tab === 'filas') {
        const payload = { codigo: form.codigo.trim(), nombre: form.nombre.trim(), activo: form.activo }
        if (editando) {
          await api.put(`/filas/${editando.id}`, payload)
        } else {
          await api.post('/filas/', payload)
        }
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

  const abrirModalEliminar = (c) => {
    setCategoriaAEliminar(c)
    setModalEliminar(true)
  }

  const confirmarEliminar = async () => {
    if (!categoriaAEliminar) return
    setEnviandoEliminar(true)
    try {
      if (tab === 'categorias-servicios') {
        await api.delete(`/categorias-servicios/${categoriaAEliminar.id}`)
      } else if (tab === 'categorias-repuestos') {
        await api.delete(`/categorias-repuestos/${categoriaAEliminar.id_categoria}`)
      } else if (tab === 'bodegas') {
        await api.delete(`/bodegas/${categoriaAEliminar.id}`)
      } else if (tab === 'ubicaciones') {
        await api.delete(`/ubicaciones/${categoriaAEliminar.id}`)
      } else if (tab === 'estantes') {
        await api.delete(`/estantes/${categoriaAEliminar.id}`)
      } else if (tab === 'niveles') {
        await api.delete(`/niveles/${categoriaAEliminar.id}`)
      } else if (tab === 'filas') {
        await api.delete(`/filas/${categoriaAEliminar.id}`)
      }
      cargar()
      setModalEliminar(false)
      setCategoriaAEliminar(null)
    } catch (err) {
      const d = err.response?.data?.detail
      alert(typeof d === 'string' ? d : 'Error al eliminar')
    } finally {
      setEnviandoEliminar(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Configuración</h1>

      <div className="flex gap-2 mb-6 border-b border-slate-200">
        <button
          onClick={() => { setTab('categorias-servicios'); setSearchParams({ tab: 'categorias-servicios' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'categorias-servicios' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Categorías de servicios
        </button>
        <button
          onClick={() => { setTab('categorias-repuestos'); setSearchParams({ tab: 'categorias-repuestos' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'categorias-repuestos' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Categorías de repuestos
        </button>
        <button
          onClick={() => { setTab('bodegas'); setSearchParams({ tab: 'bodegas' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'bodegas' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Bodegas
        </button>
        <button
          onClick={() => { setTab('ubicaciones'); setSearchParams({ tab: 'ubicaciones' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'ubicaciones' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Ubicaciones
        </button>
        <button
          onClick={() => { setTab('estantes'); setSearchParams({ tab: 'estantes' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'estantes' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Estantes
        </button>
        <button
          onClick={() => { setTab('niveles'); setSearchParams({ tab: 'niveles' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'niveles' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Niveles
        </button>
        <button
          onClick={() => { setTab('filas'); setSearchParams({ tab: 'filas' }) }}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'filas' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Filas
        </button>
      </div>

      {tab === 'ubicaciones' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Inventario
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Ubicaciones</h2>
              <select
                value={filtroBodega}
                onChange={(e) => setFiltroBodega(e.target.value)}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm"
              >
                <option value="">Todas las bodegas</option>
                {bodegas.filter(b => b.activo !== false).map((b) => (
                  <option key={b.id} value={b.id}>{b.nombre}</option>
                ))}
              </select>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nueva ubicación
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Bodega</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                    {esAdmin && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {(() => {
                    const list = filtroBodega ? ubicaciones.filter(u => u.id_bodega === Number(filtroBodega)) : ubicaciones
                    if (list.length === 0) {
                      return (
                        <tr>
                          <td colSpan={esAdmin ? 7 : 6} className="px-4 py-8 text-center text-slate-500">
                            No hay ubicaciones. Crea bodegas primero y luego añade ubicaciones (ej: Pasillo A-1, Estante B2).
                          </td>
                        </tr>
                      )
                    }
                    return list.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{u.id}</td>
                        <td className="px-4 py-3 text-sm font-medium text-slate-800">{u.bodega_nombre || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-700 font-mono">{u.codigo}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{u.nombre}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={u.descripcion || ''}>{u.descripcion || '-'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${u.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                            {u.activo !== false ? 'Activa' : 'Inactiva'}
                          </span>
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button type="button" onClick={() => abrirEditar(u)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button type="button" onClick={() => abrirModalEliminar(u)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  })()}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'estantes' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Inventario
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Estantes</h2>
              <select value={filtroBodega} onChange={(e) => setFiltroBodega(e.target.value)} className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm">
                <option value="">Todas las bodegas</option>
                {bodegas.filter(b => b.activo !== false).map((b) => (
                  <option key={b.id} value={b.id}>{b.nombre}</option>
                ))}
              </select>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nuevo estante
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Bodega</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Ubicación</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                    {esAdmin && <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {(() => {
                    const listFiltered = filtroBodega ? estantes.filter(e => {
                      const u = ubicaciones.find(uu => uu.id === e.id_ubicacion)
                      return u && u.id_bodega === Number(filtroBodega)
                    }) : estantes
                    if (listFiltered.length === 0) {
                      return (
                        <tr><td colSpan={esAdmin ? 8 : 7} className="px-4 py-8 text-center text-slate-500">
                          No hay estantes. Crea bodegas, luego ubicaciones (zonas/pasillos) y después estantes (ej: E1, Estante 1).
                        </td></tr>
                      )
                    }
                    return listFiltered.map((e) => (
                      <tr key={e.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{e.id}</td>
                        <td className="px-4 py-3 text-sm font-medium text-slate-800">{e.bodega_nombre || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">{e.ubicacion_nombre || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-700 font-mono">{e.codigo}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{e.nombre}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={e.descripcion || ''}>{e.descripcion || '-'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${e.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                            {e.activo !== false ? 'Activo' : 'Inactivo'}
                          </span>
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button type="button" onClick={() => abrirEditar(e)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button type="button" onClick={() => abrirModalEliminar(e)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  })()}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'niveles' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Inventario
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Niveles (A, B, C, D...)</h2>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nuevo nivel
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                    {esAdmin && <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {niveles.length === 0 ? (
                    <tr><td colSpan={esAdmin ? 5 : 4} className="px-4 py-8 text-center text-slate-500">No hay niveles. Crea A, B, C, D para organizar verticalmente.</td></tr>
                  ) : (
                    niveles.map((n) => (
                      <tr key={n.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{n.id}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-800">{n.codigo}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{n.nombre}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${n.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                            {n.activo !== false ? 'Activo' : 'Inactivo'}
                          </span>
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button type="button" onClick={() => abrirEditar(n)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button type="button" onClick={() => abrirModalEliminar(n)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'filas' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Inventario
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Filas (1, 2, 3, 4, 5...)</h2>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nueva fila
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                    {esAdmin && <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filas.length === 0 ? (
                    <tr><td colSpan={esAdmin ? 5 : 4} className="px-4 py-8 text-center text-slate-500">No hay filas. Crea 1, 2, 3, 4, 5 para posiciones horizontales.</td></tr>
                  ) : (
                    filas.map((f) => (
                      <tr key={f.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{f.id}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-800">{f.codigo}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{f.nombre}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${f.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                            {f.activo !== false ? 'Activa' : 'Inactiva'}
                          </span>
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button type="button" onClick={() => abrirEditar(f)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button type="button" onClick={() => abrirModalEliminar(f)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'bodegas' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Inventario
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Bodegas</h2>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nueva bodega
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                    {esAdmin && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {bodegas.length === 0 ? (
                    <tr>
                      <td colSpan={esAdmin ? 5 : 4} className="px-4 py-8 text-center text-slate-500">
                        No hay bodegas. Crea una para organizar el almacenamiento (Principal, Taller, Mostrador, etc.).
                      </td>
                    </tr>
                  ) : (
                    bodegas.map((b) => (
                      <tr key={b.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{b.id}</td>
                        <td className="px-4 py-3 text-sm font-medium text-slate-800">{b.nombre}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={b.descripcion || ''}>
                          {b.descripcion || '-'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${b.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                            {b.activo !== false ? 'Activa' : 'Inactiva'}
                          </span>
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button onClick={() => abrirEditar(b)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button onClick={() => abrirModalEliminar(b)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'categorias-servicios' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/servicios" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Servicios
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Categorías de servicios</h2>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nueva categoría
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                    {esAdmin && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {categoriasServicios.length === 0 ? (
                    <tr>
                      <td colSpan={esAdmin ? 5 : 4} className="px-4 py-8 text-center text-slate-500">
                        No hay categorías. Crea una para asignarla a los servicios.
                      </td>
                    </tr>
                  ) : (
                    categoriasServicios.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{c.id}</td>
                        <td className="px-4 py-3 text-sm font-medium text-slate-800">{c.nombre}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={c.descripcion || ''}>
                          {c.descripcion || '-'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${c.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                            {c.activo !== false ? 'Activa' : 'Inactiva'}
                          </span>
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button onClick={() => abrirEditar(c)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">
                                ✏️
                              </button>
                              <button onClick={() => abrirModalEliminar(c)} className="text-sm text-red-600 hover:text-red-700" title="Eliminar">
                                🗑️
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'categorias-repuestos' && (
        <div className="bg-white rounded-lg shadow border border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm">
                ← Volver a Inventario
              </Link>
              <h2 className="text-lg font-semibold text-slate-800">Categorías de repuestos</h2>
            </div>
            {esAdmin && (
              <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                + Nueva categoría
              </button>
            )}
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>
                    {esAdmin && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {categoriasRepuestos.length === 0 ? (
                    <tr>
                      <td colSpan={esAdmin ? 4 : 3} className="px-4 py-8 text-center text-slate-500">
                        No hay categorías. Crea una para asignarla a los repuestos del inventario.
                      </td>
                    </tr>
                  ) : (
                    categoriasRepuestos.map((c) => (
                      <tr key={c.id_categoria} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-600">{c.id_categoria}</td>
                        <td className="px-4 py-3 text-sm font-medium text-slate-800">{c.nombre}</td>
                        <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={c.descripcion || ''}>
                          {c.descripcion || '-'}
                        </td>
                        {esAdmin && (
                          <td className="px-4 py-3 text-right">
                            <div className="flex gap-1 justify-end">
                              <button onClick={() => abrirEditar(c)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">
                                ✏️
                              </button>
                              <button onClick={() => abrirModalEliminar(c)} className="text-sm text-red-600 hover:text-red-700" title="Eliminar">
                                🗑️
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <Modal titulo={editando ? (tab === 'ubicaciones' ? 'Editar ubicación' : tab === 'bodegas' ? 'Editar bodega' : tab === 'estantes' ? 'Editar estante' : tab === 'niveles' ? 'Editar nivel' : tab === 'filas' ? 'Editar fila' : 'Editar categoría') : (tab === 'ubicaciones' ? 'Nueva ubicación' : tab === 'bodegas' ? 'Nueva bodega' : tab === 'estantes' ? 'Nuevo estante' : tab === 'niveles' ? 'Nuevo nivel' : tab === 'filas' ? 'Nueva fila' : 'Nueva categoría')} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          {tab === 'ubicaciones' && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Bodega *</label>
                <select value={form.id_bodega} onChange={(e) => setForm({ ...form, id_bodega: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required>
                  <option value="">Selecciona bodega</option>
                  {bodegas.filter(b => b.activo !== false).map((b) => (
                    <option key={b.id} value={b.id}>{b.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>
                <input type="text" value={form.codigo || ''} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="Ej: A1, B2, PASILLO-01" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono" required />
              </div>
            </>
          )}
          {tab === 'estantes' && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Bodega *</label>
                <select value={form.id_bodega} onChange={(e) => setForm({ ...form, id_bodega: e.target.value, id_ubicacion: '' })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required>
                  <option value="">Selecciona bodega</option>
                  {bodegas.filter(b => b.activo !== false).map((b) => (
                    <option key={b.id} value={b.id}>{b.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Ubicación (zona/pasillo) *</label>
                <select value={form.id_ubicacion} onChange={(e) => setForm({ ...form, id_ubicacion: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required disabled={!form.id_bodega}>
                  <option value="">Selecciona ubicación</option>
                  {ubicaciones.filter(u => Number(u.id_bodega) === Number(form.id_bodega)).map((u) => (
                    <option key={u.id} value={u.id}>{u.codigo} - {u.nombre}{u.activo === false ? ' (Inactiva)' : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>
                <input type="text" value={form.codigo || ''} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="Ej: E1, EST-01" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono" required />
              </div>
            </>
          )}
          {(tab === 'niveles' || tab === 'filas') && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>
              <input type="text" value={form.codigo || ''} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder={tab === 'niveles' ? 'Ej: A, B, C' : 'Ej: 1, 2, 3'} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono" required />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
            <input
              type="text"
              value={form.nombre || ''}
              onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              placeholder={tab === 'ubicaciones' ? 'Ej: Pasillo A, Estante 1' : tab === 'categorias-repuestos' ? 'Ej: Aceites' : tab === 'bodegas' ? 'Ej: Bodega principal' : 'Ej: Mantenimiento'}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>
          {tab !== 'niveles' && tab !== 'filas' && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Descripción (opcional)</label>
              <textarea
                value={form.descripcion || ''}
                onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
                rows={2}
                placeholder={tab === 'ubicaciones' ? 'Ej: Pasillo principal, nivel superior' : tab === 'estantes' ? 'Ej: Estante principal del pasillo A' : tab === 'categorias-repuestos' ? 'Ej: Aceites, lubricantes y aditivos' : tab === 'bodegas' ? 'Ej: Bodega principal' : 'Descripción breve'}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>
          )}
          {((tab === 'categorias-servicios' || tab === 'bodegas' || tab === 'ubicaciones' || tab === 'estantes' || tab === 'niveles' || tab === 'filas')) && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.activo}
                onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                className="rounded border-slate-300"
              />
              <span className="text-sm text-slate-700">Activo</span>
            </label>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
              Cancelar
            </button>
            <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
              {enviando ? 'Guardando...' : editando ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal titulo={tab === 'ubicaciones' ? 'Desactivar ubicación' : tab === 'estantes' ? 'Desactivar estante' : tab === 'niveles' ? 'Desactivar nivel' : tab === 'filas' ? 'Desactivar fila' : tab === 'bodegas' ? 'Desactivar bodega' : 'Eliminar categoría'} abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setCategoriaAEliminar(null) }}>
        <div className="space-y-4">
          {categoriaAEliminar && (
            <>
              <p className="text-slate-600">
                ¿{['ubicaciones','bodegas','estantes','niveles','filas'].includes(tab) ? 'Desactivar' : 'Eliminar'} {tab === 'ubicaciones' ? 'la ubicación' : tab === 'estantes' ? 'el estante' : tab === 'niveles' ? 'el nivel' : tab === 'filas' ? 'la fila' : tab === 'bodegas' ? 'la bodega' : 'la categoría'} <strong>{categoriaAEliminar.nombre}</strong>?{['ubicaciones','bodegas','estantes','niveles','filas'].includes(tab) ? ' Se marcará como inactiva.' : ' No podrás eliminarla si tiene ' + (tab === 'categorias-repuestos' ? 'repuestos' : 'servicios') + ' asignados. Asigna otra categoría primero.'}
              </p>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminar(false); setCategoriaAEliminar(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">
                  Cancelar
                </button>
                <button type="button" onClick={confirmarEliminar} disabled={enviandoEliminar} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                  {enviandoEliminar ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  )
}
