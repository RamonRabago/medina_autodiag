import { useState, useEffect, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { hoyStr, parseFechaLocal, fechaAStr } from '../utils/fechas'
import { normalizeDetail, showError } from '../utils/toast'



export default function Configuracion() {

  const { user } = useAuth()

  const [searchParams, setSearchParams] = useSearchParams()

  const tabParam = searchParams.get('tab')

  const [tab, setTab] = useState(tabParam === 'festivos' ? 'festivos' : tabParam === 'usuarios' ? 'usuarios' : tabParam === 'usuarios-bodegas' ? 'usuarios-bodegas' : tabParam === 'ubicaciones' ? 'ubicaciones' : tabParam === 'bodegas' ? 'bodegas' : tabParam === 'categorias-repuestos' ? 'categorias-repuestos' : 'categorias-servicios')

  const [categoriasServicios, setCategoriasServicios] = useState([])

  const [categoriasRepuestos, setCategoriasRepuestos] = useState([])

  const [bodegas, setBodegas] = useState([])

  const [ubicaciones, setUbicaciones] = useState([])

  const [estantes, setEstantes] = useState([])

  const [niveles, setNiveles] = useState([])

  const [filas, setFilas] = useState([])

  const [usuarios, setUsuarios] = useState([])

  const [festivos, setFestivos] = useState([])

  const [filtroAnioFestivos, setFiltroAnioFestivos] = useState(new Date().getFullYear().toString())

  const [filtroBodega, setFiltroBodega] = useState('')

  const [modalBodegasUsuario, setModalBodegasUsuario] = useState(false)

  const [usuarioEditandoBodegas, setUsuarioEditandoBodegas] = useState(null)

  const [bodegasUsuario, setBodegasUsuario] = useState([])

  const [guardandoBodegasUsuario, setGuardandoBodegasUsuario] = useState(false)

  const [mostrarInactivas, setMostrarInactivas] = useState(false)

  const [loading, setLoading] = useState(true)

  const [modalAbierto, setModalAbierto] = useState(false)

  const [editando, setEditando] = useState(null)

  const [form, setForm] = useState({ nombre: '', descripcion: '', activo: true })

  const [error, setError] = useState('')

  const [enviando, setEnviando] = useState(false)

  const [modalEliminar, setModalEliminar] = useState(false)

  const [categoriaAEliminar, setCategoriaAEliminar] = useState(null)

  const [enviandoEliminar, setEnviandoEliminar] = useState(false)

  const rolStr = typeof user?.rol === 'string' ? user.rol : user?.rol?.value ?? ''
  const esAdmin = rolStr === 'ADMIN'

  const cargarServicios = () => {

    api.get('/categorias-servicios/', { params: { limit: 500 } })

      .then((r) => setCategoriasServicios(Array.isArray(r.data) ? r.data : []))

      .catch((err) => { showError(err, 'Error al cargar categorías de servicios'); setCategoriasServicios([]) })

  }



  const cargarRepuestos = () => {

    api.get('/categorias-repuestos/', { params: { limit: 500 } })

      .then((r) => setCategoriasRepuestos(Array.isArray(r.data) ? r.data : []))

      .catch((err) => { showError(err, 'Error al cargar categorías de repuestos'); setCategoriasRepuestos([]) })

  }



  const cargarBodegas = () => {

    api.get('/bodegas/', { params: { limit: 500 } })

      .then((r) => setBodegas(Array.isArray(r.data) ? r.data : []))

      .catch((err) => { showError(err, 'Error al cargar bodegas'); setBodegas([]) })

  }



  const cargar = useCallback(() => {

    setLoading(true)

    Promise.all([

      api.get('/categorias-servicios/', { params: { limit: 500 } }),

      api.get('/categorias-repuestos/', { params: { limit: 500 } }),

      api.get('/bodegas/', { params: { limit: 500 } }),

      api.get('/ubicaciones/', { params: { limit: 500 } }),

      api.get('/estantes/', { params: { limit: 500 } }),

      api.get('/niveles/', { params: { limit: 100 } }),

      api.get('/filas/', { params: { limit: 100 } }),

      esAdmin ? api.get('/usuarios/') : Promise.resolve({ data: [] }),

      api.get('/festivos/').catch(() => ({ data: [] })),

    ])

      .then(([r1, r2, r3, r4, r5, r6, r7, r8, r9]) => {

        setCategoriasServicios(Array.isArray(r1.data) ? r1.data : [])

        setCategoriasRepuestos(Array.isArray(r2.data) ? r2.data : [])

        setBodegas(Array.isArray(r3.data) ? r3.data : [])

        setUbicaciones(Array.isArray(r4.data) ? r4.data : [])

        setEstantes(Array.isArray(r5.data) ? r5.data : [])

        setNiveles(Array.isArray(r6.data) ? r6.data : [])

        setFilas(Array.isArray(r7.data) ? r7.data : [])

        setUsuarios(r8?.data?.usuarios ?? (Array.isArray(r8?.data) ? r8.data : []))

        setFestivos(Array.isArray(r9?.data) ? r9.data : [])

      })

      .catch((err) => {
        setError(normalizeDetail(err.response?.data?.detail) || 'Error al cargar datos')
      })

      .finally(() => setLoading(false))

  }, [esAdmin])

  useEffect(() => { cargar() }, [cargar])

  useEffect(() => {

    if (tabParam === 'estantes') setTab('estantes')

    else if (tabParam === 'niveles') setTab('niveles')

    else if (tabParam === 'filas') setTab('filas')

    else if (tabParam === 'ubicaciones') setTab('ubicaciones')

    else if (tabParam === 'categorias-repuestos') setTab('categorias-repuestos')

    else if (tabParam === 'categorias-servicios') setTab('categorias-servicios')

    else if (tabParam === 'bodegas') setTab('bodegas')

    else if (tabParam === 'usuarios') setTab('usuarios')

    else if (tabParam === 'usuarios-bodegas') setTab('usuarios-bodegas')

    else if (tabParam === 'festivos') setTab('festivos')

  }, [tabParam])



  const abrirModalBodegasUsuario = (u) => {

    setUsuarioEditandoBodegas(u)

    api.get(`/usuarios/${u.id_usuario}/bodegas-permitidas`)

      .then((r) => {

        setBodegasUsuario(r.data?.id_bodegas ?? [])

        setModalBodegasUsuario(true)

      })

      .catch((err) => {
        showError(err, 'Error al cargar bodegas del usuario')
        setBodegasUsuario([])
        setModalBodegasUsuario(true)
      })

  }



  const guardarBodegasUsuario = async () => {

    if (!usuarioEditandoBodegas) return

    setGuardandoBodegasUsuario(true)

    try {

      await api.put(`/usuarios/${usuarioEditandoBodegas.id_usuario}/bodegas-permitidas`, {

        id_bodegas: bodegasUsuario,

      })

      setModalBodegasUsuario(false)

      setUsuarioEditandoBodegas(null)

    } catch (err) {

      showError(err, 'Error al guardar')

    } finally {

      setGuardandoBodegasUsuario(false)

    }

  }



  const toggleBodegaUsuario = (idBodega) => {

    setBodegasUsuario((prev) =>

      prev.includes(idBodega) ? prev.filter((x) => x !== idBodega) : [...prev, idBodega]

    )

  }



  const abrirNuevo = () => {

    setEditando(null)

    if (tab === 'ubicaciones') setForm({ id_bodega: bodegas[0]?.id || '', codigo: '', nombre: '', descripcion: '', activo: true })

    else if (tab === 'estantes') setForm({ id_bodega: bodegas[0]?.id || '', id_ubicacion: ubicaciones[0]?.id || '', codigo: '', nombre: '', descripcion: '', activo: true })

    else if (tab === 'niveles') setForm({ codigo: '', nombre: '', activo: true })

    else if (tab === 'filas') setForm({ codigo: '', nombre: '', activo: true })

    else if (tab === 'categorias-repuestos') setForm({ nombre: '', descripcion: '' })

    else if (tab === 'festivos') setForm({ fecha: hoyStr(), nombre: '', anio: new Date().getFullYear() })

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

    } else if (tab === 'festivos') {

      setForm({ fecha: c.fecha ? fechaAStr(parseFechaLocal(String(c.fecha))) : '', nombre: c.nombre || '', anio: c.anio || new Date().getFullYear() })

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

    } else if (tab === 'festivos' && (!form.fecha || !form.nombre?.trim() || !form.anio)) {

      setError('Fecha, nombre y año son obligatorios')

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

      } else if (tab === 'festivos') {

        const payload = { fecha: form.fecha, nombre: form.nombre.trim(), anio: Number(form.anio) }

        if (editando) {

          await api.put(`/festivos/${editando.id}`, payload)

        } else {

          await api.post('/festivos/', payload)

        }

      }

      cargar()

      setModalAbierto(false)

      setEditando(null)

    } catch (err) {

      setError(normalizeDetail(err.response?.data?.detail) || 'Error al guardar')

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

      } else if (tab === 'festivos') {

        await api.delete(`/festivos/${categoriaAEliminar.id}`)

      }

      cargar()

      setModalEliminar(false)

      setCategoriaAEliminar(null)

    } catch (err) {

      showError(err, 'Error al eliminar')

    } finally {

      setEnviandoEliminar(false)

    }

  }



  return (

    <div className="min-h-0 flex flex-col">

      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Configuración</h1>
        <button onClick={cargar} disabled={loading} className="min-h-[44px] px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-60 text-sm font-medium touch-manipulation">
          {loading ? 'Cargando...' : '↻ Actualizar'}
        </button>
      </div>

      <div className="overflow-x-auto -mx-2 sm:mx-0 mb-4 sm:mb-6 border-b border-slate-200">

        <div className="flex gap-1 sm:gap-2 min-w-max px-2 sm:px-0">

          <button

            onClick={() => { setTab('categorias-servicios'); setSearchParams({ tab: 'categorias-servicios' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'categorias-servicios' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Categorías de servicios

          </button>

          <button

            onClick={() => { setTab('categorias-repuestos'); setSearchParams({ tab: 'categorias-repuestos' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'categorias-repuestos' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Categorías de repuestos

          </button>

          <button

            onClick={() => { setTab('bodegas'); setSearchParams({ tab: 'bodegas' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'bodegas' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Bodegas

          </button>

          <button

            onClick={() => { setTab('ubicaciones'); setSearchParams({ tab: 'ubicaciones' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'ubicaciones' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Ubicaciones

          </button>

          <button

            onClick={() => { setTab('estantes'); setSearchParams({ tab: 'estantes' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'estantes' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Estantes

          </button>

          <button

            onClick={() => { setTab('niveles'); setSearchParams({ tab: 'niveles' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'niveles' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Niveles

          </button>

          <button

            onClick={() => { setTab('filas'); setSearchParams({ tab: 'filas' }) }}

            className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'filas' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

          >

            Filas

          </button>

          {esAdmin && (

            <>

              <button

                onClick={() => { setTab('usuarios'); setSearchParams({ tab: 'usuarios' }) }}

                className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'usuarios' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

              >

                Usuarios

              </button>

              <button

                onClick={() => { setTab('usuarios-bodegas'); setSearchParams({ tab: 'usuarios-bodegas' }) }}

                className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'usuarios-bodegas' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

              >

                Usuarios y bodegas

              </button>

              <button

                onClick={() => { setTab('festivos'); setSearchParams({ tab: 'festivos' }) }}

                className={`px-3 sm:px-4 py-2 font-medium rounded-t-lg min-h-[44px] touch-manipulation active:bg-slate-100 ${tab === 'festivos' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}

              >

                Festivos

              </button>

            </>

          )}

        </div>

      </div>



      {tab === 'ubicaciones' && (

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Inventario

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Ubicaciones</h2>

              <label className="flex items-center gap-2 text-sm text-slate-600 min-h-[44px] py-1 cursor-pointer touch-manipulation">

                <input type="checkbox" checked={mostrarInactivas} onChange={(e) => setMostrarInactivas(e.target.checked)} className="rounded border-slate-300 w-5 h-5" />

                Mostrar inactivas

              </label>

              <select

                value={filtroBodega}

                onChange={(e) => setFiltroBodega(e.target.value)}

                className="px-3 py-2 min-h-[48px] border border-slate-300 rounded-lg text-base sm:text-sm"

              >

                <option value="">Todas las bodegas</option>

                {bodegas.filter(b => b.activo !== false).map((b) => (

                  <option key={b.id} value={b.id}>{b.nombre}</option>

                ))}

              </select>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Bodega</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    {esAdmin && (

                      <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>

                    )}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {(() => {

                    const list = ubicaciones

                      .filter(u => !filtroBodega || u.id_bodega === Number(filtroBodega))

                      .filter(u => mostrarInactivas || u.activo !== false)

                    if (list.length === 0) {

                      return (

                        <tr>

                          <td colSpan={esAdmin ? 7 : 6} className="px-2 sm:px-4 py-8 text-center text-slate-500">

                            No hay ubicaciones. Crea bodegas primero y luego añade ubicaciones (ej: Pasillo A-1, Estante B2).

                          </td>

                        </tr>

                      )

                    }

                    return list.map((u) => (

                      <tr key={u.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{u.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{u.bodega_nombre || '-'}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-700 font-mono">{u.codigo}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-800">{u.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={u.descripcion || ''}>{u.descripcion || '-'}</td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${u.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {u.activo !== false ? 'Activa' : 'Inactiva'}

                          </span>

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button type="button" onClick={() => abrirEditar(u)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">✏️</button>

                              <button type="button" onClick={() => abrirModalEliminar(u)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>

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

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Inventario

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Estantes</h2>

              <label className="flex items-center gap-2 text-sm text-slate-600 min-h-[44px] py-1 cursor-pointer touch-manipulation">

                <input type="checkbox" checked={mostrarInactivas} onChange={(e) => setMostrarInactivas(e.target.checked)} className="rounded border-slate-300 w-5 h-5" />

                Mostrar inactivas

              </label>

              <select value={filtroBodega} onChange={(e) => setFiltroBodega(e.target.value)} className="px-3 py-2 min-h-[48px] border border-slate-300 rounded-lg text-base sm:text-sm">

                <option value="">Todas las bodegas</option>

                {bodegas.filter(b => b.activo !== false).map((b) => (

                  <option key={b.id} value={b.id}>{b.nombre}</option>

                ))}

              </select>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Bodega</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Ubicación</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    {esAdmin && <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {(() => {

                    const listFiltered = estantes

                      .filter(e => {

                        const u = ubicaciones.find(uu => uu.id === e.id_ubicacion)

                        return !filtroBodega || (u && u.id_bodega === Number(filtroBodega))

                      })

                      .filter(e => mostrarInactivas || e.activo !== false)

                    if (listFiltered.length === 0) {

                      return (

                        <tr><td colSpan={esAdmin ? 8 : 7} className="px-2 sm:px-4 py-8 text-center text-slate-500">

                          No hay estantes. Crea bodegas, luego ubicaciones (zonas/pasillos) y después estantes (ej: E1, Estante 1).

                        </td></tr>

                      )

                    }

                    return listFiltered.map((e) => (

                      <tr key={e.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{e.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{e.bodega_nombre || '-'}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{e.ubicacion_nombre || '-'}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-700 font-mono">{e.codigo}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-800">{e.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={e.descripcion || ''}>{e.descripcion || '-'}</td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${e.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {e.activo !== false ? 'Activo' : 'Inactivo'}

                          </span>

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button type="button" onClick={() => abrirEditar(e)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">✏️</button>

                              <button type="button" onClick={() => abrirModalEliminar(e)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>

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

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Inventario

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Niveles (A, B, C, D...)</h2>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    {esAdmin && <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {niveles.length === 0 ? (

                    <tr><td colSpan={esAdmin ? 5 : 4} className="px-2 sm:px-4 py-8 text-center text-slate-500">No hay niveles. Crea A, B, C, D para organizar verticalmente.</td></tr>

                  ) : (

                    niveles.map((n) => (

                      <tr key={n.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{n.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-mono text-slate-800">{n.codigo}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-800">{n.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${n.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {n.activo !== false ? 'Activo' : 'Inactivo'}

                          </span>

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button type="button" onClick={() => abrirEditar(n)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">✏️</button>

                              <button type="button" onClick={() => abrirModalEliminar(n)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>

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

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Inventario

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Filas (1, 2, 3, 4, 5...)</h2>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    {esAdmin && <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {filas.length === 0 ? (

                    <tr><td colSpan={esAdmin ? 5 : 4} className="px-2 sm:px-4 py-8 text-center text-slate-500">No hay filas. Crea 1, 2, 3, 4, 5 para posiciones horizontales.</td></tr>

                  ) : (

                    filas.map((f) => (

                      <tr key={f.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{f.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-mono text-slate-800">{f.codigo}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-800">{f.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${f.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {f.activo !== false ? 'Activa' : 'Inactiva'}

                          </span>

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button type="button" onClick={() => abrirEditar(f)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">✏️</button>

                              <button type="button" onClick={() => abrirModalEliminar(f)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>

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



      {tab === 'festivos' && esAdmin && (

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <h2 className="text-lg font-semibold text-slate-800">Días festivos</h2>

              <select

                value={filtroAnioFestivos}

                onChange={(e) => setFiltroAnioFestivos(e.target.value)}

                className="px-3 py-2 min-h-[48px] border border-slate-300 rounded-lg text-base sm:text-sm"

              >

                {[new Date().getFullYear() - 1, new Date().getFullYear(), new Date().getFullYear() + 1].map((a) => (

                  <option key={a} value={String(a)}>{a}</option>

                ))}

              </select>

            </div>

            <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

              + Nuevo festivo

            </button>

          </div>

          {loading ? (

            <p className="p-8 text-slate-500 text-center">Cargando...</p>

          ) : (

            <div className="overflow-x-auto">

              <table className="min-w-full divide-y divide-slate-200">

                <thead className="bg-slate-50">

                  <tr>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Año</th>

                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {festivos.filter((f) => String(f.anio) === filtroAnioFestivos).length === 0 ? (

                    <tr><td colSpan={5} className="px-2 sm:px-4 py-8 text-center text-slate-500">No hay festivos para este año. Agrega días festivos para el checador.</td></tr>

                  ) : (

                    festivos.filter((f) => String(f.anio) === filtroAnioFestivos).map((fv) => (

                      <tr key={fv.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{fv.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-800">{fv.fecha}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-800">{fv.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{fv.anio}</td>

                        <td className="px-2 sm:px-4 py-3 text-right">

                          <div className="flex gap-1 justify-end">

                            <button type="button" onClick={() => abrirEditar(fv)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">✏️</button>

                            <button type="button" onClick={() => abrirModalEliminar(fv)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Eliminar">🗑️</button>

                          </div>

                        </td>

                      </tr>

                    ))

                  )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      )}



      {tab === 'usuarios' && esAdmin && (

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <h2 className="text-lg font-semibold text-slate-800">Usuarios del negocio</h2>

            <Link to="/configuracion/usuarios/nuevo" className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation inline-flex items-center">
              + Nuevo usuario
            </Link>

          </div>

          {loading ? (

            <p className="p-8 text-slate-500 text-center">Cargando...</p>

          ) : (

            <div className="overflow-x-auto">

              <table className="min-w-full divide-y divide-slate-200">

                <thead className="bg-slate-50">

                  <tr>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Rol</th>

                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Salario</th>

                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Bono punt.</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Periodo</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {usuarios.length === 0 ? (

                    <tr><td colSpan={9} className="px-2 sm:px-4 py-8 text-center text-slate-500">No hay usuarios. Crea el primero con &quot;Nuevo usuario&quot;.</td></tr>

                  ) : (

                    usuarios.map((u) => (

                      <tr key={u.id_usuario} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{u.id_usuario}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{u.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{u.email}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm">

                          <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700">{typeof u.rol === 'string' ? u.rol : u.rol?.value ?? '-'}</span>

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-right font-medium text-slate-800">

                          {u.salario_base != null ? `$${Number(u.salario_base).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '-'}

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-right text-slate-700">

                          {u.bono_puntualidad != null ? `$${Number(u.bono_puntualidad).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '-'}

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">

                          {(() => { const pp = typeof u.periodo_pago === 'string' ? u.periodo_pago : u.periodo_pago?.value ?? ''; return pp === 'SEMANAL' ? 'Semanal' : pp === 'QUINCENAL' ? 'Quincenal' : pp === 'MENSUAL' ? 'Mensual' : '-' })()}

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${u.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {u.activo !== false ? 'Activo' : 'Inactivo'}

                          </span>

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-right">

                          <Link to={`/configuracion/usuarios/editar/${u.id_usuario}`} className="min-h-[36px] px-3 py-1.5 inline-flex text-sm text-primary-600 hover:text-primary-700 font-medium mr-2 rounded touch-manipulation active:bg-primary-50">Editar</Link>

                          <Link to={`/configuracion?tab=usuarios-bodegas`} className="min-h-[36px] px-3 py-1.5 inline-flex items-center text-sm text-slate-600 hover:text-slate-800 rounded touch-manipulation active:bg-slate-100">Bodegas</Link>

                        </td>

                      </tr>

                    ))

                  )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      )}



      {tab === 'usuarios-bodegas' && esAdmin && (

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200">

            <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

              ← Volver a Inventario

            </Link>

            <h2 className="text-lg font-semibold text-slate-800 mt-3">Usuarios y bodegas permitidas</h2>

            <p className="text-sm text-slate-600 mt-1">Asigna bodegas a cada usuario. Si no tiene bodegas asignadas, verá todas. ADMIN siempre ve todo.</p>

          </div>

          {loading ? (

            <p className="p-8 text-slate-500 text-center">Cargando...</p>

          ) : (

            <div className="overflow-x-auto">

              <table className="min-w-full divide-y divide-slate-200">

                <thead className="bg-slate-50">

                  <tr>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Usuario</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Rol</th>

                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acción</th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {usuarios.length === 0 ? (

                    <tr><td colSpan={4} className="px-2 sm:px-4 py-8 text-center text-slate-500">No hay usuarios.</td></tr>

                  ) : (

                    usuarios.map((u) => (

                      <tr key={u.id_usuario} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{u.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{u.email}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">

                          <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700">{typeof u.rol === 'string' ? u.rol : u.rol?.value ?? '-'}</span>

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-right">

                          <button

                            type="button"

                            onClick={() => abrirModalBodegasUsuario(u)}

                            className="min-h-[36px] px-3 py-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium rounded touch-manipulation active:bg-primary-50"

                          >

                            Asignar bodegas

                          </button>

                        </td>

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

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Inventario

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Bodegas</h2>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    {esAdmin && (

                      <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>

                    )}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {bodegas.length === 0 ? (

                    <tr>

                      <td colSpan={esAdmin ? 5 : 4} className="px-2 sm:px-4 py-8 text-center text-slate-500">

                        No hay bodegas. Crea una para organizar el almacenamiento (Principal, Taller, Mostrador, etc.).

                      </td>

                    </tr>

                  ) : (

                    bodegas.map((b) => (

                      <tr key={b.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{b.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{b.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={b.descripcion || ''}>

                          {b.descripcion || '-'}

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${b.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {b.activo !== false ? 'Activa' : 'Inactiva'}

                          </span>

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button onClick={() => abrirEditar(b)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">✏️</button>

                              <button onClick={() => abrirModalEliminar(b)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>

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

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/servicios" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Servicios

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Categorías de servicios</h2>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>

                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>

                    {esAdmin && (

                      <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>

                    )}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {categoriasServicios.length === 0 ? (

                    <tr>

                      <td colSpan={esAdmin ? 5 : 4} className="px-2 sm:px-4 py-8 text-center text-slate-500">

                        No hay categorías. Crea una para asignarla a los servicios.

                      </td>

                    </tr>

                  ) : (

                    categoriasServicios.map((c) => (

                      <tr key={c.id} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{c.id}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{c.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={c.descripcion || ''}>

                          {c.descripcion || '-'}

                        </td>

                        <td className="px-2 sm:px-4 py-3 text-center">

                          <span className={`px-2 py-0.5 rounded text-xs ${c.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>

                            {c.activo !== false ? 'Activa' : 'Inactiva'}

                          </span>

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button onClick={() => abrirEditar(c)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">

                                ✏️

                              </button>

                              <button onClick={() => abrirModalEliminar(c)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Eliminar">

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

        <div className="bg-white rounded-lg shadow border border-slate-200 min-h-0 flex flex-col">

          <div className="p-4 border-b border-slate-200 flex justify-between items-center flex-wrap gap-2">

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">

              <Link to="/inventario" className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 hover:border-slate-400 font-medium text-sm bg-white shadow-sm touch-manipulation">

                ← Volver a Inventario

              </Link>

              <h2 className="text-lg font-semibold text-slate-800">Categorías de repuestos</h2>

            </div>

            {esAdmin && (

              <button onClick={abrirNuevo} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">

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

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>

                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>

                    {esAdmin && (

                      <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>

                    )}

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-200">

                  {categoriasRepuestos.length === 0 ? (

                    <tr>

                      <td colSpan={esAdmin ? 4 : 3} className="px-2 sm:px-4 py-8 text-center text-slate-500">

                        No hay categorías. Crea una para asignarla a los repuestos del inventario.

                      </td>

                    </tr>

                  ) : (

                    categoriasRepuestos.map((c) => (

                      <tr key={c.id_categoria} className="hover:bg-slate-50">

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{c.id_categoria}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{c.nombre}</td>

                        <td className="px-2 sm:px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={c.descripcion || ''}>

                          {c.descripcion || '-'}

                        </td>

                        {esAdmin && (

                          <td className="px-2 sm:px-4 py-3 text-right">

                            <div className="flex gap-1 justify-end">

                              <button onClick={() => abrirEditar(c)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-200 rounded touch-manipulation" title="Editar">

                                ✏️

                              </button>

                              <button onClick={() => abrirModalEliminar(c)} className="min-h-[36px] min-w-[36px] px-2 py-1 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Eliminar">

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



      <Modal titulo={editando ? (tab === 'ubicaciones' ? 'Editar ubicación' : tab === 'bodegas' ? 'Editar bodega' : tab === 'estantes' ? 'Editar estante' : tab === 'niveles' ? 'Editar nivel' : tab === 'filas' ? 'Editar fila' : tab === 'festivos' ? 'Editar festivo' : 'Editar categoría') : (tab === 'ubicaciones' ? 'Nueva ubicación' : tab === 'bodegas' ? 'Nueva bodega' : tab === 'estantes' ? 'Nuevo estante' : tab === 'niveles' ? 'Nuevo nivel' : tab === 'filas' ? 'Nueva fila' : tab === 'festivos' ? 'Nuevo festivo' : 'Nueva categoría')} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }}>

        <form onSubmit={handleSubmit} className="space-y-4">

          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

          {tab === 'ubicaciones' && (

            <>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Bodega *</label>

                <select value={form.id_bodega} onChange={(e) => setForm({ ...form, id_bodega: e.target.value })} className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm" required>

                  <option value="">Selecciona bodega</option>

                  {bodegas.filter(b => b.activo !== false).map((b) => (

                    <option key={b.id} value={b.id}>{b.nombre}</option>

                  ))}

                </select>

              </div>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>

                <input type="text" value={form.codigo || ''} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="Ej: A1, B2, PASILLO-01" className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono text-base sm:text-sm" required />

              </div>

            </>

          )}

          {tab === 'estantes' && (

            <>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Bodega *</label>

                <select value={form.id_bodega} onChange={(e) => setForm({ ...form, id_bodega: e.target.value, id_ubicacion: '' })} className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm" required>

                  <option value="">Selecciona bodega</option>

                  {bodegas.filter(b => b.activo !== false).map((b) => (

                    <option key={b.id} value={b.id}>{b.nombre}</option>

                  ))}

                </select>

              </div>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Ubicación (zona/pasillo) *</label>

                <select value={form.id_ubicacion} onChange={(e) => setForm({ ...form, id_ubicacion: e.target.value })} className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm" required disabled={!form.id_bodega}>

                  <option value="">Selecciona ubicación</option>

                  {ubicaciones.filter(u => Number(u.id_bodega) === Number(form.id_bodega) && u.activo !== false).map((u) => (

                    <option key={u.id} value={u.id}>{u.codigo} - {u.nombre}</option>

                  ))}

                </select>

              </div>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>

                <input type="text" value={form.codigo || ''} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="Ej: E1, EST-01" className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono text-base sm:text-sm" required />

              </div>

            </>

          )}

          {(tab === 'niveles' || tab === 'filas') && (

            <div>

              <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>

              <input type="text" value={form.codigo || ''} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder={tab === 'niveles' ? 'Ej: A, B, C' : 'Ej: 1, 2, 3'} className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono text-base sm:text-sm" required />

            </div>

          )}

          {tab === 'festivos' && (

            <>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Fecha *</label>

                <input type="date" value={form.fecha || ''} onChange={(e) => setForm({ ...form, fecha: e.target.value })} className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm" required />

              </div>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>

                <input type="text" value={form.nombre || ''} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: Navidad" className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm" required />

              </div>

              <div>

                <label className="block text-sm font-medium text-slate-700 mb-1">Año *</label>

                <input type="number" min={2000} max={2100} value={form.anio ?? ''} onChange={(e) => setForm({ ...form, anio: e.target.value ? Number(e.target.value) : '' })} placeholder={new Date().getFullYear()} className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm" required />

              </div>

            </>

          )}

          {tab !== 'festivos' && (

          <div>

            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>

            <input

              type="text"

              value={form.nombre || ''}

              onChange={(e) => setForm({ ...form, nombre: e.target.value })}

              placeholder={tab === 'ubicaciones' ? 'Ej: Pasillo A, Estante 1' : tab === 'categorias-repuestos' ? 'Ej: Aceites' : tab === 'bodegas' ? 'Ej: Bodega principal' : 'Ej: Mantenimiento'}

              className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm"

              required

            />

          </div>

          )}

          {tab !== 'niveles' && tab !== 'filas' && tab !== 'festivos' && (

            <div>

              <label className="block text-sm font-medium text-slate-700 mb-1">Descripción (opcional)</label>

              <textarea

                value={form.descripcion || ''}

                onChange={(e) => setForm({ ...form, descripcion: e.target.value })}

                rows={2}

                placeholder={tab === 'ubicaciones' ? 'Ej: Pasillo principal, nivel superior' : tab === 'estantes' ? 'Ej: Estante principal del pasillo A' : tab === 'categorias-repuestos' ? 'Ej: Aceites, lubricantes y aditivos' : tab === 'bodegas' ? 'Ej: Bodega principal' : 'Descripción breve'}

                className="w-full px-4 py-3 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm"

              />

            </div>

          )}

          {((tab === 'categorias-servicios' || tab === 'bodegas' || tab === 'ubicaciones' || tab === 'estantes' || tab === 'niveles' || tab === 'filas')) && (

            <label className="flex items-center gap-2 cursor-pointer min-h-[44px] touch-manipulation">

              <input

                type="checkbox"

                checked={form.activo}

                onChange={(e) => setForm({ ...form, activo: e.target.checked })}

                className="rounded border-slate-300 w-5 h-5"

              />

              <span className="text-sm text-slate-700">Activo</span>

            </label>

          )}

          <div className="flex justify-end gap-2 pt-2">

            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="px-4 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">

              Cancelar

            </button>

            <button type="submit" disabled={enviando} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">

              {enviando ? 'Guardando...' : editando ? 'Guardar' : 'Crear'}

            </button>

          </div>

        </form>

      </Modal>



      <Modal titulo={tab === 'ubicaciones' ? 'Desactivar ubicación' : tab === 'estantes' ? 'Desactivar estante' : tab === 'niveles' ? 'Desactivar nivel' : tab === 'filas' ? 'Desactivar fila' : tab === 'bodegas' ? 'Desactivar bodega' : tab === 'festivos' ? 'Eliminar festivo' : 'Eliminar categoría'} abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setCategoriaAEliminar(null) }}>

        <div className="space-y-4">

          {categoriaAEliminar && (

            <>

              <p className="text-slate-600">

                ¿{tab === 'festivos' ? 'Eliminar' : ['ubicaciones','bodegas','estantes','niveles','filas'].includes(tab) ? 'Desactivar' : 'Eliminar'} {tab === 'festivos' ? 'el festivo' : tab === 'ubicaciones' ? 'la ubicación' : tab === 'estantes' ? 'el estante' : tab === 'niveles' ? 'el nivel' : tab === 'filas' ? 'la fila' : tab === 'bodegas' ? 'la bodega' : 'la categoría'} <strong>{categoriaAEliminar.nombre}</strong>?{tab === 'festivos' ? '' : ['ubicaciones','bodegas','estantes','niveles','filas'].includes(tab) ? ' Se marcará como inactiva.' : ' No podrás eliminarla si tiene ' + (tab === 'categorias-repuestos' ? 'repuestos' : 'servicios') + ' asignados. Asigna otra categoría primero.'}

              </p>

              <div className="flex justify-end gap-2">

                <button type="button" onClick={() => { setModalEliminar(false); setCategoriaAEliminar(null) }} className="px-4 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">

                  Cancelar

                </button>

                <button type="button" onClick={confirmarEliminar} disabled={enviandoEliminar} className="px-4 py-2 min-h-[44px] bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">

                  {enviandoEliminar ? 'Eliminando...' : 'Eliminar'}

                </button>

              </div>

            </>

          )}

        </div>

      </Modal>




      <Modal titulo={usuarioEditandoBodegas ? `Bodegas permitidas - ${usuarioEditandoBodegas.nombre}` : 'Bodegas permitidas'} abierto={modalBodegasUsuario} onCerrar={() => { setModalBodegasUsuario(false); setUsuarioEditandoBodegas(null) }}>

        <div className="space-y-4">

          <p className="text-sm text-slate-600">

            Si no seleccionas ninguna bodega, el usuario verá todas. Si seleccionas una o más, solo verá inventario de esas bodegas.

          </p>

          <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">

            {bodegas.filter((b) => b.activo !== false).map((b) => (

              <label key={b.id} className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 p-3 rounded min-h-[44px] touch-manipulation">

                <input

                  type="checkbox"

                  checked={bodegasUsuario.includes(b.id)}

                  onChange={() => toggleBodegaUsuario(b.id)}

                  className="rounded border-slate-300 w-5 h-5"

                />

                <span className="text-sm text-slate-800">{b.nombre}</span>

              </label>

            ))}

            {bodegas.filter((b) => b.activo !== false).length === 0 && (

              <p className="text-sm text-slate-500">No hay bodegas activas.</p>

            )}

          </div>

          <div className="flex justify-end gap-2 pt-2">

            <button type="button" onClick={() => { setModalBodegasUsuario(false); setUsuarioEditandoBodegas(null) }} className="px-4 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">

              Cancelar

            </button>

            <button type="button" onClick={guardarBodegasUsuario} disabled={guardandoBodegasUsuario} className="px-4 py-2 min-h-[44px] bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">

              {guardandoBodegasUsuario ? 'Guardando...' : 'Guardar'}

            </button>

          </div>

        </div>

      </Modal>

    </div>

  )

}
