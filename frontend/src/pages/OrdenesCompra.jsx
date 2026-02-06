import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { useApiQuery, useInvalidateQueries } from '../hooks/useApi'

const LIMIT = 20
const ALLOWED_EXT = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf']

const labelEstado = (est) => {
  const m = { BORRADOR: 'Borrador', AUTORIZADA: 'Autorizada', ENVIADA: 'Enviada (Iniciada)', RECIBIDA_PARCIAL: 'Recibida parcial', RECIBIDA: 'Recibida', CANCELADA: 'Cancelada' }
  return m[est] || est
}

export default function OrdenesCompra() {
  const { user } = useAuth()
  const invalidate = useInvalidateQueries()
  const [pagina, setPagina] = useState(1)
  const [filtroEstado, setFiltroEstado] = useState('')
  const [filtroProveedor, setFiltroProveedor] = useState('')
  const [searchParams] = useSearchParams()
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

  const puedeEditarComprobanteYFecha = ordenDetalle && ['BORRADOR', 'AUTORIZADA', 'ENVIADA', 'RECIBIDA_PARCIAL'].includes(ordenDetalle.estado)

  const subirComprobante = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !ordenDetalle || !puedeEditarComprobanteYFecha) return
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
      .map((it) => ({ id_detalle: it.id_detalle, cantidad_recibida: parseInt(it.cantidad_recibida) || 0, precio_unitario_real: it.precio_unitario_real != null ? parseFloat(it.precio_unitario_real) : null }))
      .filter((it) => it.cantidad_recibida > 0)
    if (itemsEnviar.length === 0) {
      alert('Indica al menos una cantidad recibida mayor a 0')
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
    if (!ordenDetalle || !formPago.monto || parseFloat(formPago.monto) <= 0) return
    setEnviandoPago(true)
    try {
      await api.post(`/ordenes-compra/${ordenDetalle.id_orden_compra}/pagar`, {
        monto: parseFloat(formPago.monto),
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
    setModalCancelar(true)
  }

  const cancelarOrden = async (e) => {
    e.preventDefault()
    if (!ordenDetalle || motivoCancelar.trim().length < 5) {
      alert('El motivo debe tener al menos 5 caracteres')
      return
    }
    setEnviandoCancelar(true)
    try {
      await api.post(`/ordenes-compra/${ordenDetalle.id_orden_compra}/cancelar`, { motivo: motivoCancelar.trim() })
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
    <div>
      {hayVencidas && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-amber-700 font-medium">⚠️ {alertasOC.ordenes_vencidas} orden(es) vencida(s) pendiente(s) de recibir</span>
          </div>
          <button
            onClick={() => setSoloPendientesRecibir(true)}
            className="text-sm px-3 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700"
          >
            Ver pendientes de recibir
          </button>
        </div>
      )}
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Órdenes de compra</h1>
        <div className="flex gap-2 flex-wrap items-center">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={soloPendientesRecibir}
              onChange={(e) => { setSoloPendientesRecibir(e.target.checked); setFiltroEstado(''); setPagina(1) }}
              className="rounded"
            />
            <span className="text-slate-600">Pendientes de recibir</span>
          </label>
          <select
            value={filtroEstado}
            onChange={(e) => { setFiltroEstado(e.target.value); setSoloPendientesRecibir(false); setPagina(1) }}
            disabled={soloPendientesRecibir}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50"
          >
            <option value="">Todos los estados</option>
            {estados.map((e) => (
              <option key={e.valor} value={e.valor}>{e.valor}</option>
            ))}
          </select>
          <select
            value={filtroProveedor}
            onChange={(e) => { setFiltroProveedor(e.target.value); setPagina(1) }}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">Todos los proveedores</option>
            {proveedores.map((p) => (
              <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
            ))}
          </select>
          <Link to="/cuentas-por-pagar" className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 text-sm">
            Cuentas por pagar
          </Link>
          {puedeGestionar && (
            <Link to="/ordenes-compra/nueva" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
              Nueva orden
            </Link>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Número</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Proveedor</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Estado</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Total est.</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha est. llegada</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {ordenes.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">No hay órdenes de compra</td>
                </tr>
              ) : (
                ordenes.map((o) => (
                  <tr key={o.id_orden_compra} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm font-medium text-slate-800">{o.numero}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{o.nombre_proveedor}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${colorEstado(o.estado)}`}>{labelEstado(o.estado)}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right">${(o.total_estimado ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td>
                    <td className="px-4 py-3 text-sm text-slate-600">{o.fecha ? new Date(o.fecha).toLocaleDateString('es-MX') : '-'}</td>
                    <td className="px-4 py-3 text-sm">
                      {o.fecha_estimada_entrega ? (
                        <span className={o.vencida ? 'text-red-600 font-medium' : ''}>
                          {new Date(o.fecha_estimada_entrega).toLocaleDateString('es-MX')}
                          {o.vencida && <span className="ml-1 text-xs">(vencida)</span>}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="inline-flex gap-2 justify-end">
                        <button onClick={() => abrirDetalle(o)} className="text-sm text-primary-600 hover:text-primary-700">Ver</button>
                        {user?.rol === 'ADMIN' && ['BORRADOR', 'AUTORIZADA', 'ENVIADA'].includes(o.estado) && (
                          <button
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
                                setModalCancelar(true)
                              } catch {
                                alert('Error al cargar la orden.')
                              }
                            }}
                            className="text-sm text-red-600 hover:text-red-700"
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
        <div className="mt-4 flex justify-center sm:justify-end gap-3 items-center flex-wrap p-3 bg-slate-50 rounded-lg">
          <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-5 py-2.5 bg-primary-600 text-white rounded-lg disabled:opacity-50">
            ← Anterior
          </button>
          <span className="text-sm font-medium text-slate-700">
            Página {pagina} de {totalPaginas} ({total} registros)
          </span>
          <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-5 py-2.5 bg-primary-600 text-white rounded-lg disabled:opacity-50">
            Siguiente →
          </button>
        </div>
      )}

      {/* Modal detalle */}
      <Modal titulo={ordenDetalle ? `Orden ${ordenDetalle.numero}` : 'Detalle'} abierto={modalDetalle} onCerrar={() => { setModalDetalle(false); setOrdenDetalle(null) }} size="xl">
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
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div><span className="text-slate-500">Proveedor:</span> {ordenDetalle.nombre_proveedor}</div>
              <div><span className="text-slate-500">Estado:</span> <span className={`px-2 py-0.5 rounded text-xs ${colorEstado(ordenDetalle.estado)}`}>{labelEstado(ordenDetalle.estado)}</span></div>
              <div><span className="text-slate-500">Total:</span> ${(ordenDetalle.total_estimado ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</div>
              <div><span className="text-slate-500">Fecha:</span> {ordenDetalle.fecha ? new Date(ordenDetalle.fecha).toLocaleDateString('es-MX') : '-'}</div>
              <div className="col-span-2 sm:col-span-4">
                <span className="text-slate-500">Fecha estimada de llegada: </span>
                {puedeEditarComprobanteYFecha && puedeGestionar ? (
                  <span className="inline-flex gap-2 items-center">
                    <input
                      type="date"
                      value={editFechaEst}
                      onChange={(e) => setEditFechaEst(e.target.value)}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <button type="button" onClick={guardarFechaEstimada} className="text-primary-600 hover:underline text-sm">Guardar</button>
                  </span>
                ) : (
                  ordenDetalle.fecha_estimada_entrega ? new Date(ordenDetalle.fecha_estimada_entrega).toLocaleDateString('es-MX') : '-'
                )}
              </div>
            </div>
            {ordenDetalle.observaciones && <p className="text-sm text-slate-600">{ordenDetalle.observaciones}</p>}
            {ordenDetalle.estado === 'BORRADOR' && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600">
                <strong>Flujo:</strong> Sube la cotización formal del proveedor, revisa los datos y luego haz clic en <strong>Autorizar orden</strong>. Después podrás enviar la orden al proveedor.
              </div>
            )}
            <div className="text-sm flex items-center gap-3 flex-wrap">
              <span className="text-slate-500">{ordenDetalle.estado === 'BORRADOR' ? 'Cotización formal:' : 'Comprobante:'} </span>
              {ordenDetalle.comprobante_url ? (
                <>
                  <a href={ordenDetalle.comprobante_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">Ver archivo</a>
                  {puedeEditarComprobanteYFecha && puedeGestionar && (
                    <label className="text-slate-600 hover:text-primary-600 cursor-pointer text-sm">
                      {subiendoComprobante ? 'Subiendo...' : 'Reemplazar'}
                      <input type="file" accept={ALLOWED_EXT.join(',')} className="hidden" onChange={subirComprobante} disabled={subiendoComprobante} />
                    </label>
                  )}
                </>
              ) : puedeEditarComprobanteYFecha && puedeGestionar ? (
                <label className="px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer text-sm font-medium">
                  {subiendoComprobante ? 'Subiendo...' : (ordenDetalle.estado === 'BORRADOR' ? '📎 Subir cotización formal' : '📎 Adjuntar comprobante')}
                  <input type="file" accept={ALLOWED_EXT.join(',')} className="hidden" onChange={subirComprobante} disabled={subiendoComprobante} />
                </label>
              ) : (
                <span className="text-slate-400">Sin comprobante</span>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-2">Repuesto</th><th className="text-right">Solicitado</th><th className="text-right">Recibido</th><th className="text-right">Pendiente</th><th className="text-right">Precio est.</th></tr></thead>
                <tbody>
                  {(ordenDetalle.detalles || []).map((d) => (
                    <tr key={d.id} className="border-b">
                      <td className="py-2">{d.nombre_repuesto || d.codigo_repuesto}</td>
                      <td className="text-right">{d.cantidad_solicitada}</td>
                      <td className="text-right">{d.cantidad_recibida ?? 0}</td>
                      <td className="text-right">{d.cantidad_pendiente ?? (d.cantidad_solicitada - (d.cantidad_recibida || 0))}</td>
                      <td className="text-right">${(d.precio_unitario_estimado ?? 0).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {puedeGestionar && (
              <div className="flex flex-col gap-2 pt-2 border-t">
                {(ordenDetalle.estado === 'BORRADOR' || ordenDetalle.estado === 'AUTORIZADA') && (
                  <p className="text-sm text-slate-600">
                    {ordenDetalle.email_proveedor
                      ? <>Al enviar, se enviará un email a <strong>{ordenDetalle.nombre_proveedor}</strong> ({ordenDetalle.email_proveedor})</>
                      : <>El proveedor <strong>{ordenDetalle.nombre_proveedor}</strong> no tiene email configurado. Solo se actualizará el estado.</>
                    }
                  </p>
                )}
                <div className="flex gap-2 flex-wrap">
                {ordenDetalle.estado === 'BORRADOR' && (
                  <>
                    <button onClick={() => autorizarOrden(ordenDetalle)} disabled={enviandoAutorizar || enviandoOrden} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2">
                      {enviandoAutorizar ? <span className="animate-pulse">Autorizando...</span> : 'Autorizar orden'}
                    </button>
                    <button onClick={() => enviarOrden(ordenDetalle)} disabled={enviandoOrden || enviandoAutorizar} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2">
                      {enviandoOrden ? <span className="animate-pulse">Enviando orden y notificando al proveedor...</span> : 'Enviar orden'}
                    </button>
                  </>
                )}
                {ordenDetalle.estado === 'AUTORIZADA' && (
                  <button onClick={() => enviarOrden(ordenDetalle)} disabled={enviandoOrden} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2">
                    {enviandoOrden ? <span className="animate-pulse">Enviando orden y notificando al proveedor...</span> : 'Enviar orden'}
                  </button>
                )}
                {(ordenDetalle.estado === 'ENVIADA' || ordenDetalle.estado === 'RECIBIDA_PARCIAL') && (
                  <button onClick={abrirRecibir} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">Recibir mercancía</button>
                )}
                {(ordenDetalle.estado === 'RECIBIDA' || ordenDetalle.estado === 'RECIBIDA_PARCIAL') && (
                  <button onClick={abrirPagar} className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm">Registrar pago</button>
                )}
                {(ordenDetalle.estado === 'BORRADOR' || ordenDetalle.estado === 'AUTORIZADA' || ordenDetalle.estado === 'ENVIADA') && user?.rol === 'ADMIN' && (
                  <button onClick={abrirCancelar} className="px-4 py-2 border border-red-500 text-red-600 rounded-lg hover:bg-red-50 text-sm">Cancelar orden</button>
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
            <input type="text" value={formRecibir.referencia_proveedor} onChange={(e) => setFormRecibir({ ...formRecibir, referencia_proveedor: e.target.value })} className="w-full px-4 py-2 border rounded-lg" placeholder="Nº factura, remisión..." />
          </div>
          <div className="space-y-2">
            {formRecibir.items.map((it, idx) => {
              const det = ordenDetalle?.detalles?.find((d) => d.id === it.id_detalle)
              return (
                <div key={idx} className="flex gap-2 items-center">
                  <span className="flex-1 text-sm">{det?.nombre_repuesto}</span>
                  <input type="number" min={0} max={det?.cantidad_pendiente ?? 999} value={it.cantidad_recibida} onChange={(e) => setFormRecibir((f) => ({ ...f, items: f.items.map((x, i) => (i === idx ? { ...x, cantidad_recibida: parseInt(e.target.value) || 0 } : x)) }))} className="w-20 px-2 py-1.5 border rounded text-sm" />
                  <input type="number" step={0.01} min={0} placeholder="Precio real" value={it.precio_unitario_real ?? ''} onChange={(e) => setFormRecibir((f) => ({ ...f, items: f.items.map((x, i) => (i === idx ? { ...x, precio_unitario_real: e.target.value === '' ? null : parseFloat(e.target.value) } : x)) }))} className="w-24 px-2 py-1.5 border rounded text-sm" />
                </div>
              )
            })}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalRecibir(false)} className="px-4 py-2 border rounded-lg">Cancelar</button>
            <button type="submit" disabled={enviandoRecibir} className="px-4 py-2 bg-green-600 text-white rounded-lg disabled:opacity-50">{enviandoRecibir ? 'Guardando...' : 'Recibir'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal pagar */}
      <Modal titulo="Registrar pago" abierto={modalPagar} onCerrar={() => setModalPagar(false)}>
        <form onSubmit={registrarPago} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto *</label>
            <input type="number" step={0.01} min={0} value={formPago.monto} onChange={(e) => setFormPago({ ...formPago, monto: e.target.value })} className="w-full px-4 py-2 border rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Método</label>
            <select value={formPago.metodo} onChange={(e) => setFormPago({ ...formPago, metodo: e.target.value })} className="w-full px-4 py-2 border rounded-lg">
              <option value="EFECTIVO">Efectivo</option>
              <option value="TARJETA">Tarjeta</option>
              <option value="TRANSFERENCIA">Transferencia</option>
              <option value="CHEQUE">Cheque</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Referencia</label>
            <input type="text" value={formPago.referencia} onChange={(e) => setFormPago({ ...formPago, referencia: e.target.value })} className="w-full px-4 py-2 border rounded-lg" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalPagar(false)} className="px-4 py-2 border rounded-lg">Cancelar</button>
            <button type="submit" disabled={enviandoPago} className="px-4 py-2 bg-primary-600 text-white rounded-lg disabled:opacity-50">{enviandoPago ? 'Guardando...' : 'Registrar'}</button>
          </div>
        </form>
      </Modal>

      {/* Modal cancelar */}
      <Modal titulo={ordenDetalle ? `Cancelar orden ${ordenDetalle.numero}` : 'Cancelar orden'} abierto={modalCancelar} onCerrar={() => setModalCancelar(false)}>
        <form onSubmit={cancelarOrden} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motivo (mín. 5 caracteres) *</label>
            <textarea value={motivoCancelar} onChange={(e) => setMotivoCancelar(e.target.value)} rows={3} className="w-full px-4 py-2 border rounded-lg" required minLength={5} />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCancelar(false)} className="px-4 py-2 border rounded-lg">Cerrar</button>
            <button type="submit" disabled={enviandoCancelar || motivoCancelar.trim().length < 5} className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">{enviandoCancelar ? 'Cancelando...' : 'Cancelar orden'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
