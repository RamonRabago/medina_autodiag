import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Configuracion() {
  const { user } = useAuth()
  const [tab, setTab] = useState('categorias-servicios')
  const [categorias, setCategorias] = useState([])
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

  const cargar = () => {
    setLoading(true)
    api.get('/categorias-servicios/', { params: { limit: 500 } })
      .then((r) => setCategorias(Array.isArray(r.data) ? r.data : []))
      .catch(() => setCategorias([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [])

  const abrirNuevo = () => {
    setEditando(null)
    setForm({ nombre: '', descripcion: '', activo: true })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (c) => {
    setEditando(c)
    setForm({
      nombre: c.nombre || '',
      descripcion: c.descripcion || '',
      activo: c.activo !== false,
    })
    setError('')
    setModalAbierto(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.nombre.trim()) {
      setError('El nombre es obligatorio')
      return
    }
    setEnviando(true)
    try {
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
      await api.delete(`/categorias-servicios/${categoriaAEliminar.id}`)
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
          onClick={() => setTab('categorias-servicios')}
          className={`px-4 py-2 font-medium rounded-t-lg ${tab === 'categorias-servicios' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:text-slate-800'}`}
        >
          Categorías de servicios
        </button>
      </div>

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
                  {categorias.length === 0 ? (
                    <tr>
                      <td colSpan={esAdmin ? 5 : 4} className="px-4 py-8 text-center text-slate-500">
                        No hay categorías. Crea una para asignarla a los servicios.
                      </td>
                    </tr>
                  ) : (
                    categorias.map((c) => (
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

      <Modal titulo={editando ? 'Editar categoría' : 'Nueva categoría'} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
            <input
              type="text"
              value={form.nombre}
              onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              placeholder="Ej: Mantenimiento"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Descripción (opcional)</label>
            <textarea
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              rows={2}
              placeholder="Descripción breve"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.activo}
              onChange={(e) => setForm({ ...form, activo: e.target.checked })}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">Activa</span>
          </label>
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

      <Modal titulo="Eliminar categoría" abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setCategoriaAEliminar(null) }}>
        <div className="space-y-4">
          {categoriaAEliminar && (
            <>
              <p className="text-slate-600">
                ¿Eliminar la categoría <strong>{categoriaAEliminar.nombre}</strong>? No podrás eliminarla si tiene servicios asignados. Asigna otra categoría a esos servicios primero.
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
