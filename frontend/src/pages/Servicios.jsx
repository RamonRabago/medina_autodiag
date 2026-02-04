import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Servicios() {
  const { user } = useAuth()
  const [servicios, setServicios] = useState([])
  const [loading, setLoading] = useState(true)
  const [buscar, setBuscar] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [categorias, setCategorias] = useState([])
  const [filtroActivo, setFiltroActivo] = useState('') // '', 'true', 'false'
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20

  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
    id_categoria: '',
    precio_base: '',
    tiempo_estimado_minutos: 60,
    activo: true,
    requiere_repuestos: false,
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const [modalEliminar, setModalEliminar] = useState(false)
  const [servicioAEliminar, setServicioAEliminar] = useState(null)
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [exportando, setExportando] = useState(false)

  const esAdmin = user?.rol === 'ADMIN'
  const [mostrarSubir, setMostrarSubir] = useState(false)

  useEffect(() => {
    const el = document.querySelector('main')
    const handleScroll = () => setMostrarSubir(el?.scrollTop > 300)
    el?.addEventListener('scroll', handleScroll)
    return () => el?.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollArriba = () => {
    document.querySelector('main')?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = { limit: 10000 }
      if (buscar.trim()) params.buscar = buscar.trim()
      if (filtroCategoria) params.categoria = parseInt(filtroCategoria)
      if (filtroActivo === 'true') params.activo = true
      if (filtroActivo === 'false') params.activo = false
      const res = await api.get('/exportaciones/servicios', { params, responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `servicios_${new Date().toISOString().slice(0, 10)}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  const cargar = () => {
    const params = { skip: (pagina - 1) * limit, limit }
    if (buscar.trim()) params.buscar = buscar.trim()
    if (filtroCategoria) params.categoria = parseInt(filtroCategoria)
    if (filtroActivo === 'true') params.activo = true
    if (filtroActivo === 'false') params.activo = false
    api.get('/servicios/', { params }).then((res) => {
      const d = res.data
      setServicios(d?.servicios ?? [])
      setTotal(d?.total ?? 0)
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => setServicios([]))
    .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, buscar, filtroCategoria, filtroActivo])

  useEffect(() => {
    api.get('/categorias-servicios/', { params: { activo: true, limit: 200 } })
      .then((r) => {
        const list = Array.isArray(r.data) ? r.data : []
        // Ordenar para que "Otros" aparezca al final
        list.sort((a, b) => {
          if ((a.nombre || '').toLowerCase() === 'otros') return 1
          if ((b.nombre || '').toLowerCase() === 'otros') return -1
          return (a.nombre || '').localeCompare(b.nombre || '')
        })
        setCategorias(list)
      })
      .catch(() => setCategorias([]))
  }, [])

  const abrirNuevo = () => {
    setEditando(null)
    const primCat = categorias[0]?.id
    setForm({
      codigo: '',
      nombre: '',
      descripcion: '',
      id_categoria: primCat ?? '',
      precio_base: '',
      tiempo_estimado_minutos: 60,
      activo: true,
      requiere_repuestos: false,
    })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (s) => {
    setEditando(s)
    setForm({
      codigo: s.codigo || '',
      nombre: s.nombre || '',
      descripcion: s.descripcion || '',
      id_categoria: s.id_categoria ?? '',
      precio_base: s.precio_base ?? '',
      tiempo_estimado_minutos: s.tiempo_estimado_minutos ?? 60,
      activo: s.activo !== false,
      requiere_repuestos: !!s.requiere_repuestos,
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
    if (!form.id_categoria) {
      setError('Selecciona una categoría')
      return
    }
    const precio = parseFloat(form.precio_base)
    if (isNaN(precio) || precio < 0) {
      setError('Precio debe ser un número mayor o igual a 0')
      return
    }
    const tiempo = parseInt(form.tiempo_estimado_minutos) || 60
    if (tiempo < 1) {
      setError('Tiempo estimado debe ser al menos 1 minuto')
      return
    }
    setEnviando(true)
    try {
      const payload = {
        codigo: form.codigo.trim(),
        nombre: form.nombre.trim(),
        descripcion: form.descripcion?.trim() || null,
        id_categoria: parseInt(form.id_categoria),
        precio_base: precio,
        tiempo_estimado_minutos: tiempo,
        activo: form.activo,
        requiere_repuestos: form.requiere_repuestos,
      }
      if (editando) {
        await api.put(`/servicios/${editando.id}`, payload)
      } else {
        await api.post('/servicios/', payload)
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

  const abrirModalEliminar = (s) => {
    setServicioAEliminar(s)
    setModalEliminar(true)
  }

  const confirmarEliminar = async () => {
    if (!servicioAEliminar) return
    setEnviandoEliminar(true)
    try {
      await api.delete(`/servicios/${servicioAEliminar.id}`)
      cargar()
      setModalEliminar(false)
      setServicioAEliminar(null)
    } catch (err) {
      const d = err.response?.data?.detail
      alert(typeof d === 'string' ? d : (Array.isArray(d) ? d.map((x) => x?.msg ?? x).join(', ') : 'Error al desactivar'))
    } finally {
      setEnviandoEliminar(false)
    }
  }

  const activarServicio = async (s) => {
    try {
      await api.post(`/servicios/${s.id}/activar`)
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      alert(typeof d === 'string' ? d : 'Error al reactivar')
    }
  }

  const nombreCategoria = (s) => s?.categoria_nombre ?? '-'

  if (loading && servicios.length === 0) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Servicios</h1>
        <div className="flex gap-2 items-center flex-wrap">
          <input
            type="text"
            placeholder="Buscar por código o nombre..."
            value={buscar}
            onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]"
          />
          <select
            value={filtroCategoria}
            onChange={(e) => { setFiltroCategoria(e.target.value); setPagina(1) }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todas las categorías</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
          {esAdmin && (
            <Link to="/configuracion?tab=categorias-servicios" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar categorías de servicios">
              ⚙️ Categorías
            </Link>
          )}
          <select
            value={filtroActivo}
            onChange={(e) => { setFiltroActivo(e.target.value); setPagina(1) }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
          <button onClick={exportarExcel} disabled={exportando} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 text-sm">
            📥 {exportando ? 'Exportando...' : 'Exportar a Excel'}
          </button>
          {esAdmin && (
            <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
              Nuevo servicio
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Código</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Categoría</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Descripción</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Tiempo</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Precio</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                {esAdmin && (
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {servicios.length === 0 ? (
                <tr>
                  <td colSpan={esAdmin ? 8 : 7} className="px-4 py-8 text-center text-slate-500">
                    No hay servicios
                  </td>
                </tr>
              ) : (
                servicios.map((s) => (
                  <tr key={s.id} className={s.activo === false ? 'bg-slate-50' : 'hover:bg-slate-50'}>
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">{s.codigo}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{s.nombre}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{nombreCategoria(s)}</td>
                    <td className="px-4 py-3 text-sm text-slate-500 max-w-[200px] truncate" title={s.descripcion || ''}>
                      {s.descripcion || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-slate-600">
                      {s.tiempo_estimado_minutos ?? 0} min
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-medium">
                      ${(Number(s.precio_base) || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${s.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                        {s.activo !== false ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    {esAdmin && (
                      <td className="px-4 py-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {s.activo !== false ? (
                            <>
                              <button onClick={() => abrirEditar(s)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button onClick={() => abrirModalEliminar(s)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                            </>
                          ) : (
                            <button onClick={() => activarServicio(s)} className="text-sm text-green-600 hover:text-green-700" title="Reactivar">✓ Reactivar</button>
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
            className="px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary-600 transition-colors"
          >
            ← Anterior
          </button>
          <span className="px-4 py-2 text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-200">
            Página {pagina} de {totalPaginas} ({total} registros)
          </span>
          <button
            onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
            disabled={pagina >= totalPaginas}
            className="px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary-600 transition-colors"
          >
            Siguiente →
          </button>
        </div>
      )}

      {mostrarSubir && (
        <button
          onClick={scrollArriba}
          className="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full bg-primary-600 text-white shadow-lg hover:bg-primary-700 flex items-center justify-center text-xl transition-all hover:scale-110"
          title="Volver al principio"
        >
          ↑
        </button>
      )}

      <Modal titulo={editando ? 'Editar servicio' : 'Nuevo servicio'} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }} size="lg">
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Código *</label>
              <input
                type="text"
                value={form.codigo}
                onChange={(e) => setForm({ ...form, codigo: e.target.value })}
                placeholder="Ej: SRV-001"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
              <input
                type="text"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                placeholder="Ej: Cambio de Aceite y Filtro"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción (opcional)</label>
            <textarea
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              rows={2}
              placeholder="Descripción breve del servicio"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 placeholder-slate-400"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Categoría *</label>
              <select
                value={form.id_categoria}
                onChange={(e) => setForm({ ...form, id_categoria: e.target.value })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              >
                <option value="">Seleccionar...</option>
                {categorias.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Precio base *</label>
              <input
                type="number"
                step={0.01}
                min={0}
                value={form.precio_base}
                onChange={(e) => setForm({ ...form, precio_base: e.target.value })}
                placeholder="0.00"
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Tiempo (min) *</label>
              <input
                type="number"
                min={1}
                value={form.tiempo_estimado_minutos}
                onChange={(e) => setForm({ ...form, tiempo_estimado_minutos: parseInt(e.target.value) || 60 })}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-6 py-3 px-4 bg-slate-50 rounded-lg border border-slate-100">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.activo}
                onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-slate-700">Activo</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer" title="Indica si este servicio típicamente requiere repuestos">
              <input
                type="checkbox"
                checked={form.requiere_repuestos}
                onChange={(e) => setForm({ ...form, requiere_repuestos: e.target.checked })}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-slate-700">Requiere repuestos</span>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-1 border-t border-slate-200">
            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium">
              Cancelar
            </button>
            <button type="submit" disabled={enviando} className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 font-medium">
              {enviando ? 'Guardando...' : (editando ? 'Guardar cambios' : 'Crear')}
            </button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Desactivar servicio" abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setServicioAEliminar(null) }}>
        <div className="space-y-4">
          {servicioAEliminar && (
            <>
              <p className="text-slate-600">
                ¿Desactivar el servicio <strong>{servicioAEliminar.nombre}</strong> ({servicioAEliminar.codigo})?
                No se eliminará, solo dejará de aparecer como opción activa.
              </p>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminar(false); setServicioAEliminar(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">
                  Cancelar
                </button>
                <button type="button" onClick={confirmarEliminar} disabled={enviandoEliminar} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                  {enviandoEliminar ? 'Desactivando...' : 'Desactivar'}
                </button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  )
}
