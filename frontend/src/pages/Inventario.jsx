import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
export default function Inventario() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [repuestos, setRepuestos] = useState([])
  const [loading, setLoading] = useState(true)
  const [buscar, setBuscar] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroStockBajo, setFiltroStockBajo] = useState(false)
  const [filtroActivo, setFiltroActivo] = useState('')
  const [incluirEliminados, setIncluirEliminados] = useState(false)
  const [pagina, setPagina] = useState(1)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [total, setTotal] = useState(0)
  const limit = 20
  const esAdmin = user?.rol === 'ADMIN'
  const esCaja = user?.rol === 'CAJA'
  const puedeEditar = esAdmin || esCaja

  const [categorias, setCategorias] = useState([])
  const [modalEliminar, setModalEliminar] = useState(false)
  const [repuestoAEliminar, setRepuestoAEliminar] = useState(null)
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [modalEliminarPermanente, setModalEliminarPermanente] = useState(false)
  const [repuestoAEliminarPermanente, setRepuestoAEliminarPermanente] = useState(null)
  const [motivoEliminar, setMotivoEliminar] = useState('')
  const [enviandoEliminarPermanente, setEnviandoEliminarPermanente] = useState(false)
  const [imagenAmpliada, setImagenAmpliada] = useState(null)
  const [exportando, setExportando] = useState(false)

  const cargar = () => {
    setLoading(true)
    const params = { skip: (pagina - 1) * limit, limit }
    if (buscar.trim()) params.buscar = buscar.trim()
    if (filtroCategoria) params.id_categoria = parseInt(filtroCategoria)
    if (filtroStockBajo) params.stock_bajo = true
    if (filtroActivo === 'true') params.activo = true
    if (filtroActivo === 'false') params.activo = false
    if (esAdmin && incluirEliminados) params.incluir_eliminados = true
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

  useEffect(() => { cargar() }, [pagina, buscar, filtroCategoria, filtroStockBajo, filtroActivo, incluirEliminados])

  useEffect(() => {
    api.get('/categorias-repuestos/').then((r) => setCategorias(Array.isArray(r.data) ? r.data : [])).catch(() => setCategorias([]))
  }, [])

  const abrirModalEliminar = (r) => {
    setRepuestoAEliminar(r)
    setModalEliminar(true)
  }

  const abrirModalEliminarPermanente = (r) => {
    setRepuestoAEliminarPermanente(r)
    setMotivoEliminar('')
    setModalEliminarPermanente(true)
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

  const confirmarEliminarPermanente = async () => {
    if (!repuestoAEliminarPermanente) return
    const motivo = motivoEliminar.trim()
    if (motivo.length < 10) {
      alert('El motivo debe tener al menos 10 caracteres para la auditoría.')
      return
    }
    setEnviandoEliminarPermanente(true)
    try {
      await api.delete(`/repuestos/${repuestoAEliminarPermanente.id_repuesto}/eliminar-permanentemente`, {
        data: { motivo },
      })
      cargar()
      setModalEliminarPermanente(false)
      setRepuestoAEliminarPermanente(null)
      setMotivoEliminar('')
    } catch (err) {
      const d = err.response?.data?.detail
      alert(typeof d === 'string' ? d : 'Error al eliminar permanentemente')
    } finally {
      setEnviandoEliminarPermanente(false)
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

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const params = { limit: 10000 }
      if (buscar.trim()) params.buscar = buscar.trim()
      if (filtroCategoria) params.id_categoria = parseInt(filtroCategoria)
      if (filtroStockBajo) params.stock_bajo = true
      if (filtroActivo === 'true') params.activo = true
      if (filtroActivo === 'false') params.activo = false
      if (esAdmin && incluirEliminados) params.incluir_eliminados = true
      const res = await api.get('/exportaciones/inventario', { params, responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `inventario_${new Date().toISOString().slice(0, 10)}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    } finally {
      setExportando(false)
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
              <Link to="/configuracion?tab=ubicaciones" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar ubicaciones (legacy)">
                📍 Ubicaciones
              </Link>
              <Link to="/configuracion?tab=estantes" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar estantes">
                🗄️ Estantes
              </Link>
              <Link to="/configuracion?tab=niveles" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar niveles">
                📊 Niveles
              </Link>
              <Link to="/configuracion?tab=filas" className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm whitespace-nowrap" title="Administrar filas">
                📋 Filas
              </Link>
            </>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={filtroStockBajo} onChange={(e) => { setFiltroStockBajo(e.target.checked); setPagina(1) }} />
            Stock bajo
          </label>
          {esAdmin && (
            <label className="flex items-center gap-2 text-sm" title="Ver productos marcados como eliminados (solo consulta)">
              <input type="checkbox" checked={incluirEliminados} onChange={(e) => { setIncluirEliminados(e.target.checked); setPagina(1) }} />
              Ver eliminados
            </label>
          )}
          <select value={filtroActivo} onChange={(e) => { setFiltroActivo(e.target.value); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
          <button onClick={exportarExcel} disabled={exportando} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 text-sm">
            📥 {exportando ? 'Exportando...' : 'Exportar a Excel'}
          </button>
          {puedeEditar && (
            <Link to="/inventario/nuevo" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
              + Nuevo repuesto
            </Link>
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
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Bodega</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Ubicación</th>
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
                  <td colSpan={puedeEditar ? 11 : 10} className="px-4 py-8 text-center text-slate-500">
                    No hay repuestos
                  </td>
                </tr>
              ) : (
                repuestos.map((r) => (
                  <tr key={r.id_repuesto} className={r.eliminado ? 'bg-slate-100' : r.activo === false ? 'bg-slate-50' : 'hover:bg-slate-50'}>
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
                    <td className="px-4 py-3 text-sm text-slate-600">{r.bodega_nombre || '-'}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{r.ubicacion_nombre || r.ubicacion || '-'}</td>
                    <td className="px-4 py-3 text-sm text-right">
                      <span className={stockCritico(r) ? 'text-red-600 font-semibold' : stockBajo(r) ? 'text-amber-600 font-medium' : ''}>
                        {r.stock_actual ?? 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-slate-600">{r.stock_minimo ?? 0}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">${(Number(r.precio_venta) || 0).toFixed(2)}</td>
                    <td className="px-4 py-3 text-center">
                      {r.eliminado ? (
                        <span className="px-2 py-0.5 rounded text-xs bg-slate-300 text-slate-700" title={r.motivo_eliminacion || 'Producto eliminado (solo consulta para historial)'}>Eliminado</span>
                      ) : r.activo === false ? (
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
                          {r.eliminado ? (
                            <span className="text-xs text-slate-500 italic">Solo consulta</span>
                          ) : r.activo !== false ? (
                            <>
                              <Link to={`/inventario/entrada/${r.id_repuesto}`} className="text-sm text-green-600 hover:text-green-700" title="Agregar stock">➕</Link>
                              <button type="button" onClick={() => navigate(`/inventario/editar/${r.id_repuesto}`)} className="text-sm text-slate-600 hover:text-slate-800" title="Editar">✏️</button>
                              <button onClick={() => abrirModalEliminar(r)} className="text-sm text-red-600 hover:text-red-700" title="Desactivar">🗑️</button>
                              {esAdmin && (
                                <button onClick={() => abrirModalEliminarPermanente(r)} className="text-sm text-red-800 hover:text-red-900" title="Eliminar permanentemente">⛔</button>
                              )}
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

      <Modal titulo="Eliminar permanentemente" abierto={modalEliminarPermanente} onCerrar={() => { setModalEliminarPermanente(false); setRepuestoAEliminarPermanente(null); setMotivoEliminar('') }}>
        <div className="space-y-4">
          {repuestoAEliminarPermanente && (
            <>
              <p className="text-slate-600">
                ¿Eliminar permanentemente <strong>{repuestoAEliminarPermanente.nombre}</strong> ({repuestoAEliminarPermanente.codigo})? Esta acción no se puede deshacer. Los datos quedarán registrados para auditoría.
              </p>
              <p className="text-amber-700 text-sm font-medium">No se puede eliminar si tiene ventas, órdenes de trabajo, movimientos u órdenes de compra asociados.</p>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Motivo (mín. 10 caracteres) *</label>
                <textarea
                  value={motivoEliminar}
                  onChange={(e) => setMotivoEliminar(e.target.value)}
                  rows={3}
                  placeholder="Ej: Producto discontinuado, error de carga, duplicado..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 text-sm"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminarPermanente(false); setRepuestoAEliminarPermanente(null); setMotivoEliminar('') }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">Cancelar</button>
                <button type="button" onClick={confirmarEliminarPermanente} disabled={enviandoEliminarPermanente || motivoEliminar.trim().length < 10} className="px-4 py-2 bg-red-700 text-white rounded-lg hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed">{enviandoEliminarPermanente ? 'Eliminando...' : 'Eliminar permanentemente'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>

    </div>
  )
}
