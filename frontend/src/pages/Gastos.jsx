import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { fechaAStr, hoyStr, formatearFechaHora } from '../utils/fechas'
import { aNumero, esNumeroValido } from '../utils/numeros'

function getRangoMesActual() {
  const hoy = new Date()
  const año = hoy.getFullYear()
  const mes = hoy.getMonth()
  const desde = `${año}-${String(mes + 1).padStart(2, '0')}-01`
  const hasta = fechaAStr(hoy)
  return { desde, hasta }
}

const CATEGORIAS = [
  { valor: 'RENTA', label: 'Renta' },
  { valor: 'SERVICIOS', label: 'Servicios (luz, agua, etc.)' },
  { valor: 'MATERIAL', label: 'Material de oficina' },
  { valor: 'NOMINA', label: 'Nómina' },
  { valor: 'DEVOLUCION_VENTA', label: 'Devolución venta (salida de efectivo)' },
  { valor: 'OTROS', label: 'Otros' },
]

export default function Gastos() {
  const rango = getRangoMesActual()
  const [gastos, setGastos] = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [totalMonto, setTotalMonto] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [limit] = useState(20)
  const [filtros, setFiltros] = useState({ fecha_desde: rango.desde, fecha_hasta: rango.hasta, categoria: '', buscar: '' })
  const [ordenPor, setOrdenPor] = useState('fecha')
  const [ordenDir, setOrdenDir] = useState('desc')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [modalEditar, setModalEditar] = useState(false)
  const [modalDetalle, setModalDetalle] = useState(false)
  const [gastoEditando, setGastoEditando] = useState(null)
  const [gastoViendo, setGastoViendo] = useState(null)
  const [form, setForm] = useState({ fecha: hoyStr(), concepto: '', monto: '', categoria: 'OTROS', observaciones: '' })
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [exportando, setExportando] = useState(false)

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = {}
      if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
      if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
      if (filtros.categoria) params.categoria = filtros.categoria
      if (filtros.buscar?.trim()) params.buscar = filtros.buscar.trim()
      const res = await api.get('/exportaciones/gastos', { params, responseType: 'blob' })
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `gastos_${hoyStr()}.xlsx`
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fn)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  const toggleOrden = (col) => {
    if (ordenPor === col) {
      setOrdenDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setOrdenPor(col)
      setOrdenDir('desc')
    }
  }
  const ThSort = ({ col, label, right }) => (
    <th
      className={`px-2 sm:px-4 py-3 text-xs font-medium text-slate-500 uppercase cursor-pointer hover:bg-slate-100 active:bg-slate-200 select-none min-h-[44px] touch-manipulation ${right ? 'text-right' : 'text-left'}`}
      onClick={() => toggleOrden(col)}
    >
      <span className={`flex items-center gap-1 ${right ? 'justify-end' : ''}`}>
        {label}
        {ordenPor === col && <span>{ordenDir === 'asc' ? '▲' : '▼'}</span>}
      </span>
    </th>
  )

  const cargar = () => {
    setLoading(true)
    const params = { skip: (pagina - 1) * limit, limit, orden_por: ordenPor, direccion: ordenDir }
    if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
    if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
    if (filtros.categoria) params.categoria = filtros.categoria
    if (filtros.buscar?.trim()) params.buscar = filtros.buscar.trim()
    api.get('/gastos/', { params }).then((res) => {
      const d = res.data
      setGastos(d?.gastos ?? [])
      setTotal(d?.total ?? 0)
      setTotalMonto(d?.total_monto ?? 0)
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => { setGastos([]); setTotalMonto(0) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, filtros, ordenPor, ordenDir])

  const abrirNuevo = () => {
    setForm({
      fecha: hoyStr(),
      concepto: '',
      monto: '',
      categoria: 'OTROS',
      observaciones: '',
    })
    setError('')
    setModalAbierto(true)
  }

  const abrirDetalle = (g) => {
    setGastoViendo(g)
    setModalDetalle(true)
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
    if (!esNumeroValido(form.monto) || aNumero(form.monto) <= 0) {
      setError('Monto debe ser un número mayor a 0')
      return
    }
    setEnviando(true)
    try {
      await api.post('/gastos/', {
        fecha: form.fecha,
        concepto: form.concepto.trim(),
        monto: aNumero(form.monto),
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
    if (!esNumeroValido(form.monto) || aNumero(form.monto) <= 0) {
      setError('Monto debe ser un número mayor a 0')
      return
    }
    setEnviando(true)
    try {
      await api.patch(`/gastos/${gastoEditando.id_gasto}`, {
        fecha: form.fecha,
        concepto: form.concepto.trim(),
        monto: aNumero(form.monto),
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
    <div className="min-h-0 flex flex-col">
      <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Gastos operativos</h1>
        <button type="button" onClick={abrirNuevo} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation">
          + Nuevo gasto
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4 border border-slate-200">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Desde</label>
            <input type="date" value={filtros.fecha_desde} onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Hasta</label>
            <input type="date" value={filtros.fecha_hasta} onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Categoría</label>
            <select value={filtros.categoria} onChange={(e) => setFiltros({ ...filtros, categoria: e.target.value })} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation min-w-[140px]">
              <option value="">Todas</option>
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>{c.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-0">
            <label className="block text-xs text-slate-500 mb-1">Buscar</label>
            <input type="text" value={filtros.buscar} onChange={(e) => setFiltros({ ...filtros, buscar: e.target.value })} placeholder="Concepto..." className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
          </div>
          <button type="button" onClick={exportarExcel} disabled={exportando} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 disabled:opacity-50 touch-manipulation">
            📥 {exportando ? 'Exportando...' : 'Exportar'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 flex-1 min-h-0">
        {total > 0 && (
          <p className="px-4 py-3 text-sm text-slate-600 bg-slate-50 border-b border-slate-200">
            Total: <strong>{total}</strong> gasto{total !== 1 ? 's' : ''} · Monto: <strong className="text-red-600">${(totalMonto || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</strong>
          </p>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <ThSort col="fecha" label="Fecha" />
                <ThSort col="concepto" label="Concepto" />
                <ThSort col="categoria" label="Categoría" />
                <ThSort col="monto" label="Monto" right />
                <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
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
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-700">{(g.fecha || '').toString().slice(0, 10)}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{g.concepto}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{catLabel(g.categoria)}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-right font-medium text-red-600">${(Number(g.monto) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                    <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                      <button type="button" onClick={() => abrirDetalle(g)} className="min-h-[36px] min-w-[36px] inline-flex items-center justify-center text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation mr-1" title="Ver detalles">👁️</button>
                      <button type="button" onClick={() => abrirEditar(g)} className="min-h-[36px] min-w-[36px] inline-flex items-center justify-center text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation mr-1" title="Editar">✏️</button>
                      <button type="button" onClick={() => eliminar(g.id_gasto)} className="min-h-[36px] min-w-[36px] inline-flex items-center justify-center text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Eliminar">🗑️</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {totalPaginas > 1 && (
          <div className="px-4 py-3 border-t border-slate-200 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 bg-slate-50">
            <span className="text-sm text-slate-600 order-2 sm:order-1 flex items-center">{total} gasto{total !== 1 ? 's' : ''} · ${(totalMonto || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
            <div className="flex gap-2 order-1 sm:order-2">
              <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 touch-manipulation">Anterior</button>
              <span className="min-h-[44px] px-4 py-2 flex items-center justify-center text-sm text-slate-700 bg-white rounded-lg border border-slate-200">Pág. {pagina} de {totalPaginas}</span>
              <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 touch-manipulation">Siguiente</button>
            </div>
          </div>
        )}
      </div>

      <Modal titulo="Detalle del gasto" abierto={modalDetalle} onCerrar={() => { setModalDetalle(false); setGastoViendo(null) }}>
        {gastoViendo && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Fecha</label>
                <p className="text-slate-800 font-medium">{(gastoViendo.fecha || '').toString().slice(0, 10)}</p>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Categoría</label>
                <p className="text-slate-800 font-medium">{catLabel(gastoViendo.categoria)}</p>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs text-slate-500 mb-1">Concepto</label>
                <p className="text-slate-800 font-medium">{gastoViendo.concepto}</p>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Monto</label>
                <p className="text-slate-800 font-bold text-red-600">${(Number(gastoViendo.monto) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
              </div>
              {gastoViendo.creado_en && (
                <div>
                  <label className="block text-xs text-slate-500 mb-1">Registrado</label>
                  <p className="text-slate-600 text-sm">{formatearFechaHora(gastoViendo.creado_en)}</p>
                </div>
              )}
              {(gastoViendo.observaciones || '').trim() && (
                <div className="sm:col-span-2">
                  <label className="block text-xs text-slate-500 mb-1">Observaciones</label>
                  <p className="text-slate-700 text-sm whitespace-pre-wrap">{gastoViendo.observaciones}</p>
                </div>
              )}
            </div>
            <div className="flex flex-wrap justify-end gap-2 pt-2 border-t border-slate-200">
              <button type="button" onClick={() => { setModalDetalle(false); setGastoViendo(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cerrar</button>
              <button type="button" onClick={() => { setModalDetalle(false); abrirEditar(gastoViendo) }} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 touch-manipulation">Editar</button>
            </div>
          </div>
        )}
      </Modal>

      <Modal titulo="Nuevo gasto" abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha</label>
            <input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} required className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Concepto *</label>
            <input type="text" value={form.concepto} onChange={(e) => setForm({ ...form, concepto: e.target.value })} required placeholder={form.categoria === 'DEVOLUCION_VENTA' ? 'Ej: Devolución venta #123' : 'Ej: Renta local, Luz, etc.'} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step={0.01} min={0.01} value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required placeholder="0.00" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Categoría</label>
            <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation">
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border rounded-lg touch-manipulation" placeholder="Opcional" />
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Editar gasto" abierto={modalEditar} onCerrar={() => { setModalEditar(false); setGastoEditando(null) }}>
        <form onSubmit={handleEditar} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fecha</label>
            <input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} required className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Concepto *</label>
            <input type="text" value={form.concepto} onChange={(e) => setForm({ ...form, concepto: e.target.value })} required className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step={0.01} min={0.01} value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} required className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Categoría</label>
            <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation">
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={2} className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => { setModalEditar(false); setGastoEditando(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
