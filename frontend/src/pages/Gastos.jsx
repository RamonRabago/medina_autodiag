import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'

const CATEGORIAS = [
  { valor: 'RENTA', label: 'Renta' },
  { valor: 'SERVICIOS', label: 'Servicios (luz, agua, etc.)' },
  { valor: 'MATERIAL', label: 'Material de oficina' },
  { valor: 'NOMINA', label: 'Nómina' },
  { valor: 'OTROS', label: 'Otros' },
]

export default function Gastos() {
  const [gastos, setGastos] = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [limit] = useState(20)
  const [filtros, setFiltros] = useState({ fecha_desde: '', fecha_hasta: '', categoria: '', buscar: '' })
  const [modalAbierto, setModalAbierto] = useState(false)
  const [modalEditar, setModalEditar] = useState(false)
  const [gastoEditando, setGastoEditando] = useState(null)
  const [form, setForm] = useState({ fecha: new Date().toISOString().slice(0, 10), concepto: '', monto: '', categoria: 'OTROS', observaciones: '' })
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  const cargar = () => {
    setLoading(true)
    const params = { skip: (pagina - 1) * limit, limit }
    if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
    if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
    if (filtros.categoria) params.categoria = filtros.categoria
    if (filtros.buscar?.trim()) params.buscar = filtros.buscar.trim()
    api.get('/gastos/', { params }).then((res) => {
      const d = res.data
      setGastos(d?.gastos ?? [])
      setTotal(d?.total ?? 0)
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => setGastos([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, filtros])

  const abrirNuevo = () => {
    setForm({
      fecha: new Date().toISOString().slice(0, 10),
      concepto: '',
      monto: '',
      categoria: 'OTROS',
      observaciones: '',
    })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (g) => {
    setGastoEditando(g)
    setForm({
      fecha: (g.fecha || '').toString().slice(0, 10),
      concepto: g.concepto || '',
      monto: String(g.monto ?? ''),
      categoria: g.categoria || 'OTROS',
      observaciones: g.observaciones || '',
    })
    setError('')
    setModalEditar(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await api.post('/gastos/', {
        fecha: form.fecha,
        concepto: form.concepto.trim(),
        monto: parseFloat(form.monto) || 0,
        categoria: form.categoria,
        observaciones: form.observaciones?.trim() || null,
      })
      cargar()
      setModalAbierto(false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const handleEditar = async (e) => {
    e.preventDefault()
    if (!gastoEditando) return
    setError('')
    setEnviando(true)
    try {
      await api.patch(`/gastos/${gastoEditando.id_gasto}`, {
        fecha: form.fecha,
        concepto: form.concepto.trim(),
        monto: parseFloat(form.monto) || 0,
        categoria: form.categoria,
        observaciones: form.observaciones?.trim() || null,
      })
      cargar()
      setModalEditar(false)
      setGastoEditando(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al actualizar')
    } finally {
      setEnviando(false)
    }
  }

  const eliminar = async (id) => {
    if (!window.confirm('¿Eliminar este gasto?')) return
    try {
      await api.delete(`/gastos/${id}`)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar')
    }
  }

  const catLabel = (c) => CATEGORIAS.find((x) => x.valor === c)?.label || c

  if (loading && gastos.length === 0) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Gastos operativos</h1>

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="date"
          value={filtros.fecha_desde}
          onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          placeholder="Desde"
        />
        <input
          type="date"
          value={filtros.fecha_hasta}
          onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          placeholder="Hasta"
        />
        <select
          value={filtros.categoria}
          onChange={(e) => setFiltros({ ...filtros, categoria: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Todas las categorías</option>
          {CATEGORIAS.map((c) => (
            <option key={c.valor} value={c.valor}>{c.label}</option>
          ))}
        </select>
        <input
          type="text"
          value={filtros.buscar}
          onChange={(e) => setFiltros({ ...filtros, buscar: e.target.value })}
          placeholder="Buscar concepto..."
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm w-48"
        />
        <button
          onClick={abrirNuevo}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          + Nuevo gasto
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Concepto</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Categoría</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Monto</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {gastos.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">No hay gastos registrados</td>
              </tr>
            ) : (
              gastos.map((g) => (
                <tr key={g.id_gasto} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-700">{(g.fecha || '').toString().slice(0, 10)}</td>
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{g.concepto}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{catLabel(g.categoria)}</td>
                  <td className="px-4 py-3 text-sm text-right font-medium text-red-600">
                    ${(Number(g.monto) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => abrirEditar(g)} className="text-slate-600 hover:text-slate-800 mr-2" title="Editar">✏️</button>
                    <button onClick={() => eliminar(g.id_gasto)} className="text-red-600 hover:text-red-700" title="Eliminar">🗑️</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {totalPaginas > 1 && (
          <div className="px-4 py-3 border-t border-slate-200 flex justify-between items-center">
            <span className="text-sm text-slate-600">Total: {total} gastos</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina <= 1}
                className="px-3 py-1 border rounded-lg text-sm disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="py-1 text-sm text-slate-600">Pág. {pagina} / {totalPaginas}</span>
              <button
                onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
                disabled={pagina >= totalPaginas}
                className="px-3 py-1 border rounded-lg text-sm disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      <Modal titulo="Nuevo gasto" abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha</label>
            <input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} required className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Concepto *</label>
            <input type="text" value={form.concepto} onChange={(e) => setForm({ ...form, concepto: e.target.value })} required placeholder="Ej: Renta local, Luz, etc." className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step={0.01} min={0.01} value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required className="w-full px-4 py-2 border rounded-lg" placeholder="0.00" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Categoría</label>
            <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} className="w-full px-4 py-2 border rounded-lg">
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} className="w-full px-4 py-2 border rounded-lg" placeholder="Opcional" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border rounded-lg">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg disabled:opacity-50">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Editar gasto" abierto={modalEditar} onCerrar={() => { setModalEditar(false); setGastoEditando(null) }}>
        <form onSubmit={handleEditar} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha</label>
            <input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} required className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Concepto *</label>
            <input type="text" value={form.concepto} onChange={(e) => setForm({ ...form, concepto: e.target.value })} required className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step={0.01} min={0.01} value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Categoría</label>
            <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} className="w-full px-4 py-2 border rounded-lg">
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => { setModalEditar(false); setGastoEditando(null) }} className="px-4 py-2 border rounded-lg">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg disabled:opacity-50">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
