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
  const [modalKardex, setModalKardex] = useState(false)
  const [repuestoKardex, setRepuestoKardex] = useState(null)
  const [movimientosKardex, setMovimientosKardex] = useState([])
  const [cargandoKardex, setCargandoKardex] = useState(false)
  const [modalAjuste, setModalAjuste] = useState(false)
  const [repuestoAjuste, setRepuestoAjuste] = useState(null)
  const [formAjuste, setFormAjuste] = useState({ stock_nuevo: '', motivo: '', referencia: '' })
  const [enviandoAjuste, setEnviandoAjuste] = useState(false)
  const [modalAuditoria, setModalAuditoria] = useState(false)
  const [movimientosAuditoria, setMovimientosAuditoria] = useState([])
  const [cargandoAuditoria, setCargandoAuditoria] = useState(false)
  const [usuarios, setUsuarios] = useState([])
  const [filtrosAuditoria, setFiltrosAuditoria] = useState({ fecha_desde: '', fecha_hasta: '', id_usuario: '' })
  const [exportandoAuditoria, setExportandoAuditoria] = useState(false)
  const [errorAuditoria, setErrorAuditoria] = useState('')
  const [modalSugerencia, setModalSugerencia] = useState(false)
  const [gruposSugerencia, setGruposSugerencia] = useState([])
  const [cargandoSugerencia, setCargandoSugerencia] = useState(false)
  const [incluirCercanosSugerencia, setIncluirCercanosSugerencia] = useState(false)

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

  const abrirModalAjuste = (r) => {
    setRepuestoAjuste(r)
    setFormAjuste({
      stock_nuevo: String(r.stock_actual ?? 0),
      motivo: '',
      referencia: '',
    })
    setModalAjuste(true)
  }

  const confirmarAjuste = async () => {
    if (!repuestoAjuste) return
    const stockNuevo = parseInt(formAjuste.stock_nuevo, 10)
    const motivo = formAjuste.motivo.trim()
    if (isNaN(stockNuevo) || stockNuevo < 0) {
      alert('Stock debe ser un número mayor o igual a 0.')
      return
    }
    if (motivo.length < 10) {
      alert('El motivo debe tener al menos 10 caracteres.')
      return
    }
    if (stockNuevo === (repuestoAjuste.stock_actual ?? 0)) {
      alert('El nuevo stock es igual al actual. No se requiere ajuste.')
      return
    }
    setEnviandoAjuste(true)
    try {
      await api.post('/inventario/movimientos/ajuste', {
        id_repuesto: repuestoAjuste.id_repuesto,
        stock_nuevo: stockNuevo,
        motivo,
        referencia: formAjuste.referencia?.trim() || null,
      })
      setModalAjuste(false)
      setRepuestoAjuste(null)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al ajustar inventario')
    } finally {
      setEnviandoAjuste(false)
    }
  }

  const abrirModalKardex = async (r) => {
    setRepuestoKardex(r)
    setModalKardex(true)
    setCargandoKardex(true)
    setMovimientosKardex([])
    try {
      const res = await api.get(`/inventario/movimientos/repuesto/${r.id_repuesto}`, { params: { limite: 100 } })
      setMovimientosKardex(Array.isArray(res.data) ? res.data : [])
    } catch {
      setMovimientosKardex([])
    } finally {
      setCargandoKardex(false)
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

  const paramsAuditoria = () => {
    const p = { skip: 0, limit: 200 }
    if (filtrosAuditoria.fecha_desde) p.fecha_desde = filtrosAuditoria.fecha_desde
    if (filtrosAuditoria.fecha_hasta) p.fecha_hasta = filtrosAuditoria.fecha_hasta
    if (filtrosAuditoria.id_usuario) p.id_usuario = parseInt(filtrosAuditoria.id_usuario, 10)
    return p
  }

  const abrirModalAuditoria = async () => {
    setModalAuditoria(true)
    setCargandoAuditoria(true)
    setMovimientosAuditoria([])
    setErrorAuditoria('')
    try {
      const params = paramsAuditoria()
      const opts = { skipAuthRedirect: true }
      const res = await api.get('/inventario/auditoria-ajustes', {
        params: {
          fecha_desde: params.fecha_desde || undefined,
          fecha_hasta: params.fecha_hasta || undefined,
          id_usuario: params.id_usuario || undefined,
          limit: 200,
        },
        ...opts,
      }).catch((e) => {
        if (e?.response?.status === 401) setErrorAuditoria('sesion')
        return { data: { usuarios: [], movimientos: [] } }
      })
      const data = res?.data || {}
      setUsuarios(Array.isArray(data.usuarios) ? data.usuarios : [])
      setMovimientosAuditoria(Array.isArray(data.movimientos) ? data.movimientos : [])
    } finally {
      setCargandoAuditoria(false)
    }
  }

  const aplicarFiltrosAuditoria = async () => {
    setCargandoAuditoria(true)
    setErrorAuditoria('')
    try {
      const params = paramsAuditoria()
      const opts = { skipAuthRedirect: true }
      const res = await api.get('/inventario/auditoria-ajustes', {
        params: {
          fecha_desde: params.fecha_desde || undefined,
          fecha_hasta: params.fecha_hasta || undefined,
          id_usuario: params.id_usuario || undefined,
          limit: 200,
        },
        ...opts,
      }).catch((e) => {
        if (e?.response?.status === 401) setErrorAuditoria('sesion')
        return { data: { movimientos: [] } }
      })
      const data = res?.data || {}
      setMovimientosAuditoria(Array.isArray(data.movimientos) ? data.movimientos : [])
    } finally {
      setCargandoAuditoria(false)
    }
  }

  const exportarAuditoriaExcel = async () => {
    setExportandoAuditoria(true)
    try {
      const params = {}
      if (filtrosAuditoria.fecha_desde) params.fecha_desde = filtrosAuditoria.fecha_desde
      if (filtrosAuditoria.fecha_hasta) params.fecha_hasta = filtrosAuditoria.fecha_hasta
      if (filtrosAuditoria.id_usuario) params.id_usuario = parseInt(filtrosAuditoria.id_usuario, 10)
      const res = await api.get('/exportaciones/ajustes-inventario', { params, responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `ajustes_inventario_${new Date().toISOString().slice(0, 10)}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    } finally {
      setExportandoAuditoria(false)
    }
  }

  const abrirModalSugerencia = async () => {
    setModalSugerencia(true)
    setCargandoSugerencia(true)
    setGruposSugerencia([])
    try {
      const res = await api.get('/inventario/sugerencia-compra', {
        params: { incluir_cercanos: incluirCercanosSugerencia },
      })
      setGruposSugerencia(res.data?.grupos ?? [])
    } catch {
      setGruposSugerencia([])
    } finally {
      setCargandoSugerencia(false)
    }
  }

  const recargarSugerencia = () => {
    setCargandoSugerencia(true)
    api.get('/inventario/sugerencia-compra', { params: { incluir_cercanos: incluirCercanosSugerencia } })
      .then((res) => setGruposSugerencia(res.data?.grupos ?? []))
      .catch(() => setGruposSugerencia([]))
      .finally(() => setCargandoSugerencia(false))
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
            <>
              <button
                type="button"
                onClick={abrirModalSugerencia}
                className="px-3 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium"
                title="Sugerencia de compra por stock bajo"
              >
                🛒 Sugerencia de compra
              </button>
              <button
                type="button"
                onClick={abrirModalAuditoria}
                className="px-3 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-900 text-sm font-medium"
                title="Ver historial de ajustes de inventario (auditoría)"
              >
                🔍 Auditoría de ajustes
              </button>
            </>
          )}
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
                <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase w-24">Kardex</th>
                {puedeEditar && (
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {repuestos.length === 0 ? (
                <tr>
                  <td colSpan={puedeEditar ? 12 : 11} className="px-4 py-8 text-center text-slate-500">
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
                    <td className="px-4 py-3 text-center">
                      <button type="button" onClick={() => abrirModalKardex(r)} className="text-sm text-primary-600 hover:text-primary-700 font-medium" title="Ver historial de movimientos (kardex)">📋 Kardex</button>
                    </td>
                    {puedeEditar && (
                      <td className="px-4 py-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {r.eliminado ? (
                            <span className="text-xs text-slate-500 italic">Solo consulta</span>
                          ) : r.activo !== false ? (
                            <>
                              <Link to={`/inventario/entrada/${r.id_repuesto}`} className="text-sm text-green-600 hover:text-green-700" title="Agregar stock">➕</Link>
                              <button type="button" onClick={() => abrirModalAjuste(r)} className="text-sm text-amber-600 hover:text-amber-700" title="Ajustar stock (conteo físico)">⚙️</button>
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

      <Modal
        titulo="Sugerencia de compra"
        abierto={modalSugerencia}
        onCerrar={() => { setModalSugerencia(false); setGruposSugerencia([]) }}
        size="xl"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Productos con stock bajo o crítico, agrupados por proveedor. La cantidad sugerida repone hasta stock máximo.
          </p>
          <div className="flex flex-wrap gap-3 items-center p-3 bg-amber-50 rounded-lg border border-amber-200">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={incluirCercanosSugerencia}
                onChange={(e) => {
                  const nuevo = e.target.checked
                  setIncluirCercanosSugerencia(nuevo)
                  if (modalSugerencia) {
                    setCargandoSugerencia(true)
                    api.get('/inventario/sugerencia-compra', { params: { incluir_cercanos: nuevo } })
                      .then((res) => setGruposSugerencia(res.data?.grupos ?? []))
                      .catch(() => setGruposSugerencia([]))
                      .finally(() => setCargandoSugerencia(false))
                  }
                }}
              />
              Incluir cercanos al mínimo (≤120% del mínimo)
            </label>
            <button type="button" onClick={recargarSugerencia} disabled={cargandoSugerencia} className="px-3 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm disabled:opacity-50">
              {cargandoSugerencia ? 'Cargando...' : 'Actualizar'}
            </button>
            {gruposSugerencia.length > 0 && (
              <button
                type="button"
                onClick={async () => {
                  try {
                    const res = await api.get('/exportaciones/sugerencia-compra', { params: { incluir_cercanos: incluirCercanosSugerencia }, responseType: 'blob' })
                    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
                    const link = document.createElement('a')
                    link.href = window.URL.createObjectURL(blob)
                    link.download = `sugerencia_compra_${new Date().toISOString().slice(0, 10)}.xlsx`
                    link.click()
                    window.URL.revokeObjectURL(link.href)
                  } catch (err) {
                    alert(err.response?.data?.detail || 'Error al exportar')
                  }
                }}
                className="px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium ml-auto"
              >
                📥 Exportar a Excel
              </button>
            )}
          </div>
          {cargandoSugerencia ? (
            <p className="text-slate-500 py-4">Cargando sugerencias...</p>
          ) : gruposSugerencia.length === 0 ? (
            <p className="text-slate-500 py-4">No hay productos con stock bajo en este momento.</p>
          ) : (
            <div className="space-y-6 max-h-[70vh] overflow-y-auto">
              {gruposSugerencia.map((g, idx) => (
                <div key={g.id_proveedor ?? `sin-${idx}`} className="border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-100 px-4 py-2 flex justify-between items-center">
                    <span className="font-medium text-slate-800">{g.nombre || 'Sin proveedor'}</span>
                    <span className="text-sm font-semibold text-amber-700">Total: ${(g.total_estimado ?? 0).toFixed(2)}</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 text-sm">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs text-slate-500">Código</th>
                          <th className="px-3 py-2 text-left text-xs text-slate-500">Nombre</th>
                          <th className="px-3 py-2 text-right text-xs text-slate-500">Stock</th>
                          <th className="px-3 py-2 text-right text-xs text-slate-500">Mín.</th>
                          <th className="px-3 py-2 text-right text-xs text-slate-500">Sugerido</th>
                          <th className="px-3 py-2 text-right text-xs text-slate-500">P. compra</th>
                          <th className="px-3 py-2 text-right text-xs text-slate-500">Costo est.</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {(g.items ?? []).map((item) => (
                          <tr key={item.id_repuesto} className="hover:bg-slate-50">
                            <td className="px-3 py-1.5 font-medium">{item.codigo}</td>
                            <td className="px-3 py-1.5">{item.nombre}</td>
                            <td className="px-3 py-1.5 text-right">{item.stock_actual}</td>
                            <td className="px-3 py-1.5 text-right">{item.stock_minimo}</td>
                            <td className="px-3 py-1.5 text-right font-medium text-amber-700">{item.cantidad_sugerida}</td>
                            <td className="px-3 py-1.5 text-right">${(item.precio_compra ?? 0).toFixed(2)}</td>
                            <td className="px-3 py-1.5 text-right font-medium">${(item.costo_estimado ?? 0).toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>

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

      <Modal
        titulo="Auditoría de ajustes de inventario"
        abierto={modalAuditoria}
        onCerrar={() => { setModalAuditoria(false); setMovimientosAuditoria([]); setFiltrosAuditoria({ fecha_desde: '', fecha_hasta: '', id_usuario: '' }); setErrorAuditoria('') }}
        size="xl"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Listado de los últimos ajustes de inventario registrados mediante conteo físico. Usa esta vista para auditoría y revisiones.
          </p>
          {errorAuditoria === 'sesion' && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm flex flex-col gap-2">
              <span>Tu sesión ha expirado o el token no es válido.</span>
              <button
                type="button"
                onClick={() => { window.location.href = '/login' }}
                className="self-start px-3 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium"
              >
                Ir a iniciar sesión
              </button>
            </div>
          )}
          <div className="flex flex-wrap gap-3 items-end p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Desde</label>
              <input
                type="date"
                value={filtrosAuditoria.fecha_desde}
                onChange={(e) => setFiltrosAuditoria((f) => ({ ...f, fecha_desde: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Hasta</label>
              <input
                type="date"
                value={filtrosAuditoria.fecha_hasta}
                onChange={(e) => setFiltrosAuditoria((f) => ({ ...f, fecha_hasta: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Usuario</label>
              <select
                value={filtrosAuditoria.id_usuario}
                onChange={(e) => setFiltrosAuditoria((f) => ({ ...f, id_usuario: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[160px]"
              >
                <option value="">Todos</option>
                {usuarios.map((u) => (
                  <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={aplicarFiltrosAuditoria}
              disabled={cargandoAuditoria}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
            >
              {cargandoAuditoria ? 'Buscando...' : 'Buscar'}
            </button>
            <button
              type="button"
              onClick={exportarAuditoriaExcel}
              disabled={exportandoAuditoria}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium disabled:opacity-50 ml-auto"
            >
              📥 {exportandoAuditoria ? 'Exportando...' : 'Exportar a Excel'}
            </button>
          </div>
          {cargandoAuditoria ? (
            <p className="text-slate-500 py-4">Cargando ajustes...</p>
          ) : movimientosAuditoria.length === 0 ? (
            <p className="text-slate-500 py-4">No hay ajustes registrados recientemente.</p>
          ) : (
            <div className="overflow-x-auto max-h-96 border border-slate-200 rounded-lg">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Fecha</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Repuesto</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Código</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Tipo</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Cant.</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Stock ant.</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Stock nuevo</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Costo total</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Usuario</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Referencia / Motivo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {movimientosAuditoria.map((m) => (
                    <tr key={m.id_movimiento} className="hover:bg-slate-50">
                      <td className="px-3 py-1.5 text-slate-600">
                        {m.fecha_movimiento ? new Date(m.fecha_movimiento).toLocaleString('es-MX') : '-'}
                      </td>
                      <td className="px-3 py-1.5 text-slate-700">
                        {m.repuesto_nombre || m.repuesto?.nombre || '-'}
                      </td>
                      <td className="px-3 py-1.5 text-slate-600">
                        {m.repuesto_codigo || m.repuesto?.codigo || '-'}
                      </td>
                      <td className="px-3 py-1.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                            m.tipo_movimiento === 'AJUSTE+'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {m.tipo_movimiento}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-right font-medium">{m.cantidad}</td>
                      <td className="px-3 py-1.5 text-right text-slate-600">{m.stock_anterior ?? '-'}</td>
                      <td className="px-3 py-1.5 text-right font-medium">{m.stock_nuevo ?? '-'}</td>
                      <td className="px-3 py-1.5 text-right">
                        ${(Number(m.costo_total) || 0).toFixed(2)}
                      </td>
                      <td className="px-3 py-1.5 text-slate-600">
                        {(m.usuario?.nombre ?? m.usuario) || '-'}
                      </td>
                      <td
                        className="px-3 py-1.5 text-slate-600 max-w-[220px] truncate"
                        title={[m.referencia, m.motivo].filter(Boolean).join(' – ')}
                      >
                        {m.referencia || m.motivo || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Modal>

      <Modal titulo={repuestoAjuste ? `Ajustar stock – ${repuestoAjuste.nombre} (${repuestoAjuste.codigo})` : 'Ajustar stock'} abierto={modalAjuste} onCerrar={() => { setModalAjuste(false); setRepuestoAjuste(null) }}>
        <div className="space-y-4">
          {repuestoAjuste && (
            <>
              <p className="text-sm text-slate-600">Stock actual: <strong>{repuestoAjuste.stock_actual ?? 0}</strong> unidades. Indica el valor correcto después del conteo físico.</p>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Stock nuevo (conteo físico) *</label>
                <input type="number" min="0" step="1" value={formAjuste.stock_nuevo} onChange={(e) => setFormAjuste((f) => ({ ...f, stock_nuevo: e.target.value }))} className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Motivo (mín. 10 caracteres) *</label>
                <textarea value={formAjuste.motivo} onChange={(e) => setFormAjuste((f) => ({ ...f, motivo: e.target.value }))} rows={3} placeholder="Ej: Conteo físico mensual, corrección por diferencia..." className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Referencia (opcional)</label>
                <input type="text" value={formAjuste.referencia} onChange={(e) => setFormAjuste((f) => ({ ...f, referencia: e.target.value }))} placeholder="Nº de acta, folio..." className="w-full px-3 py-2 border border-slate-300 rounded-lg" />
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => { setModalAjuste(false); setRepuestoAjuste(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">Cancelar</button>
                <button type="button" onClick={confirmarAjuste} disabled={enviandoAjuste || !formAjuste.motivo.trim() || formAjuste.motivo.trim().length < 10} className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50">{enviandoAjuste ? 'Ajustando...' : 'Ajustar'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>

      <Modal titulo={repuestoKardex ? `Kardex – ${repuestoKardex.nombre} (${repuestoKardex.codigo})` : 'Kardex'} abierto={modalKardex} onCerrar={() => { setModalKardex(false); setRepuestoKardex(null); setMovimientosKardex([]) }}>
        <div className="space-y-4">
          {repuestoKardex && (
            <p className="text-sm text-slate-600">Historial de movimientos. Stock actual: <strong>{repuestoKardex.stock_actual ?? 0}</strong> unidades.</p>
          )}
          {cargandoKardex ? (
            <p className="text-slate-500 py-4">Cargando movimientos...</p>
          ) : movimientosKardex.length === 0 ? (
            <p className="text-slate-500 py-4">No hay movimientos registrados.</p>
          ) : (
            <div className="overflow-x-auto max-h-80 overflow-y-auto border border-slate-200 rounded-lg">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Fecha</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Tipo</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Cant.</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Stock ant.</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Stock nuevo</th>
                    <th className="px-3 py-2 text-right text-xs text-slate-500">Costo</th>
                    <th className="px-3 py-2 text-left text-xs text-slate-500">Referencia / Motivo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {movimientosKardex.map((m) => (
                    <tr key={m.id_movimiento} className="hover:bg-slate-50">
                      <td className="px-3 py-1.5 text-slate-600">{m.fecha_movimiento ? new Date(m.fecha_movimiento).toLocaleString('es-MX') : '-'}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${m.tipo_movimiento === 'ENTRADA' || m.tipo_movimiento === 'AJUSTE+' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {m.tipo_movimiento}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-right font-medium">{m.cantidad}</td>
                      <td className="px-3 py-1.5 text-right text-slate-600">{m.stock_anterior ?? '-'}</td>
                      <td className="px-3 py-1.5 text-right font-medium">{m.stock_nuevo ?? '-'}</td>
                      <td className="px-3 py-1.5 text-right">${(Number(m.costo_total) || 0).toFixed(2)}</td>
                      <td className="px-3 py-1.5 text-slate-600 max-w-[180px] truncate" title={[m.referencia, m.motivo].filter(Boolean).join(' – ')}>
                        {m.referencia || m.motivo || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
