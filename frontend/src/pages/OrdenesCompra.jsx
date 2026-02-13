import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { useApiQuery, useInvalidateQueries } from '../hooks/useApi'
import { aNumero, aEntero, esNumeroValido } from '../utils/numeros'

const LIMIT = 20
const ALLOWED_EXT = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf']

const labelEstado = (est, saldoPendiente = null) => {
  const m = { BORRADOR: 'Borrador', AUTORIZADA: 'Autorizada', ENVIADA: 'Enviada (Iniciada)', RECIBIDA_PARCIAL: 'Recibida parcial', RECIBIDA: 'Recibida', CANCELADA: 'Cancelada' }
  const base = m[est] || est
  if (est === 'RECIBIDA' || est === 'RECIBIDA_PARCIAL') {
    const saldo = saldoPendiente ?? 0
    if (saldo <= 0) {
      return base.replace(/^Recibida parcial$/, 'Recibida parcial/Pagada').replace(/^Recibida$/, 'Recibida/Pagada')
    }
    return base.replace(/^Recibida parcial$/, 'Recibida parcial (Pend. por pago)').replace(/^Recibida$/, 'Recibida (Pend. por pago)')
  }
  return base
}

// Formatea YYYY-MM-DD sin desfase por zona horaria (evita que 2026-02-07 muestre 6/2/2026)
const formatFechaLocal = (isoStr) => {
  if (!isoStr) return '-'
  const s = String(isoStr).slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return new Date(isoStr).toLocaleDateString('es-MX')
  return new Date(s + 'T12:00:00').toLocaleDateString('es-MX')
}

