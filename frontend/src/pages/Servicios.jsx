import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { useApiQuery, useInvalidateQueries } from '../hooks/useApi'
import { hoyStr } from '../utils/fechas'
import { aNumero, aEntero } from '../utils/numeros'
import { normalizeDetail, showError } from '../utils/toast'

export default function Servicios() {
  const { user } = useAuth()
  const invalidate = useInvalidateQueries()
  const [buscar, setBuscar] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroActivo, setFiltroActivo] = useState('') // '', 'true', 'false'
  const [pagina, setPagina] = useState(1)
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

  const paramsServicios = { skip: (pagina - 1) * limit, limit }
  if (buscar.trim()) paramsServicios.buscar = buscar.trim()
  if (filtroCategoria) paramsServicios.categoria = aEntero(filtroCategoria)
  if (filtroActivo === 'true') paramsServicios.activo = true
  if (filtroActivo === 'false') paramsServicios.activo = false

  const { data: dataServicios, isLoading: loading, refetch: refetchServicios } = useApiQuery(
    ['servicios', pagina, buscar, filtroCategoria, filtroActivo],
    () => api.get('/servicios/', { params: paramsServicios }).then((r) => r.data),
  )

  const { data: dataCategorias } = useApiQuery(
    ['categorias-servicios'],
    async () => {
      const r = await api.get('/categorias-servicios/', { params: { activo: true, limit: 200 } })
      const list = Array.isArray(r.data) ? r.data : []
      list.sort((a, b) => {
        if ((a.nombre || '').toLowerCase() === 'otros') return 1
        if ((b.nombre || '').toLowerCase() === 'otros') return -1
        return (a.nombre || '').localeCompare(b.nombre || '')
      })
      return list
    },
  )

  const servicios = dataServicios?.servicios ?? []
  const total = dataServicios?.total ?? 0
  const totalPaginas = dataServicios?.total_paginas ?? 1
  const categorias = dataCategorias ?? []

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
      if (filtroCategoria) params.categoria = aEntero(filtroCategoria)
      if (filtroActivo === 'true') params.activo = true
      if (filtroActivo === 'false') params.activo = false
      const res = await api.get('/exportaciones/servicios', { params, responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `servicios_${hoyStr()}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      showError(err, 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

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
    const precio = aNumero(form.precio_base)
    if (!Number.isFinite(precio) || precio < 0) {
      setError('Precio debe ser un número mayor o igual a 0')
      return
    }
    const tiempo = aEntero(form.tiempo_estimado_minutos, 60)
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
        id_categoria: aEntero(form.id_categoria),
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
      invalidate(['servicios'])
      setModalAbierto(false)
      setEditando(null)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al guardar')
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
      invalidate(['servicios'])
      setModalEliminar(false)
      setServicioAEliminar(null)
    } catch (err) {
      showError(err, 'Error al desactivar')
    } finally {
      setEnviandoEliminar(false)
    }
  }

  const activarServicio = async (s) => {
    try {
      await api.post(`/servicios/${s.id}/activar`)
      invalidate(['servicios'])
    } catch (err) {
      showError(err, 'Error al reactivar')
    }
  }

  const nombreCategoria = (s) => s?.categoria_nombre ?? '-'

  if (loading && servicios.length === 0) return <div className="py-6"><p className="text-slate-500">Cargando...</p></div>

  return (
    <div className="min-h-0">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Servicios</h1>
        <div className="flex flex-wrap gap-2">
          {esAdmin && (
            <button type="button" onClick={abrirNuevo} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium touch-manipulation">
              Nuevo servicio
            </button>
          )}
          <button type="button" onClick={exportarExcel} disabled={exportando} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 font-medium disabled:opacity-50 text-sm touch-manipulation">
            📥 {exportando ? 'Exportando...' : 'Exportar'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[140px]">
            <label className="block text-xs text-slate-500 mb-1">Buscar</label>
            <input
              type="text"
              placeholder="Código o nombre..."
              value={buscar}
              onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
              className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation"
            />
          </div>
          <div className="min-w-[140px] flex-1 sm:flex-initial">
            <label className="block text-xs text-slate-500 mb-1">Categoría</label>
            <select
              value={filtroCategoria}
              onChange={(e) => { setFiltroCategoria(e.target.value); setPagina(1) }}
              className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation"
            >
              <option value="">Todas</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          </div>
          {esAdmin && (
            <Link to="/configuracion?tab=categorias-servicios" className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 active:bg-slate-100 text-sm whitespace-nowrap inline-flex items-center justify-center touch-manipulation" title="Administrar categorías">
              ⚙️ Categorías
            </Link>
          )}
          <div className="min-w-[120px]">
            <label className="block text-xs text-slate-500 mb-1">Estado</label>
            <select
              value={filtroActivo}
              onChange={(e) => { setFiltroActivo(e.target.value); setPagina(1) }}
              className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation"
            >
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <div className="overflow-x-auto min-w-0">
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
                      <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex gap-1 justify-end">
                          {s.activo !== false ? (
                            <>
                              <button type="button" onClick={() => abrirEditar(s)} className="min-h-[40px] min-w-[40px] flex items-center justify-center text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation" title="Editar">✏️</button>
                              <button type="button" onClick={() => abrirModalEliminar(s)} className="min-h-[40px] min-w-[40px] flex items-center justify-center text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>
                            </>
                          ) : (
                            <button type="button" onClick={() => activarServicio(s)} className="min-h-[40px] px-2 py-1.5 text-sm text-green-600 hover:text-green-700 active:bg-green-50 rounded touch-manipulation" title="Reactivar">✓ Reactivar</button>
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
        <div className="mt-4 flex flex-col sm:flex-row justify-center sm:justify-end gap-3 items-stretch sm:items-center flex-wrap p-3 bg-slate-50 rounded-lg border border-slate-200">
          <button
            type="button"
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={pagina <= 1}
            className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          >
            ← Anterior
          </button>
          <span className="min-h-[44px] px-4 py-2 flex items-center justify-center text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-200">
            Pág. {pagina} de {totalPaginas} ({total})
          </span>
          <button
            type="button"
            onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
            disabled={pagina >= totalPaginas}
            className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
          >
            Siguiente →
          </button>
        </div>
      )}

      {mostrarSubir && (
        <button
          type="button"
          onClick={scrollArriba}
          className="fixed bottom-6 right-6 z-40 min-w-[48px] min-h-[48px] rounded-full bg-primary-600 text-white shadow-lg hover:bg-primary-700 active:bg-primary-800 flex items-center justify-center text-xl transition-all hover:scale-110 touch-manipulation"
          title="Volver al principio"
          aria-label="Volver al principio"
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
                className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
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
                className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
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
              className="w-full px-4 py-3 min-h-[72px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 placeholder-slate-400 touch-manipulation"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Categoría *</label>
              <select
                value={form.id_categoria}
                onChange={(e) => setForm({ ...form, id_categoria: e.target.value })}
                className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
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
                className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Tiempo (min) *</label>
              <input
                type="number"
                min={1}
                value={form.tiempo_estimado_minutos}
                onChange={(e) => setForm({ ...form, tiempo_estimado_minutos: aEntero(e.target.value, 60) })}
                className="w-full px-4 py-3 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation"
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

          <div className="flex flex-wrap justify-end gap-2 pt-1 border-t border-slate-200">
            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 font-medium touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviando} className="min-h-[44px] px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 font-medium touch-manipulation">{enviando ? 'Guardando...' : (editando ? 'Guardar cambios' : 'Crear')}</button>
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
              <div className="flex flex-wrap justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminar(false); setServicioAEliminar(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
                <button type="button" onClick={confirmarEliminar} disabled={enviandoEliminar} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">{enviandoEliminar ? 'Desactivando...' : 'Desactivar'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  )
}
