import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { useInvalidateQueries } from '../hooks/useApi'
import { hoyStr, formatearFechaHora } from '../utils/fechas'
import { showError } from '../utils/toast'
export default function Inventario() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const invalidate = useInvalidateQueries()
  const [repuestos, setRepuestos] = useState([])
  const [loading, setLoading] = useState(true)
  const [buscar, setBuscar] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroBodega, setFiltroBodega] = useState('')
  const [filtroUbicacion, setFiltroUbicacion] = useState('')
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
  const [bodegas, setBodegas] = useState([])
  const [ubicaciones, setUbicaciones] = useState([])
  const [modalEliminar, setModalEliminar] = useState(false)
  const [repuestoAEliminar, setRepuestoAEliminar] = useState(null)
  const [enviandoEliminar, setEnviandoEliminar] = useState(false)
  const [modalEliminarPermanente, setModalEliminarPermanente] = useState(false)
  const [repuestoAEliminarPermanente, setRepuestoAEliminarPermanente] = useState(null)
  const [motivoEliminar, setMotivoEliminar] = useState('')
  const [enviandoEliminarPermanente, setEnviandoEliminarPermanente] = useState(false)
  const [imagenAmpliada, setImagenAmpliada] = useState(null)
  const [exportando, setExportando] = useState(false)
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
  const [creandoOrdenGrupo, setCreandoOrdenGrupo] = useState(null)
  const [modalEntradaMasiva, setModalEntradaMasiva] = useState(false)
  const [archivoEntradaMasiva, setArchivoEntradaMasiva] = useState(null)
  const [proveedorEntradaMasiva, setProveedorEntradaMasiva] = useState('')
  const [referenciaEntradaMasiva, setReferenciaEntradaMasiva] = useState('')
  const [subiendoEntradaMasiva, setSubiendoEntradaMasiva] = useState(false)
  const [resultadoEntradaMasiva, setResultadoEntradaMasiva] = useState(null)
  const [proveedores, setProveedores] = useState([])

  const cargar = () => {
    setLoading(true)
    const params = { skip: (pagina - 1) * limit, limit }
    if (buscar.trim()) params.buscar = buscar.trim()
    if (filtroCategoria) params.id_categoria = parseInt(filtroCategoria)
    if (filtroBodega) params.id_bodega = parseInt(filtroBodega)
    if (filtroUbicacion) params.id_ubicacion = parseInt(filtroUbicacion)
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
      .catch((err) => { showError(err, 'Error al cargar inventario'); setRepuestos([]) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, buscar, filtroCategoria, filtroBodega, filtroUbicacion, filtroStockBajo, filtroActivo, incluirEliminados])

  useEffect(() => {
    api.get('/categorias-repuestos/').then((r) => setCategorias(Array.isArray(r.data) ? r.data : [])).catch((err) => { showError(err, 'Error al cargar categorías'); setCategorias([]) })
    api.get('/bodegas/').then((r) => setBodegas(Array.isArray(r.data) ? r.data : [])).catch((err) => { showError(err, 'Error al cargar bodegas'); setBodegas([]) })
    api.get('/ubicaciones/', { params: { activo: true } })
      .then((r) => setUbicaciones(Array.isArray(r.data) ? r.data : []))
      .catch((err) => { showError(err, 'Error al cargar ubicaciones'); setUbicaciones([]) })
    api.get('/proveedores/', { params: { limit: 200 } })
      .then((r) => setProveedores(r.data?.proveedores ?? (Array.isArray(r.data) ? r.data : [])))
      .catch((err) => { showError(err, 'Error al cargar proveedores'); setProveedores([]) })
  }, [])

  const abrirModalEntradaMasiva = () => {
    setArchivoEntradaMasiva(null)
    setResultadoEntradaMasiva(null)
    setProveedorEntradaMasiva('')
    setReferenciaEntradaMasiva('')
    setModalEntradaMasiva(true)
  }

  const descargarPlantillaEntradaMasiva = () => {
    api.get('/inventario/movimientos/entrada-masiva/plantilla', { responseType: 'blob' })
      .then((res) => {
        const url = URL.createObjectURL(new Blob([res.data]))
        const link = document.createElement('a')
        link.href = url
        link.download = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || 'plantilla_entrada_masiva.xlsx'
        link.click()
        URL.revokeObjectURL(url)
      })
      .catch(() => showError('Error al descargar plantilla'))
  }

  const submitEntradaMasiva = async () => {
    if (!archivoEntradaMasiva) {
      showError('Selecciona un archivo Excel (.xlsx) o CSV')
      return
    }
    setSubiendoEntradaMasiva(true)
    setResultadoEntradaMasiva(null)
    try {
      const fd = new FormData()
      fd.append('archivo', archivoEntradaMasiva)
      const params = {}
      if (proveedorEntradaMasiva) params.id_proveedor = parseInt(proveedorEntradaMasiva)
      if (referenciaEntradaMasiva.trim()) params.referencia_global = referenciaEntradaMasiva.trim()
      const res = await api.post('/inventario/movimientos/entrada-masiva', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        params,
      })
      setResultadoEntradaMasiva(res.data)
      if (res.data?.procesados > 0) {
        cargar()
        setArchivoEntradaMasiva(null)
        document.querySelector('#input-entrada-masiva')?.value && (document.querySelector('#input-entrada-masiva').value = '')
      }
    } catch (err) {
      setResultadoEntradaMasiva({
        procesados: 0,
        errores: [{ error: err.response?.data?.detail || 'Error al procesar el archivo' }],
      })
    } finally {
      setSubiendoEntradaMasiva(false)
    }
  }

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
      showError(typeof d === 'string' ? d : 'Error al desactivar')
    } finally {
      setEnviandoEliminar(false)
    }
  }

  const confirmarEliminarPermanente = async () => {
    if (!repuestoAEliminarPermanente) return
    const motivo = motivoEliminar.trim()
    if (motivo.length < 10) {
      showError('El motivo debe tener al menos 10 caracteres para la auditoría.')
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
      showError(typeof d === 'string' ? d : 'Error al eliminar permanentemente')
    } finally {
      setEnviandoEliminarPermanente(false)
    }
  }

  const activarRepuesto = async (r) => {
    try {
      await api.post(`/repuestos/${r.id_repuesto}/activar`)
      cargar()
    } catch (err) {
      showError(err, 'Error al reactivar')
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
      showError('Stock debe ser un número mayor o igual a 0.')
      return
    }
    if (motivo.length < 10) {
      showError('El motivo debe tener al menos 10 caracteres.')
      return
    }
    if (stockNuevo === (repuestoAjuste.stock_actual ?? 0)) {
      showError('El nuevo stock es igual al actual. No se requiere ajuste.')
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
      showError(err, 'Error al ajustar inventario')
    } finally {
      setEnviandoAjuste(false)
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
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `inventario_${hoyStr()}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      showError(err, 'Error al exportar')
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
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `ajustes_inventario_${hoyStr()}.xlsx`
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      showError(err, 'Error al exportar')
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

  const crearOrdenDesdeSugerencia = async (g) => {
    if (!g?.id_proveedor || !g.items?.length) return
    setCreandoOrdenGrupo(g.id_proveedor)
    try {
      await api.post('/ordenes-compra/', {
        id_proveedor: g.id_proveedor,
        observaciones: 'Creada desde sugerencia de compra',
        items: g.items.map((item) => ({
          id_repuesto: item.id_repuesto,
          cantidad_solicitada: item.cantidad_sugerida,
          precio_unitario_estimado: item.precio_compra ?? 0,
        })),
      })
      invalidate(['ordenes-compra'])
      setModalSugerencia(false)
      setGruposSugerencia([])
      navigate('/ordenes-compra')
    } catch (err) {
      showError(err, 'Error al crear la orden')
    } finally {
      setCreandoOrdenGrupo(null)
    }
  }

  if (loading && repuestos.length === 0) return <div className="py-6"><p className="text-slate-500">Cargando...</p></div>

  const bodegasActivas = bodegas.filter((b) => b.activo !== false)

  return (
    <div className="min-h-0">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Inventario</h1>
        <div className="flex flex-wrap gap-2">
          {puedeEditar && (
            <Link to="/inventario/nuevo" className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium inline-flex items-center justify-center touch-manipulation">+ Nuevo repuesto</Link>
          )}
          <button type="button" onClick={exportarExcel} disabled={exportando} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 font-medium disabled:opacity-50 text-sm touch-manipulation">📥 {exportando ? 'Exportando...' : 'Exportar'}</button>
          {puedeEditar && (
            <>
              <button type="button" onClick={abrirModalSugerencia} className="min-h-[44px] px-3 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:bg-amber-800 text-sm font-medium touch-manipulation" title="Sugerencia de compra">🛒 Sugerencia</button>
              <button type="button" onClick={abrirModalEntradaMasiva} className="min-h-[44px] px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm font-medium touch-manipulation" title="Entrada masiva">📥 Entrada masiva</button>
              <button type="button" onClick={abrirModalAuditoria} className="min-h-[44px] px-3 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-900 active:bg-slate-950 text-sm font-medium touch-manipulation" title="Auditoría">🔍 Auditoría</button>
              <Link to="/inventario/alertas" className="min-h-[44px] px-3 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 active:bg-amber-700 text-sm font-medium inline-flex items-center justify-center touch-manipulation">⚠️ Alertas</Link>
            </>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[120px]">
            <label className="block text-xs text-slate-500 mb-1">Buscar</label>
            <input type="text" placeholder="Código, nombre, marca..." value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div className="min-w-[120px] flex-1 sm:flex-initial">
            <label className="block text-xs text-slate-500 mb-1">Categoría</label>
            <select value={filtroCategoria} onChange={(e) => { setFiltroCategoria(e.target.value); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
              <option value="">Todas</option>
              {categorias.map((c) => (
                <option key={c.id_categoria} value={c.id_categoria}>{c.nombre}</option>
              ))}
            </select>
          </div>
          <div className="min-w-[120px] flex-1 sm:flex-initial">
            <label className="block text-xs text-slate-500 mb-1">Bodega</label>
            <select value={filtroBodega} onChange={(e) => { setFiltroBodega(e.target.value); setFiltroUbicacion(''); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
              <option value="">Todas</option>
              {bodegas.filter((b) => b.activo !== false).map((b) => (
                <option key={b.id} value={b.id}>{b.nombre}</option>
              ))}
            </select>
          </div>
          <div className="min-w-[140px] flex-1 sm:flex-initial">
            <label className="block text-xs text-slate-500 mb-1">Ubicación</label>
            <select value={filtroUbicacion} onChange={(e) => { setFiltroUbicacion(e.target.value); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
              <option value="">Todas</option>
              {ubicaciones.filter((u) => !filtroBodega || Number(u.id_bodega) === Number(filtroBodega)).filter((u) => u.activo !== false).map((u) => (
                <option key={u.id} value={u.id}>{u.bodega_nombre ? `${u.bodega_nombre} → ${u.codigo}` : `${u.codigo} - ${u.nombre || ''}`}</option>
              ))}
            </select>
          </div>
          <div className="min-w-[100px]">
            <label className="block text-xs text-slate-500 mb-1">Estado</label>
            <select value={filtroActivo} onChange={(e) => { setFiltroActivo(e.target.value); setPagina(1) }} className="w-full px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </select>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm min-h-[44px] cursor-pointer touch-manipulation">
              <input type="checkbox" checked={filtroStockBajo} onChange={(e) => { setFiltroStockBajo(e.target.checked); setPagina(1) }} className="rounded" />
              Stock bajo
            </label>
            {esAdmin && (
              <label className="flex items-center gap-2 text-sm min-h-[44px] cursor-pointer touch-manipulation" title="Ver eliminados">
                <input type="checkbox" checked={incluirEliminados} onChange={(e) => { setIncluirEliminados(e.target.checked); setPagina(1) }} className="rounded" />
                Ver eliminados
              </label>
            )}
          </div>
          {esAdmin && (
            <div className="flex flex-wrap gap-2">
              <Link to="/configuracion?tab=categorias-repuestos" className="min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 active:bg-slate-100 text-sm inline-flex items-center touch-manipulation">⚙️</Link>
              <Link to="/configuracion?tab=bodegas" className="min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 active:bg-slate-100 text-sm inline-flex items-center touch-manipulation">🏪</Link>
              <Link to="/configuracion?tab=ubicaciones" className="min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 active:bg-slate-100 text-sm inline-flex items-center touch-manipulation">📍</Link>
            </div>
          )}
        </div>
      </div>

      {bodegasActivas.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4 items-center">
          <span className="text-sm text-slate-500">Bodega rápida:</span>
          <button type="button" onClick={() => { setFiltroBodega(''); setFiltroUbicacion(''); setPagina(1) }} className={`min-h-[44px] px-3 py-2 rounded-full text-sm font-medium transition-colors touch-manipulation ${!filtroBodega ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 active:bg-slate-300'}`}>Todas</button>
          {bodegasActivas.map((b) => (
            <button key={b.id} type="button" onClick={() => { setFiltroBodega(String(b.id)); setFiltroUbicacion(''); setPagina(1) }} className={`min-h-[44px] px-3 py-2 rounded-full text-sm font-medium transition-colors touch-manipulation ${filtroBodega === String(b.id) ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 active:bg-slate-300'}`}>{b.nombre}</button>
          ))}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <div className="overflow-x-auto min-w-0">
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
                    <td className="px-2 sm:px-4 py-3 text-center">
                      <Link to={`/inventario/kardex/${r.id_repuesto}`} className="min-h-[36px] inline-flex items-center justify-center px-2 py-1.5 text-sm text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded touch-manipulation" title="Kardex">📋</Link>
                    </td>
                    {puedeEditar && (
                      <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex gap-1 justify-end flex-wrap">
                          {r.eliminado ? (
                            <span className="text-xs text-slate-500 italic">Solo consulta</span>
                          ) : r.activo !== false ? (
                            <>
                              <Link to={`/inventario/entrada/${r.id_repuesto}`} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-green-600 hover:text-green-700 active:bg-green-50 rounded touch-manipulation" title="Agregar stock">➕</Link>
                              <button type="button" onClick={() => abrirModalAjuste(r)} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-amber-600 hover:text-amber-700 active:bg-amber-50 rounded touch-manipulation" title="Ajustar stock">⚙️</button>
                              <button type="button" onClick={() => navigate(`/inventario/editar/${r.id_repuesto}`)} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation" title="Editar">✏️</button>
                              <button type="button" onClick={() => abrirModalEliminar(r)} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation" title="Desactivar">🗑️</button>
                              {esAdmin && (
                                <button type="button" onClick={() => abrirModalEliminarPermanente(r)} className="min-h-[36px] min-w-[36px] flex items-center justify-center text-sm text-red-800 hover:text-red-900 active:bg-red-100 rounded touch-manipulation" title="Eliminar permanentemente">⛔</button>
                              )}
                            </>
                          ) : (
                            <button type="button" onClick={() => activarRepuesto(r)} className="min-h-[36px] px-2 py-1.5 text-sm text-green-600 hover:text-green-700 active:bg-green-50 rounded touch-manipulation" title="Reactivar">✓</button>
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
          <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation">← Anterior</button>
          <span className="min-h-[44px] px-4 py-2 flex items-center justify-center text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-200">Pág. {pagina} de {totalPaginas} ({total})</span>
          <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white font-medium rounded-lg shadow-md hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation">Siguiente →</button>
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
          <button type="button" onClick={() => setImagenAmpliada(null)} className="absolute top-4 right-4 min-w-[48px] min-h-[48px] rounded-full bg-white/90 hover:bg-white active:bg-slate-100 text-slate-700 flex items-center justify-center text-xl touch-manipulation" aria-label="Cerrar">×</button>
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
            <button type="button" onClick={recargarSugerencia} disabled={cargandoSugerencia} className="min-h-[44px] px-3 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:bg-amber-800 text-sm disabled:opacity-50 touch-manipulation">
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
                    link.download = `sugerencia_compra_${hoyStr()}.xlsx`
                    link.click()
                    window.URL.revokeObjectURL(link.href)
                  } catch (err) {
                    showError(err, 'Error al exportar')
                  }
                }}
                className="min-h-[44px] px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm font-medium ml-auto touch-manipulation"
              >
                📥 Exportar
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
                  <div className="bg-slate-100 px-4 py-2 flex justify-between items-center gap-3 flex-wrap">
                    <span className="font-medium text-slate-800">{g.nombre || 'Sin proveedor'}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-amber-700">Total: ${(g.total_estimado ?? 0).toFixed(2)}</span>
                      {g.id_proveedor && g.items?.length > 0 && puedeEditar && (
                        <button
                          type="button"
                          onClick={() => crearOrdenDesdeSugerencia(g)}
                          disabled={creandoOrdenGrupo !== null}
                          className="min-h-[44px] px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
                        >
                          {creandoOrdenGrupo === g.id_proveedor ? 'Creando...' : 'Crear orden'}
                        </button>
                      )}
                    </div>
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

      <Modal
        titulo="Entrada masiva"
        abierto={modalEntradaMasiva}
        onCerrar={() => { setModalEntradaMasiva(false); setResultadoEntradaMasiva(null); setArchivoEntradaMasiva(null) }}
        size="lg"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Carga varios repuestos a la vez desde un archivo Excel (.xlsx) o CSV. Columnas: <strong>codigo</strong>, <strong>cantidad</strong>, precio_unitario (opc), referencia (opc), observaciones (opc).
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={descargarPlantillaEntradaMasiva} className="min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 text-sm font-medium touch-manipulation">📋 Descargar plantilla</button>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Archivo</label>
            <input id="input-entrada-masiva" type="file" accept=".xlsx,.csv" onChange={(e) => setArchivoEntradaMasiva(e.target.files?.[0] || null)} className="block w-full text-sm text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 file:min-h-[44px] file:flex file:items-center" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Proveedor (opcional)</label>
              <select value={proveedorEntradaMasiva} onChange={(e) => setProveedorEntradaMasiva(e.target.value)} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation"
              >
                <option value="">Ninguno</option>
                {proveedores.filter((p) => p.activo !== false).map((p) => (
                  <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Referencia global (opcional)</label>
              <input type="text" value={referenciaEntradaMasiva} onChange={(e) => setReferenciaEntradaMasiva(e.target.value)} placeholder="Ej: FACT-001" className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
          </div>
          {resultadoEntradaMasiva && (
            <div className={`p-4 rounded-lg border ${resultadoEntradaMasiva.procesados > 0 ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
              <p className="font-medium text-slate-800">
                {resultadoEntradaMasiva.procesados} entradas procesadas
                {resultadoEntradaMasiva.total_filas != null && ` de ${resultadoEntradaMasiva.total_filas} filas`}
              </p>
              {resultadoEntradaMasiva.errores?.length > 0 && (
                <div className="mt-2 max-h-32 overflow-y-auto">
                  <p className="text-sm font-medium text-red-700 mb-1">Errores:</p>
                  <ul className="text-sm text-red-600 space-y-0.5">
                    {resultadoEntradaMasiva.errores.slice(0, 10).map((e, i) => (
                      <li key={i}>Fila {e.fila}: {e.codigo || '(sin código)'} - {e.error}</li>
                    ))}
                    {resultadoEntradaMasiva.errores.length > 10 && (
                      <li>... y {resultadoEntradaMasiva.errores.length - 10} más</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}
          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button type="button" onClick={submitEntradaMasiva} disabled={!archivoEntradaMasiva || subiendoEntradaMasiva} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 font-medium disabled:opacity-50 text-sm touch-manipulation">{subiendoEntradaMasiva ? 'Procesando...' : 'Procesar archivo'}</button>
          </div>
        </div>
      </Modal>

      <Modal titulo="Desactivar repuesto" abierto={modalEliminar} onCerrar={() => { setModalEliminar(false); setRepuestoAEliminar(null) }}>
        <div className="space-y-4">
          {repuestoAEliminar && (
            <>
              <p className="text-slate-600">¿Desactivar el repuesto <strong>{repuestoAEliminar.nombre}</strong> ({repuestoAEliminar.codigo})? No se eliminará, solo dejará de aparecer como opción activa.</p>
              <div className="flex flex-wrap justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminar(false); setRepuestoAEliminar(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
                <button type="button" onClick={confirmarEliminar} disabled={enviandoEliminar} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">{enviandoEliminar ? 'Desactivando...' : 'Desactivar'}</button>
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
                className="self-start min-h-[44px] px-3 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:bg-amber-800 text-sm font-medium touch-manipulation"
              >
                Ir a iniciar sesión
              </button>
            </div>
          )}
          <div className="flex flex-wrap gap-3 items-end p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Desde</label>
              <input type="date" value={filtrosAuditoria.fecha_desde} onChange={(e) => setFiltrosAuditoria((f) => ({ ...f, fecha_desde: e.target.value }))} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Hasta</label>
              <input type="date" value={filtrosAuditoria.fecha_hasta} onChange={(e) => setFiltrosAuditoria((f) => ({ ...f, fecha_hasta: e.target.value }))} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Usuario</label>
              <select value={filtrosAuditoria.id_usuario} onChange={(e) => setFiltrosAuditoria((f) => ({ ...f, id_usuario: e.target.value }))} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation min-w-[140px]">
                <option value="">Todos</option>
                {usuarios.map((u) => (
                  <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>
                ))}
              </select>
            </div>
            <button type="button" onClick={aplicarFiltrosAuditoria} disabled={cargandoAuditoria} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium disabled:opacity-50 touch-manipulation">{cargandoAuditoria ? 'Buscando...' : 'Buscar'}</button>
            <button type="button" onClick={exportarAuditoriaExcel} disabled={exportandoAuditoria} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm font-medium disabled:opacity-50 ml-auto touch-manipulation">📥 {exportandoAuditoria ? 'Exportando...' : 'Exportar'}</button>
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
                        {formatearFechaHora(m.fecha_movimiento)}
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
                <input type="number" min="0" step="1" value={formAjuste.stock_nuevo} onChange={(e) => setFormAjuste((f) => ({ ...f, stock_nuevo: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Motivo (mín. 10 caracteres) *</label>
                <textarea value={formAjuste.motivo} onChange={(e) => setFormAjuste((f) => ({ ...f, motivo: e.target.value }))} rows={3} placeholder="Ej: Conteo físico mensual..." className="w-full px-3 py-2 min-h-[80px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Referencia (opcional)</label>
                <input type="text" value={formAjuste.referencia} onChange={(e) => setFormAjuste((f) => ({ ...f, referencia: e.target.value }))} placeholder="Nº de acta, folio..." className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <button type="button" onClick={() => { setModalAjuste(false); setRepuestoAjuste(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
                <button type="button" onClick={confirmarAjuste} disabled={enviandoAjuste || !formAjuste.motivo.trim() || formAjuste.motivo.trim().length < 10} className="min-h-[44px] px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50 touch-manipulation">{enviandoAjuste ? 'Ajustando...' : 'Ajustar'}</button>
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
                <textarea value={motivoEliminar} onChange={(e) => setMotivoEliminar(e.target.value)} rows={3} placeholder="Ej: Producto discontinuado, error de carga, duplicado..." className="w-full px-3 py-2 min-h-[80px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 touch-manipulation" required />
              </div>
              <div className="flex flex-wrap justify-end gap-2">
                <button type="button" onClick={() => { setModalEliminarPermanente(false); setRepuestoAEliminarPermanente(null); setMotivoEliminar('') }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
                <button type="button" onClick={confirmarEliminarPermanente} disabled={enviandoEliminarPermanente || motivoEliminar.trim().length < 10} className="min-h-[44px] px-4 py-2 bg-red-700 text-white rounded-lg hover:bg-red-800 active:bg-red-900 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation">{enviandoEliminarPermanente ? 'Eliminando...' : 'Eliminar permanentemente'}</button>
              </div>
            </>
          )}
        </div>
      </Modal>

    </div>
  )
}