export default function OrdenesCompra() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const invalidate = useInvalidateQueries()
  const [pagina, setPagina] = useState(1)
  const [filtroEstado, setFiltroEstado] = useState('')
  const [filtroProveedor, setFiltroProveedor] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [soloPendientesRecibir, setSoloPendientesRecibir] = useState(() => searchParams.get('pendientes') === '1')

  const params = { skip: (pagina - 1) * LIMIT, limit: LIMIT }
  if (soloPendientesRecibir) params.pendientes_recibir = true
  else if (filtroEstado) params.estado = filtroEstado
  if (filtroProveedor) params.id_proveedor = filtroProveedor

  const { data: dataOrdenes, isLoading: loadingOrdenes, refetch } = useApiQuery(
    ['ordenes-compra', pagina, filtroEstado, filtroProveedor, soloPendientesRecibir],
    () => api.get('/ordenes-compra/', { params }).then((r) => r.data)
  )

  const { data: alertasOC = {} } = useApiQuery(
    ['ordenes-compra-alertas'],
    () => api.get('/ordenes-compra/alertas', { params: { limit: 5 } }).then((r) => r.data)
  )

  const { data: proveedores = [] } = useApiQuery(
    ['proveedores-ordenes-compra'],
    () => api.get('/proveedores/', { params: { limit: 500, activo: true } }).then((r) => r.data?.proveedores ?? r.data ?? [])
  )

  const { data: estados = [] } = useApiQuery(
    ['ordenes-compra-estados'],
    () => api.get('/ordenes-compra/estados').then((r) => r.data)
  )

  const ordenes = dataOrdenes?.ordenes ?? []
  const total = dataOrdenes?.total ?? 0
  const totalPaginas = dataOrdenes?.total_paginas ?? 1

  const [modalDetalle, setModalDetalle] = useState(false)
  const [ordenDetalle, setOrdenDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [modalRecibir, setModalRecibir] = useState(false)
  const [modalPagar, setModalPagar] = useState(false)
  const [modalCancelar, setModalCancelar] = useState(false)
  const [formRecibir, setFormRecibir] = useState({ items: [], referencia_proveedor: '' })
  const [enviandoRecibir, setEnviandoRecibir] = useState(false)
  const [formPago, setFormPago] = useState({ monto: '', metodo: 'EFECTIVO', referencia: '' })
  const [enviandoPago, setEnviandoPago] = useState(false)
  const [motivoCancelar, setMotivoCancelar] = useState('')
  const [evidenciaCancelar, setEvidenciaCancelar] = useState('')
  const [subiendoEvidenciaCancelar, setSubiendoEvidenciaCancelar] = useState(false)
  const [enviandoCancelar, setEnviandoCancelar] = useState(false)
  const [subiendoComprobante, setSubiendoComprobante] = useState(false)
  const [editFechaEst, setEditFechaEst] = useState('')
  const [enviandoOrden, setEnviandoOrden] = useState(false)
  const [enviandoAutorizar, setEnviandoAutorizar] = useState(false)

  const puedeGestionar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  const abrirDetalle = (orden) => {
    setOrdenDetalle(orden)
    setModalDetalle(true)
    setCargandoDetalle(true)
    setEditFechaEst('')
    api
      .get(`/ordenes-compra/${orden.id_orden_compra}`)
      .then((r) => {
        setOrdenDetalle(r.data)
        const fe = r.data?.fecha_estimada_entrega
        setEditFechaEst(fe ? fe.slice(0, 10) : '')
      })
      .catch(() => setOrdenDetalle(null))
      .finally(() => setCargandoDetalle(false))
  }

  const verId = searchParams.get('ver')
  useEffect(() => {
    if (verId && /^\d+$/.test(verId)) {
      abrirDetalle({ id_orden_compra: parseInt(verId) })
      setSearchParams((prev) => {
        const p = new URLSearchParams(prev)
        p.delete('ver')
        return Object.fromEntries(p.entries())
      }, { replace: true })
    }
  }, [verId])

  const puedeEditarComprobanteYFecha = ordenDetalle && ['BORRADOR', 'AUTORIZADA', 'ENVIADA', 'RECIBIDA_PARCIAL'].includes(ordenDetalle.estado)
  const puedeAdjuntarComprobante = ordenDetalle && ['ENVIADA', 'AUTORIZADA', 'RECIBIDA_PARCIAL'].includes(ordenDetalle.estado)

  const fechaGuardada = ordenDetalle?.fecha_estimada_entrega ? String(ordenDetalle.fecha_estimada_entrega).slice(0, 10) : ''
  const hasUnsavedFechaChange = !!fechaGuardada && !!editFechaEst?.trim() && editFechaEst.trim() !== fechaGuardada

  const cerrarModalDetalle = () => {
    if (hasUnsavedFechaChange) {
      alert('Modificaste la fecha promesa pero no la guardaste. Los cambios no se guardarán; se mantendrá la fecha que guardaste anteriormente.')
    }
    setModalDetalle(false)
    setOrdenDetalle(null)
  }

  const abrirRecibirConAlerta = () => {
    if (hasUnsavedFechaChange) {
      const continuar = window.confirm('Modificaste la fecha promesa pero no la guardaste. Se usará la fecha que guardaste anteriormente.\n\n¿Continuar con Recibir mercancía? (Cancelar para guardar la nueva fecha primero)')
      if (!continuar) return
    }
    abrirRecibir()
  }

  const subirComprobante = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !ordenDetalle || !puedeAdjuntarComprobante) return
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED_EXT.includes(ext)) {
      alert(`Formato no permitido. Use: ${ALLOWED_EXT.join(', ')}`)
      e.target.value = ''
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('El archivo no debe superar 5 MB')
      e.target.value = ''
      return
    }
    setSubiendoComprobante(true)
    try {
      const fd = new FormData()
      fd.append('archivo', file)
      const up = await api.post('/inventario/movimientos/upload-comprobante', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      const url = up.data?.url
      if (!url) throw new Error('No se recibió URL')
      await api.put(`/ordenes-compra/${ordenDetalle.id_orden_compra}`, { comprobante_url: url })
      setOrdenDetalle((o) => ({ ...o, comprobante_url: url }))
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al subir comprobante')
    } finally {
      setSubiendoComprobante(false)
      e.target.value = ''
    }
  }

  const guardarFechaEstimada = async () => {
    if (!ordenDetalle || !puedeEditarComprobanteYFecha) return
    const val = editFechaEst?.trim() || null
    if (val) {
      const hoy = new Date()
      hoy.setHours(0, 0, 0, 0)
      const sel = new Date(val + 'T12:00:00')
      if (sel < hoy) {
        alert('La fecha promesa no puede ser anterior a hoy. Si pides hoy, no podrás recibir ayer.')
        return
      }
    }
    try {
      const res = await api.put(`/ordenes-compra/${ordenDetalle.id_orden_compra}`, {
        fecha_estimada_entrega: val || null,
      })
      setOrdenDetalle(res.data)
      setEditFechaEst(res.data?.fecha_estimada_entrega ? res.data.fecha_estimada_entrega.slice(0, 10) : '')
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al guardar')
    }
  }

  const autorizarOrden = async (oc) => {
    setEnviandoAutorizar(true)
    try {
      await api.post(`/ordenes-compra/${oc.id_orden_compra}/autorizar`)
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
      abrirDetalle({ ...oc, estado: 'AUTORIZADA' })
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al autorizar')
    } finally {
      setEnviandoAutorizar(false)
    }
  }

  const enviarOrden = async (oc) => {
    setEnviandoOrden(true)
    try {
      const res = await api.post(`/ordenes-compra/${oc.id_orden_compra}/enviar`)
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
      abrirDetalle({ ...oc, estado: 'ENVIADA' })
      if (res.data?.email_enviado) {
        alert('Orden enviada. Se envió un email al proveedor con el detalle.')
      } else if (res.data?.mensaje_email) {
        alert(`Orden enviada (estado actualizado). El email no se pudo enviar: ${res.data.mensaje_email}`)
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al enviar')
    } finally {
      setEnviandoOrden(false)
    }
  }

  const abrirRecibir = () => {
    if (!ordenDetalle) return
    const items = (ordenDetalle.detalles || [])
      .filter((d) => (d.cantidad_pendiente ?? d.cantidad_solicitada - d.cantidad_recibida) > 0)
      .map((d) => ({
        id_detalle: d.id,
        cantidad_recibida: d.cantidad_pendiente ?? d.cantidad_solicitada - d.cantidad_recibida,
        precio_unitario_real: d.precio_unitario_real ?? d.precio_unitario_estimado ?? null,
      }))
    setFormRecibir({ items, referencia_proveedor: ordenDetalle.referencia_proveedor || '' })
    setModalRecibir(true)
  }

  const recibirMercancia = async (e) => {
    e.preventDefault()
    if (!ordenDetalle || formRecibir.items.length === 0) return
    const itemsEnviar = formRecibir.items
      .map((it) => ({ id_detalle: it.id_detalle, cantidad_recibida: aEntero(it.cantidad_recibida), precio_unitario_real: it.precio_unitario_real != null && it.precio_unitario_real !== '' ? aNumero(it.precio_unitario_real) : null }))
      .filter((it) => it.cantidad_recibida > 0)
    if (itemsEnviar.length === 0) {
      alert('Indica al menos una cantidad recibida mayor a 0')
      return
    }
    const sinPrecio = itemsEnviar.filter((it) => it.precio_unitario_real == null || !esNumeroValido(it.precio_unitario_real) || it.precio_unitario_real <= 0)
    if (sinPrecio.length > 0) {
      alert('Indica el precio real (mayor a 0) para cada ítem antes de recibir.')
      return
    }
    setEnviandoRecibir(true)
    try {
      const res = await api.post(`/ordenes-compra/${ordenDetalle.id_orden_compra}/recibir`, {
        items: itemsEnviar,
        referencia_proveedor: formRecibir.referencia_proveedor?.trim() || null,
      })
      setOrdenDetalle(res.data)
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
      setModalRecibir(false)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al recibir')
    } finally {
      setEnviandoRecibir(false)
    }
  }

  const abrirPagar = async () => {
    if (!ordenDetalle) return
    try {
      const r = await api.get('/ordenes-compra/cuentas-por-pagar')
      const item = (r.data?.items ?? []).find((i) => i.id_orden_compra === ordenDetalle.id_orden_compra)
      const saldo = item?.saldo_pendiente ?? ordenDetalle.detalles?.reduce((acc, d) => {
        const cant = d.cantidad_recibida || 0
        const precio = d.precio_unitario_real ?? d.precio_unitario_estimado ?? 0
        return acc + cant * precio
      }, 0) ?? 0
      setFormPago({ monto: saldo.toFixed(2), metodo: 'EFECTIVO', referencia: '' })
    } catch {
      const total = ordenDetalle.detalles?.reduce((acc, d) => {
        const cant = d.cantidad_recibida || 0
        const precio = d.precio_unitario_real ?? d.precio_unitario_estimado ?? 0
        return acc + cant * precio
      }, 0) ?? 0
      setFormPago({ monto: total.toFixed(2), metodo: 'EFECTIVO', referencia: '' })
    }
    setModalPagar(true)
  }

  const registrarPago = async (e) => {
    e.preventDefault()
    if (!ordenDetalle || !esNumeroValido(formPago.monto) || aNumero(formPago.monto) <= 0) return
    setEnviandoPago(true)
    try {
      await api.post(`/ordenes-compra/${ordenDetalle.id_orden_compra}/pagar`, {
        monto: aNumero(formPago.monto),
        metodo: formPago.metodo,
        referencia: formPago.referencia?.trim() || null,
      })
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
      setModalPagar(false)
      api.get(`/ordenes-compra/${ordenDetalle.id_orden_compra}`).then((r) => setOrdenDetalle(r.data))
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al registrar pago')
    } finally {
      setEnviandoPago(false)
    }
  }

  const abrirCancelar = () => {
    setMotivoCancelar('')
    setEvidenciaCancelar('')
    setModalCancelar(true)
  }

  const subirEvidenciaCancelar = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED_EXT.includes(ext)) {
      alert(`Formato no permitido. Use: ${ALLOWED_EXT.join(', ')}`)
      e.target.value = ''
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('El archivo no debe superar 5 MB')
      e.target.value = ''
      return
    }
    setSubiendoEvidenciaCancelar(true)
    try {
      const fd = new FormData()
      fd.append('archivo', file)
      const up = await api.post('/inventario/movimientos/upload-comprobante', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      const url = up.data?.url ?? ''
      setEvidenciaCancelar(url)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al subir evidencia')
    } finally {
      setSubiendoEvidenciaCancelar(false)
      e.target.value = ''
    }
  }

  const cancelarOrden = async (e) => {
    e.preventDefault()
    if (!ordenDetalle || motivoCancelar.trim().length < 5) {
      alert('El motivo debe tener al menos 5 caracteres')
      return
    }
    setEnviandoCancelar(true)
    try {
      const payload = { motivo: motivoCancelar.trim() }
      if (evidenciaCancelar?.trim()) payload.evidencia_cancelacion_url = evidenciaCancelar.trim()
      await api.post(`/ordenes-compra/${ordenDetalle.id_orden_compra}/cancelar`, payload)
      invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
      setModalDetalle(false)
      setModalCancelar(false)
      setOrdenDetalle(null)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al cancelar')
    } finally {
      setEnviandoCancelar(false)
    }
  }

  const colorEstado = (est) => {
    const m = { BORRADOR: 'bg-slate-100 text-slate-700', AUTORIZADA: 'bg-indigo-100 text-indigo-800', ENVIADA: 'bg-blue-100 text-blue-800', RECIBIDA: 'bg-green-100 text-green-800', RECIBIDA_PARCIAL: 'bg-amber-100 text-amber-800', CANCELADA: 'bg-red-100 text-red-700' }
    return m[est] || 'bg-slate-100'
  }

  if (loadingOrdenes && ordenes.length === 0) return <p className="text-slate-500">Cargando...</p>

  const hayVencidas = (alertasOC.ordenes_vencidas || 0) > 0

  return (
    <div className="min-h-0 flex flex-col">
      {hayVencidas && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <span className="text-amber-700 font-medium">⚠️ {alertasOC.ordenes_vencidas} orden(es) vencida(s) pendiente(s) de recibir</span>
          <button type="button" onClick={() => setSoloPendientesRecibir(true)} className="min-h-[44px] px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:bg-amber-800 text-sm touch-manipulation">
            Ver pendientes de recibir
          </button>
        </div>
      )}
      <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center mb-4 gap-3">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Ordenes de compra</h1>
        <div className="flex flex-wrap gap-2 items-center">
          <label className="flex items-center gap-2 text-sm cursor-pointer min-h-[44px] touch-manipulation">
            <input type="checkbox" checked={soloPendientesRecibir} onChange={(e) => { setSoloPendientesRecibir(e.target.checked); setFiltroEstado(''); setPagina(1) }} className="rounded w-5 h-5" />
            <span className="text-slate-600">Pendientes de recibir</span>
          </label>
          <select value={filtroEstado} onChange={(e) => { setFiltroEstado(e.target.value); setSoloPendientesRecibir(false); setPagina(1) }} disabled={soloPendientesRecibir} className="min-h-[44px] px-3 py-2 text-base sm:text-sm border border-slate-300 rounded-lg disabled:opacity-50 touch-manipulation min-w-[140px]">
            <option value="">Todos los estados</option>
            {estados.map((e) => (
              <option key={e.valor} value={e.valor}>{e.valor}</option>
            ))}
          </select>
          <select value={filtroProveedor} onChange={(e) => { setFiltroProveedor(e.target.value); setPagina(1) }} className="min-h-[44px] px-3 py-2 text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation min-w-[140px]">
            <option value="">Todos los proveedores</option>
            {proveedores.map((p) => (
              <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
            ))}
          </select>
          <Link to="/cuentas-por-pagar" className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 text-sm inline-flex items-center touch-manipulation">Cuentas por pagar</Link>
          {puedeGestionar && (
            <Link to="/ordenes-compra/nueva" className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 text-sm font-medium inline-flex items-center touch-manipulation">Nueva orden</Link>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 flex-1 min-h-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Número</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Proveedor</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Estado</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha est.</th>
                <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {ordenes.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">No hay ordenes de compra</td>
                </tr>
              ) : (
                ordenes.map((o) => (
                  <tr key={o.id_orden_compra} className="hover:bg-slate-50">
                    <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{o.numero}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{o.nombre_proveedor}</td>
                    <td className="px-2 sm:px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${colorEstado(o.estado)}`}>{labelEstado(o.estado, o.saldo_pendiente)}</span>
                    </td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{formatFechaLocal(o.fecha)}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm">
                      {o.fecha_estimada_entrega ? (
                        <span className={o.vencida ? 'text-red-600 font-medium' : ''}>
                          {formatFechaLocal(o.fecha_estimada_entrega)}
                          {o.vencida && <span className="ml-1 text-xs">(vencida)</span>}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                      <span className="inline-flex gap-2 justify-end flex-wrap">
                        <button type="button" onClick={() => abrirDetalle(o)} className="min-h-[36px] px-2 py-1.5 text-sm text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded touch-manipulation">Ver</button>
                        {user?.rol === 'ADMIN' && ['BORRADOR', 'AUTORIZADA', 'ENVIADA'].includes(o.estado) && (
                          <button
                            type="button"
                            onClick={async () => {
                              try {
                                const r = await api.get(`/ordenes-compra/${o.id_orden_compra}`)
                                if (!['BORRADOR', 'AUTORIZADA', 'ENVIADA'].includes(r.data?.estado)) {
                                  await refetch()
                                  invalidate(['ordenes-compra']); invalidate(['ordenes-compra-alertas'])
                                  alert(`La orden ${r.data?.numero} ya no se puede cancelar (estado: ${r.data?.estado}).`)
                                  return
                                }
                                setOrdenDetalle(r.data)
                                setMotivoCancelar('')
                                setEvidenciaCancelar('')
                                setModalCancelar(true)
                              } catch {
                                alert('Error al cargar la orden.')
                              }
                            }}
                            className="min-h-[36px] px-2 py-1.5 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation"
                          >
                            Cancelar
                          </button>
                        )}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPaginas > 1 && (
        <div className="mt-4 flex flex-col sm:flex-row justify-center sm:justify-end gap-3 items-stretch sm:items-center p-3 bg-slate-50 rounded-lg border border-slate-200">
          <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">← Anterior</button>
          <span className="min-h-[44px] px-4 py-2 flex items-center justify-center text-sm font-medium text-slate-700 bg-white rounded-lg border border-slate-200">Pág. {pagina} de {totalPaginas} ({total})</span>
          <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">Siguiente →</button>
        </div>
      )}

      {/* Modal detalle */}
      <Modal titulo={ordenDetalle ? `Orden ${ordenDetalle.numero}` : 'Detalle'} abierto={modalDetalle} onCerrar={cerrarModalDetalle} size="xl">
        {cargandoDetalle ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <svg className="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-slate-500">Cargando detalle...</p>
          </div>
        ) : ordenDetalle ? (
          <div className="space-y-4">
            {ordenDetalle.vencida && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm font-medium flex items-center gap-2">
                <span>⚠️ Orden vencida</span> – La fecha estimada de entrega ya pasó. Revisa el estado con el proveedor.
              </div>
            )}
            {ordenDetalle.estado === 'CANCELADA' && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
                <strong>Motivo de cancelación:</strong>
                <p className="mt-1 whitespace-pre-wrap">{ordenDetalle.motivo_cancelacion || 'Sin motivo registrado'}</p>
                {ordenDetalle.evidencia_cancelacion_url && (
                  <p className="mt-2">
                    <a href={ordenDetalle.evidencia_cancelacion_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline font-medium">📎 Ver evidencia/imagen</a>
                  </p>
                )}
                {ordenDetalle.fecha_cancelacion && (
                  <p className="mt-1 text-xs text-red-600">Cancelada el {formatFechaLocal(ordenDetalle.fecha_cancelacion)}</p>
                )}
              </div>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div><span className="text-slate-500">Proveedor:</span> {ordenDetalle.nombre_proveedor}</div>
              <div><span className="text-slate-500">Estado:</span> <span className={`px-2 py-0.5 rounded text-xs ${colorEstado(ordenDetalle.estado)}`}>{labelEstado(ordenDetalle.estado, ordenDetalle.saldo_pendiente)}</span></div>
              <div><span className="text-slate-500">Total:</span> {
                (() => {
                  const totalReal = (ordenDetalle.detalles || []).reduce((acc, d) => {
                    const cant = d.cantidad_recibida || 0
                    const precio = (d.precio_unitario_real != null && d.precio_unitario_real > 0) ? d.precio_unitario_real : 0
                    return acc + cant * precio
                  }, 0)
                  return totalReal > 0 ? `$${totalReal.toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '-'
                })()
              }</div>
              <div><span className="text-slate-500">Fecha:</span> {formatFechaLocal(ordenDetalle.fecha)}</div>
              {ordenDetalle.vehiculo_info && <div className="col-span-2"><span className="text-slate-500">Vehículo:</span> {ordenDetalle.vehiculo_info}</div>}
              <div className="col-span-2 sm:col-span-4">
                <span className="text-slate-500">
                  {ordenDetalle.estado === 'AUTORIZADA' ? 'Fecha promesa (obligatorio) *' : 'Fecha promesa (cuando el proveedor informe disponibilidad): '}
                </span>
                {ordenDetalle.estado === 'AUTORIZADA' && puedeGestionar ? (
                  <span className="inline-flex gap-2 items-center flex-wrap">
                    <input type="date" value={editFechaEst} onChange={(e) => setEditFechaEst(e.target.value)} min={(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; })()} required className="px-2 py-2 min-h-[44px] text-base sm:text-sm border rounded touch-manipulation" title="La fecha promesa no puede ser anterior a hoy" />
                    <button type="button" onClick={guardarFechaEstimada} disabled={!editFechaEst?.trim()} className="min-h-[44px] px-2 py-2 text-primary-600 hover:underline active:bg-primary-50 rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation">Guardar</button>
                  </span>
                ) : (
                  ordenDetalle.fecha_estimada_entrega ? formatFechaLocal(ordenDetalle.fecha_estimada_entrega) : '-'
                )}
              </div>
            </div>
            {ordenDetalle.observaciones && <p className="text-sm text-slate-600">{ordenDetalle.observaciones}</p>}
            {ordenDetalle.estado === 'BORRADOR' && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-slate-700 shadow-sm">
                <span className="font-semibold text-amber-800">📋 Flujo:</span> Haz clic en <strong className="text-amber-900">Enviar orden</strong> para notificar al proveedor con la solicitud. Cuando el proveedor responda con la cotización, súbela y autoriza la orden.
              </div>
            )}
            {ordenDetalle.estado === 'ENVIADA' && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-slate-700 shadow-sm">
                <span className="font-semibold text-amber-800">📋 Flujo:</span> El proveedor recibió la solicitud. Cuando responda con la cotización formal, súbela aquí y haz clic en <strong className="text-amber-900">Autorizar orden</strong> para aprobar.
              </div>
            )}
            {ordenDetalle.estado === 'AUTORIZADA' && !ordenDetalle.fecha_estimada_entrega && (
              <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl text-sm text-slate-700 shadow-sm flex items-center gap-2">
                <span className="text-sky-600 text-lg">📅</span>
                <span><strong className="text-sky-800">Paso siguiente:</strong> Ingresa la fecha promesa de llegada y haz clic en <strong>Guardar</strong> para habilitar <strong>Recibir mercancía</strong>.</span>
              </div>
            )}
            <div className="text-sm flex items-center gap-3 flex-wrap">
              <span className="text-slate-500">
                {ordenDetalle.estado === 'BORRADOR' && 'Cotización del proveedor: '}
                {ordenDetalle.estado === 'ENVIADA' && 'Cotización formal del proveedor: '}
                {(ordenDetalle.estado === 'AUTORIZADA' || ordenDetalle.estado === 'RECIBIDA_PARCIAL' || ordenDetalle.estado === 'RECIBIDA') && 'Comprobante: '}
                {ordenDetalle.estado === 'CANCELADA' && 'Cotización del proveedor: '}
              </span>
              {ordenDetalle.comprobante_url ? (
                <>
                  <a href={ordenDetalle.comprobante_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline font-medium">Ver archivo (cotización/comprobante)</a>
                  {puedeAdjuntarComprobante && puedeGestionar && (
                    <label className="text-slate-600 hover:text-primary-600 cursor-pointer text-sm">
                      {subiendoComprobante ? 'Subiendo...' : 'Reemplazar'}
                      <input type="file" accept={ALLOWED_EXT.join(',')} className="hidden" onChange={subirComprobante} disabled={subiendoComprobante} />
                    </label>
                  )}
                </>
              ) : puedeAdjuntarComprobante && puedeGestionar ? (
                <label className="min-h-[44px] px-3 py-2 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 rounded-lg cursor-pointer text-sm font-medium inline-flex items-center touch-manipulation">
                  {subiendoComprobante ? 'Subiendo...' : (ordenDetalle.estado === 'ENVIADA' ? '📎 Subir cotización' : '📎 Adjuntar comprobante')}
                  <input type="file" accept={ALLOWED_EXT.join(',')} className="hidden" onChange={subirComprobante} disabled={subiendoComprobante} />
                </label>
              ) : ordenDetalle.estado === 'BORRADOR' ? (
                <span className="text-slate-400">Envía la orden al proveedor para poder adjuntar la cotización</span>
              ) : (
                <span className="text-slate-400">Sin comprobante</span>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-2">Repuesto</th><th className="text-right">Solicitado</th><th className="text-right">Recibido</th><th className="text-right">Pendiente</th><th className="text-right">Precio</th></tr></thead>
                <tbody>
                  {(ordenDetalle.detalles || []).map((d) => (
                    <tr key={d.id} className="border-b">
                      <td className="py-2">{d.nombre_repuesto || d.codigo_repuesto}</td>
                      <td className="text-right">{d.cantidad_solicitada}</td>
                      <td className="text-right">{d.cantidad_recibida ?? 0}</td>
                      <td className="text-right">{d.cantidad_pendiente ?? (d.cantidad_solicitada - (d.cantidad_recibida || 0))}</td>
                      <td className="text-right">
                        {(d.cantidad_recibida > 0 && (d.precio_unitario_real != null && d.precio_unitario_real > 0))
                          ? `$${(d.precio_unitario_real ?? 0).toFixed(2)}`
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {puedeGestionar && (
              <div className="flex flex-col gap-2 pt-2 border-t">
                {ordenDetalle.estado === 'BORRADOR' && (
                  <p className="text-sm text-slate-600">
                    {ordenDetalle.email_proveedor
                      ? <>Al enviar, se enviará un email a <strong>{ordenDetalle.nombre_proveedor}</strong> ({ordenDetalle.email_proveedor}) con la solicitud.</>
                      : <>El proveedor <strong>{ordenDetalle.nombre_proveedor}</strong> no tiene email configurado. Solo se actualizará el estado.</>
                    }
                  </p>
                )}
                <div className="flex gap-2 flex-wrap">
                {ordenDetalle.estado === 'BORRADOR' && (
                  <>
                    <button type="button" onClick={() => navigate(`/ordenes-compra/editar/${ordenDetalle.id_orden_compra}`)} className="min-h-[44px] px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 active:bg-slate-100 text-sm flex items-center gap-2 touch-manipulation">✏️ Editar</button>
                    <button type="button" onClick={() => enviarOrden(ordenDetalle)} disabled={enviandoOrden} className="min-h-[44px] px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 text-sm disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2 touch-manipulation">{enviandoOrden ? <span className="animate-pulse">Enviando...</span> : 'Enviar orden'}</button>
                  </>
                )}
                {ordenDetalle.estado === 'ENVIADA' && (
                  <button type="button" onClick={() => autorizarOrden(ordenDetalle)} disabled={enviandoAutorizar || !ordenDetalle.comprobante_url} title={!ordenDetalle.comprobante_url ? 'Primero sube la cotización formal del proveedor' : ''} className="min-h-[44px] px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 active:bg-indigo-800 text-sm disabled:opacity-60 disabled:cursor-not-allowed touch-manipulation">{enviandoAutorizar ? <span className="animate-pulse">Autorizando...</span> : 'Autorizar orden'}</button>
                )}
                {(ordenDetalle.estado === 'AUTORIZADA' || ordenDetalle.estado === 'RECIBIDA_PARCIAL') && (
                  <button type="button" onClick={abrirRecibirConAlerta} disabled={ordenDetalle.estado === 'AUTORIZADA' && !ordenDetalle.fecha_estimada_entrega} title={ordenDetalle.estado === 'AUTORIZADA' && !ordenDetalle.fecha_estimada_entrega ? 'Guarde la fecha promesa antes de recibir' : ''} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm disabled:opacity-60 disabled:cursor-not-allowed touch-manipulation">Recibir mercancía</button>
                )}
                {(ordenDetalle.estado === 'RECIBIDA' || ordenDetalle.estado === 'RECIBIDA_PARCIAL') && (ordenDetalle.saldo_pendiente ?? 0) > 0 && (
                  <button type="button" onClick={abrirPagar} className="min-h-[44px] px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 active:bg-amber-800 text-sm touch-manipulation">Registrar pago</button>
                )}
                {(ordenDetalle.estado === 'BORRADOR' || ordenDetalle.estado === 'AUTORIZADA' || ordenDetalle.estado === 'ENVIADA') && user?.rol === 'ADMIN' && (
                  <button type="button" onClick={abrirCancelar} className="min-h-[44px] px-4 py-2 border border-red-500 text-red-600 rounded-lg hover:bg-red-50 active:bg-red-100 text-sm touch-manipulation">Cancelar orden</button>
                )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-slate-500">No se pudo cargar la orden</p>
        )}
      </Modal>

      {/* Modal recibir */}
      <Modal titulo="Recibir mercancía" abierto={modalRecibir} onCerrar={() => setModalRecibir(false)} size="lg">
        <form onSubmit={recibirMercancia} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Ref. proveedor</label>
            <input type="text" value={formRecibir.referencia_proveedor} onChange={(e) => setFormRecibir({ ...formRecibir, referencia_proveedor: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" placeholder="Nº factura, remisión..." />
          </div>
          <div className="space-y-2">
            <div className="flex gap-2 items-center text-sm font-medium text-slate-600 pb-1 border-b border-slate-200">
              <span className="flex-1">Repuesto</span>
              <span className="w-20 text-center">Cant.</span>
              <span className="w-24 text-center">Precio real</span>
            </div>
            {formRecibir.items.map((it, idx) => {
              const det = ordenDetalle?.detalles?.find((d) => d.id === it.id_detalle)
              return (
                <div key={idx} className="flex gap-2 items-center flex-wrap">
                  <span className="flex-1 text-sm min-w-0">{det?.nombre_repuesto}</span>
                  <input type="number" min={0} max={det?.cantidad_pendiente ?? 999} value={it.cantidad_recibida} onChange={(e) => setFormRecibir((f) => ({ ...f, items: f.items.map((x, i) => (i === idx ? { ...x, cantidad_recibida: parseInt(e.target.value) || 0 } : x)) }))} className="w-20 min-h-[44px] px-2 py-2 border rounded text-base sm:text-sm touch-manipulation" aria-label="Cantidad recibida" />
                  <input type="number" step={0.01} min={0.01} placeholder="Oblig." value={it.precio_unitario_real ?? ''} onChange={(e) => setFormRecibir((f) => ({ ...f, items: f.items.map((x, i) => (i === idx ? { ...x, precio_unitario_real: e.target.value === '' ? null : parseFloat(e.target.value) } : x)) }))} className="w-24 min-h-[44px] px-2 py-2 border rounded text-base sm:text-sm touch-manipulation" aria-label="Precio real" title="Precio real obligatorio (mayor a 0)" />
                </div>
              )
            })}
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalRecibir(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviandoRecibir || formRecibir.items.some((it) => (it.cantidad_recibida || 0) > 0 && ((it.precio_unitario_real ?? 0) <= 0))} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 disabled:opacity-50 touch-manipulation">{enviandoRecibir ? 'Guardando...' : 'Recibir'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal pagar */}
      <Modal titulo="Registrar pago" abierto={modalPagar} onCerrar={() => setModalPagar(false)}>
        <form onSubmit={registrarPago} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step={0.01} min={0} value={formPago.monto} onChange={(e) => setFormPago({ ...formPago, monto: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Método</label>
            <select value={formPago.metodo} onChange={(e) => setFormPago({ ...formPago, metodo: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation">
              <option value="EFECTIVO">Efectivo</option>
              <option value="TARJETA">Tarjeta</option>
              <option value="TRANSFERENCIA">Transferencia</option>
              <option value="CHEQUE">Cheque</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Referencia</label>
            <input type="text" value={formPago.referencia} onChange={(e) => setFormPago({ ...formPago, referencia: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border rounded-lg touch-manipulation" />
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => setModalPagar(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviandoPago} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviandoPago ? 'Guardando...' : 'Registrar'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal cancelar */}
      <Modal titulo={ordenDetalle ? `Cancelar orden ${ordenDetalle.numero}` : 'Cancelar orden'} abierto={modalCancelar} onCerrar={() => setModalCancelar(false)}>
        <form onSubmit={cancelarOrden} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motivo (mín. 5 caracteres) *</label>
            <textarea value={motivoCancelar} onChange={(e) => setMotivoCancelar(e.target.value)} rows={3} className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border rounded-lg touch-manipulation" required minLength={5} />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Evidencia/imagen (opcional)</label>
            {evidenciaCancelar ? (
              <div className="flex items-center gap-2 flex-wrap">
                <a href={evidenciaCancelar} target="_blank" rel="noopener noreferrer" className="min-h-[44px] inline-flex items-center text-primary-600 hover:underline text-sm touch-manipulation">Ver archivo</a>
                <button type="button" onClick={() => setEvidenciaCancelar('')} className="min-h-[44px] px-2 py-2 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation">Eliminar</button>
              </div>
            ) : (
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <span className="min-h-[44px] px-4 py-2 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 border border-slate-300 rounded-lg text-sm text-slate-700 disabled:opacity-50 inline-flex items-center touch-manipulation">
                  {subiendoEvidenciaCancelar ? 'Subiendo...' : '📎 Adjuntar evidencia'}
                </span>
                <input type="file" accept={ALLOWED_EXT.join(',')} className="hidden" onChange={subirEvidenciaCancelar} disabled={subiendoEvidenciaCancelar} />
              </label>
            )}
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => setModalCancelar(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cerrar</button>
            <button type="submit" disabled={enviandoCancelar || motivoCancelar.trim().length < 5} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">{enviandoCancelar ? 'Cancelando...' : 'Cancelar orden'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
