import { useState, useEffect, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../services/api'
import PageHeader from '../components/PageHeader'
import PageLoading from '../components/PageLoading'
import { normalizeDetail, showError, showSuccess } from '../utils/toast'
import { useAuth } from '../context/AuthContext'

function fmtMoney(v) {
  if (v == null || v === '') return '—'
  const n = Number(v)
  if (Number.isNaN(n)) return String(v)
  return n.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function CotizacionRefaccionDetalle() {
  const { id } = useParams()
  const { user } = useAuth()
  const puedeAceptarCliente = ['ADMIN', 'CAJA', 'EMPLEADO'].includes(user?.rol)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cot, setCot] = useState(null)

  const [formCab, setFormCab] = useState({
    tc_referencia_usd_mxn: '',
    margen_objetivo_pct: '',
    notas_generales: '',
    id_vehiculo: '',
    id_orden_trabajo: '',
  })

  const [nuevaLinea, setNuevaLinea] = useState({ descripcion: '', cantidad: '1', posicion_lado: '' })
  const [opcionDraft, setOpcionDraft] = useState({}) // lineId -> form fields

  const [comentario, setComentario] = useState('')
  const [compraModal, setCompraModal] = useState(false)
  const [compraForm, setCompraForm] = useState({
    id_linea: '',
    id_opcion: '',
    monto_pagado: '',
    moneda: 'MXN',
    tipo_cambio_aplicado: '',
    metodo: 'PAYPAL',
    notas: '',
  })

  const cargar = useCallback(async () => {
    setError('')
    try {
      const r = await api.get(`/cotizaciones-refaccion/${id}`)
      const d = r.data
      setCot(d)
      setFormCab({
        tc_referencia_usd_mxn: d.tc_referencia_usd_mxn != null ? String(d.tc_referencia_usd_mxn) : '',
        margen_objetivo_pct: d.margen_objetivo_pct != null ? String(d.margen_objetivo_pct) : '',
        notas_generales: d.notas_generales || '',
        id_vehiculo: d.id_vehiculo != null ? String(d.id_vehiculo) : '',
        id_orden_trabajo: d.id_orden_trabajo != null ? String(d.id_orden_trabajo) : '',
      })
    } catch (e) {
      setError(normalizeDetail(e.response?.data?.detail) || 'No se pudo cargar')
      setCot(null)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    cargar()
  }, [cargar])

  const guardarCabecera = async () => {
    try {
      await api.put(`/cotizaciones-refaccion/${id}`, {
        tc_referencia_usd_mxn: formCab.tc_referencia_usd_mxn ? parseFloat(formCab.tc_referencia_usd_mxn) : null,
        margen_objetivo_pct: formCab.margen_objetivo_pct ? parseFloat(formCab.margen_objetivo_pct) : null,
        notas_generales: formCab.notas_generales?.trim() || null,
        id_vehiculo: formCab.id_vehiculo ? parseInt(formCab.id_vehiculo, 10) : null,
        id_orden_trabajo: formCab.id_orden_trabajo ? parseInt(formCab.id_orden_trabajo, 10) : null,
      })
      showSuccess('Guardado')
      cargar()
    } catch (e) {
      showError(normalizeDetail(e.response?.data?.detail) || 'Error al guardar')
    }
  }

  const agregarLinea = async (e) => {
    e.preventDefault()
    if (!nuevaLinea.descripcion?.trim()) return
    try {
      await api.post(`/cotizaciones-refaccion/${id}/lineas`, {
        descripcion: nuevaLinea.descripcion.trim(),
        cantidad: parseFloat(nuevaLinea.cantidad) || 1,
        posicion_lado: nuevaLinea.posicion_lado?.trim() || null,
      })
      setNuevaLinea({ descripcion: '', cantidad: '1', posicion_lado: '' })
      showSuccess('Línea agregada')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const agregarOpcion = async (lineaId) => {
    const f = opcionDraft[lineaId] || {}
    if (!f.origen_nombre?.trim()) {
      showError('Indique origen (ej. RockAuto)')
      return
    }
    try {
      await api.post(`/cotizaciones-refaccion/lineas/${lineaId}/opciones`, {
        origen_nombre: f.origen_nombre.trim(),
        url_compra: f.url_compra?.trim() || null,
        moneda: f.moneda || 'MXN',
        monto_unitario: parseFloat(f.monto_unitario) || 0,
        tipo_cambio_a_mxn: f.tipo_cambio_a_mxn ? parseFloat(f.tipo_cambio_a_mxn) : null,
        otros_costos_mxn: f.otros_costos_mxn ? parseFloat(f.otros_costos_mxn) : 0,
        dias_estimados_entrega: f.dias_estimados_entrega ? parseInt(f.dias_estimados_entrega, 10) : null,
        notas: f.notas?.trim() || null,
        es_preferida: !!f.es_preferida,
      })
      setOpcionDraft((d) => ({ ...d, [lineaId]: {} }))
      showSuccess('Opción guardada')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const marcarPreferida = async (opcionId) => {
    try {
      await api.post(`/cotizaciones-refaccion/opciones/${opcionId}/marcar-preferida`)
      showSuccess('Opción preferida')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const eliminarOpcion = async (opcionId) => {
    if (!window.confirm('¿Eliminar esta opción?')) return
    try {
      await api.delete(`/cotizaciones-refaccion/opciones/${opcionId}`)
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const eliminarLinea = async (lineaId) => {
    if (!window.confirm('¿Eliminar línea y sus opciones?')) return
    try {
      await api.delete(`/cotizaciones-refaccion/lineas/${lineaId}`)
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const enviar = async () => {
    try {
      await api.post(`/cotizaciones-refaccion/${id}/enviar`)
      showSuccess('Cotización enviada (congelada)')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const aceptarCliente = async () => {
    try {
      await api.post(`/cotizaciones-refaccion/${id}/aceptar-cliente`)
      showSuccess('Cliente marcado como aceptado')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const cancelarCot = async () => {
    if (!window.confirm('¿Cancelar esta cotización?')) return
    try {
      await api.post(`/cotizaciones-refaccion/${id}/cancelar`)
      showSuccess('Cancelada')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const agregarComentario = async () => {
    if (!comentario.trim()) return
    try {
      await api.post(`/cotizaciones-refaccion/${id}/comentarios`, { mensaje: comentario.trim() })
      setComentario('')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const registrarCompra = async (e) => {
    e.preventDefault()
    try {
      await api.post(`/cotizaciones-refaccion/${id}/registrar-compra`, {
        id_linea: compraForm.id_linea ? parseInt(compraForm.id_linea, 10) : null,
        id_opcion: compraForm.id_opcion ? parseInt(compraForm.id_opcion, 10) : null,
        monto_pagado: parseFloat(compraForm.monto_pagado),
        moneda: compraForm.moneda,
        tipo_cambio_aplicado: compraForm.tipo_cambio_aplicado ? parseFloat(compraForm.tipo_cambio_aplicado) : null,
        metodo: compraForm.metodo,
        notas: compraForm.notas?.trim() || null,
      })
      setCompraModal(false)
      showSuccess('Compra registrada')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const marcarRecibida = async () => {
    try {
      await api.post(`/cotizaciones-refaccion/${id}/marcar-recibida`)
      showSuccess('Marcada como recibida')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  const marcarEntregada = async () => {
    try {
      await api.post(`/cotizaciones-refaccion/${id}/marcar-entregada`)
      showSuccess('Entregada')
      cargar()
    } catch (e2) {
      showError(normalizeDetail(e2.response?.data?.detail) || 'Error')
    }
  }

  if (loading) return <PageLoading mensaje="Cargando cotización..." />
  if (error || !cot)
    return (
      <div className="p-6">
        <p className="text-red-600">{error || 'No encontrada'}</p>
        <Link to="/cotizaciones-refaccion" className="text-orange-600 underline mt-2 inline-block">
          Volver al listado
        </Link>
      </div>
    )

  const borrador = cot.estado === 'BORRADOR'
  const tot = cot.totales || {}

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <PageHeader
        title={cot.numero}
        subtitle={`Cliente: ${cot.cliente_nombre || '# ' + cot.id_cliente}${cot.vehiculo_texto ? ` · ${cot.vehiculo_texto}` : ''}`}
      >
        <button
          type="button"
          className="min-h-[44px] px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-medium shadow-sm hover:bg-emerald-700"
          onClick={async () => {
            try {
              const res = await api.get(`/cotizaciones-refaccion/${id}/pdf`, { responseType: 'blob' })
              const blob = new Blob([res.data], { type: 'application/pdf' })
              const url = window.URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.setAttribute('download', `cotizacion-refaccion-${cot.numero || id}.pdf`)
              document.body.appendChild(link)
              link.click()
              link.remove()
              window.URL.revokeObjectURL(url)
              showSuccess('PDF descargado')
            } catch (e) {
              showError(normalizeDetail(e.response?.data?.detail) || 'No se pudo generar el PDF')
            }
          }}
        >
          PDF cotización
        </button>
        <Link
          to="/cotizaciones-refaccion"
          className="min-h-[44px] px-4 py-2 rounded-xl border border-slate-300 text-sm font-medium text-slate-700"
        >
          ← Listado
        </Link>
      </PageHeader>

      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-medium">{cot.estado}</span>
        {cot.congelada && <span className="text-xs text-slate-500">Congelada</span>}
      </div>

      {tot.precio_sugerido_total != null && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-white border rounded-xl p-4">
            <p className="text-xs text-slate-500">Precio sugerido total</p>
            <p className="text-lg font-semibold text-slate-800">${fmtMoney(tot.precio_sugerido_total)}</p>
          </div>
          <div className="bg-white border rounded-xl p-4">
            <p className="text-xs text-slate-500">Costo estimado (MXN)</p>
            <p className="text-lg font-semibold text-slate-800">${fmtMoney(tot.costo_estimado_total_mxn)}</p>
          </div>
          <div className="bg-white border rounded-xl p-4">
            <p className="text-xs text-slate-500">Ganancia estimada</p>
            <p className="text-lg font-semibold text-emerald-700">${fmtMoney(tot.ganancia_estimada_total)}</p>
          </div>
        </div>
      )}

      {borrador && (
        <div className="bg-white border rounded-xl p-4 space-y-3">
          <h3 className="font-semibold text-slate-800">Datos de cotización</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-500">TC USD → MXN</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm mt-0.5"
                value={formCab.tc_referencia_usd_mxn}
                onChange={(e) => setFormCab((f) => ({ ...f, tc_referencia_usd_mxn: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Margen % objetivo</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm mt-0.5"
                value={formCab.margen_objetivo_pct}
                onChange={(e) => setFormCab((f) => ({ ...f, margen_objetivo_pct: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Id vehículo (opcional)</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm mt-0.5"
                value={formCab.id_vehiculo}
                onChange={(e) => setFormCab((f) => ({ ...f, id_vehiculo: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Id orden trabajo (opcional)</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm mt-0.5"
                value={formCab.id_orden_trabajo}
                onChange={(e) => setFormCab((f) => ({ ...f, id_orden_trabajo: e.target.value }))}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-500">Notas generales</label>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm mt-0.5"
              rows={2}
              value={formCab.notas_generales}
              onChange={(e) => setFormCab((f) => ({ ...f, notas_generales: e.target.value }))}
            />
          </div>
          <button type="button" onClick={guardarCabecera} className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm">
            Guardar cabecera
          </button>
        </div>
      )}

      <div className="bg-white border rounded-xl p-4 space-y-4">
        <h3 className="font-semibold text-slate-800">Líneas y opciones de compra</h3>
        {(cot.lineas || []).map((ln) => (
          <div key={ln.id} className="border border-slate-200 rounded-lg p-3 space-y-2">
            <div className="flex flex-wrap justify-between gap-2">
              <div>
                <span className="text-xs text-slate-500">Línea {ln.n_linea}</span>
                <p className="font-medium text-slate-800">{ln.descripcion}</p>
                <p className="text-sm text-slate-600">
                  Cant. {ln.cantidad}
                  {ln.posicion_lado ? ` · ${ln.posicion_lado}` : ''}
                </p>
              </div>
              {borrador && (
                <button type="button" className="text-xs text-red-600" onClick={() => eliminarLinea(ln.id)}>
                  Eliminar línea
                </button>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-slate-500 border-b">
                    <th className="py-1 pr-2">Origen</th>
                    <th className="py-1 pr-2">$</th>
                    <th className="py-1 pr-2">MXN u.</th>
                    <th className="py-1 pr-2">Sugerido</th>
                    <th className="py-1 pr-2">Días</th>
                    <th className="py-1 pr-2">Pref.</th>
                    <th className="py-1" />
                  </tr>
                </thead>
                <tbody>
                  {(ln.opciones || []).map((op) => (
                    <tr key={op.id} className="border-b border-slate-50">
                      <td className="py-1 pr-2">
                        <a
                          href={op.url_compra || '#'}
                          target="_blank"
                          rel="noreferrer"
                          className={op.url_compra ? 'text-orange-600 underline' : ''}
                        >
                          {op.origen_nombre}
                        </a>
                      </td>
                      <td className="py-1 pr-2">
                        {op.moneda} {fmtMoney(op.monto_unitario)}
                      </td>
                      <td className="py-1 pr-2">{op.costo_error ? <span className="text-red-600">{op.costo_error}</span> : fmtMoney(op.costo_unitario_mxn)}</td>
                      <td className="py-1 pr-2">{fmtMoney(op.precio_sugerido_linea)}</td>
                      <td className="py-1 pr-2">{op.dias_estimados_entrega ?? '—'}</td>
                      <td className="py-1 pr-2">{op.es_preferida ? '★' : ''}</td>
                      <td className="py-1">
                        {borrador && (
                          <span className="flex gap-1">
                            <button type="button" className="text-orange-600" onClick={() => marcarPreferida(op.id)}>
                              Preferida
                            </button>
                            <button type="button" className="text-red-600" onClick={() => eliminarOpcion(op.id)}>
                              ✕
                            </button>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {borrador && (
              <div className="bg-slate-50 rounded p-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <input
                  placeholder="Origen"
                  className="border rounded px-2 py-1"
                  value={opcionDraft[ln.id]?.origen_nombre || ''}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), origen_nombre: e.target.value },
                    }))
                  }
                />
                <select
                  className="border rounded px-2 py-1"
                  value={opcionDraft[ln.id]?.moneda || 'MXN'}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), moneda: e.target.value },
                    }))
                  }
                >
                  <option value="MXN">MXN</option>
                  <option value="USD">USD</option>
                </select>
                <input
                  placeholder="Monto u."
                  className="border rounded px-2 py-1"
                  value={opcionDraft[ln.id]?.monto_unitario || ''}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), monto_unitario: e.target.value },
                    }))
                  }
                />
                <input
                  placeholder="TC (si USD y override)"
                  className="border rounded px-2 py-1"
                  value={opcionDraft[ln.id]?.tipo_cambio_a_mxn || ''}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), tipo_cambio_a_mxn: e.target.value },
                    }))
                  }
                />
                <input
                  placeholder="Otros MXN (envío)"
                  className="border rounded px-2 py-1"
                  value={opcionDraft[ln.id]?.otros_costos_mxn || ''}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), otros_costos_mxn: e.target.value },
                    }))
                  }
                />
                <input
                  placeholder="Días ETA"
                  className="border rounded px-2 py-1"
                  value={opcionDraft[ln.id]?.dias_estimados_entrega || ''}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), dias_estimados_entrega: e.target.value },
                    }))
                  }
                />
                <input
                  placeholder="URL"
                  className="border rounded px-2 py-1 col-span-2"
                  value={opcionDraft[ln.id]?.url_compra || ''}
                  onChange={(e) =>
                    setOpcionDraft((d) => ({
                      ...d,
                      [ln.id]: { ...(d[ln.id] || {}), url_compra: e.target.value },
                    }))
                  }
                />
                <label className="flex items-center gap-1 col-span-2">
                  <input
                    type="checkbox"
                    checked={!!opcionDraft[ln.id]?.es_preferida}
                    onChange={(e) =>
                      setOpcionDraft((d) => ({
                        ...d,
                        [ln.id]: { ...(d[ln.id] || {}), es_preferida: e.target.checked },
                      }))
                    }
                  />
                  Preferida
                </label>
                <button
                  type="button"
                  className="col-span-2 sm:col-span-4 py-1 rounded bg-orange-500 text-white text-xs"
                  onClick={() => agregarOpcion(ln.id)}
                >
                  Agregar opción
                </button>
              </div>
            )}
          </div>
        ))}
        {borrador && (
          <form onSubmit={agregarLinea} className="flex flex-wrap gap-2 items-end border-t pt-3">
            <input
              placeholder="Descripción pieza"
              className="flex-1 min-w-[200px] border rounded-lg px-3 py-2 text-sm"
              value={nuevaLinea.descripcion}
              onChange={(e) => setNuevaLinea((n) => ({ ...n, descripcion: e.target.value }))}
            />
            <input
              placeholder="Cant."
              className="w-24 border rounded-lg px-3 py-2 text-sm"
              value={nuevaLinea.cantidad}
              onChange={(e) => setNuevaLinea((n) => ({ ...n, cantidad: e.target.value }))}
            />
            <input
              placeholder="Lado / posición"
              className="w-36 border rounded-lg px-3 py-2 text-sm"
              value={nuevaLinea.posicion_lado}
              onChange={(e) => setNuevaLinea((n) => ({ ...n, posicion_lado: e.target.value }))}
            />
            <button type="submit" className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm">
              + Línea
            </button>
          </form>
        )}
      </div>

      <div className="bg-white border rounded-xl p-4 space-y-2">
        <h3 className="font-semibold text-slate-800">Comentarios internos</h3>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {(cot.comentarios || []).map((c) => (
            <div key={c.id} className="text-sm border-b border-slate-100 pb-2">
              <span className="text-slate-500 text-xs">
                {c.usuario_nombre || 'Usuario'} — {c.creado_en ? new Date(c.creado_en).toLocaleString() : ''}
              </span>
              <p className="text-slate-800 whitespace-pre-wrap">{c.mensaje}</p>
            </div>
          ))}
        </div>
        {cot.estado !== 'CANCELADA' && (
          <div className="flex gap-2">
            <textarea
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
              rows={2}
              placeholder="Escribir comentario..."
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
            />
            <button type="button" onClick={agregarComentario} className="px-4 py-2 rounded-lg bg-slate-200 text-sm self-end">
              Enviar
            </button>
          </div>
        )}
      </div>

      {(cot.compras_ejecutadas || []).length > 0 && (
        <div className="bg-white border rounded-xl p-4">
          <h3 className="font-semibold text-slate-800 mb-2">Compras registradas</h3>
          <ul className="text-sm space-y-1">
            {cot.compras_ejecutadas.map((p) => (
              <li key={p.id}>
                {p.metodo} {p.moneda} {fmtMoney(p.monto_pagado)}
                {p.fecha_pago ? ` · ${new Date(p.fecha_pago).toLocaleString()}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {borrador && (
          <>
            <button type="button" className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm" onClick={enviar}>
              Enviar cotización
            </button>
            <button type="button" className="px-4 py-2 rounded-xl border border-red-300 text-red-700 text-sm" onClick={cancelarCot}>
              Cancelar
            </button>
          </>
        )}
        {cot.estado === 'ENVIADA' && puedeAceptarCliente && (
          <button type="button" className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm" onClick={aceptarCliente}>
            Cliente aceptó
          </button>
        )}
        {(cot.estado === 'ACEPTADA_CLIENTE' || cot.estado === 'EN_COMPRA') && (
          <button type="button" className="px-4 py-2 rounded-xl bg-primary-600 text-white text-sm" onClick={() => setCompraModal(true)}>
            Registrar compra
          </button>
        )}
        {cot.estado === 'EN_COMPRA' && (
          <button type="button" className="px-4 py-2 rounded-xl bg-slate-700 text-white text-sm" onClick={marcarRecibida}>
            Marcar recibida en taller
          </button>
        )}
        {cot.estado === 'RECIBIDA' && (
          <button type="button" className="px-4 py-2 rounded-xl bg-slate-700 text-white text-sm" onClick={marcarEntregada}>
            Marcar entregada
          </button>
        )}
        {cot.estado !== 'BORRADOR' && cot.estado !== 'ENTREGADA' && cot.estado !== 'CANCELADA' && (
          <button type="button" className="px-4 py-2 rounded-xl border border-red-300 text-red-700 text-sm" onClick={cancelarCot}>
            Cancelar
          </button>
        )}
      </div>

      {compraModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl space-y-3">
            <h3 className="font-semibold">Registrar compra (PayPal / tarjeta / …)</h3>
            <form onSubmit={registrarCompra} className="space-y-2 text-sm">
              <input
                placeholder="Id línea (opcional)"
                className="w-full border rounded px-3 py-2"
                value={compraForm.id_linea}
                onChange={(e) => setCompraForm((f) => ({ ...f, id_linea: e.target.value }))}
              />
              <input
                placeholder="Id opción (opcional)"
                className="w-full border rounded px-3 py-2"
                value={compraForm.id_opcion}
                onChange={(e) => setCompraForm((f) => ({ ...f, id_opcion: e.target.value }))}
              />
              <input
                required
                placeholder="Monto pagado *"
                className="w-full border rounded px-3 py-2"
                value={compraForm.monto_pagado}
                onChange={(e) => setCompraForm((f) => ({ ...f, monto_pagado: e.target.value }))}
              />
              <select
                className="w-full border rounded px-3 py-2"
                value={compraForm.moneda}
                onChange={(e) => setCompraForm((f) => ({ ...f, moneda: e.target.value }))}
              >
                <option value="MXN">MXN</option>
                <option value="USD">USD</option>
              </select>
              <input
                placeholder="TC aplicado (opcional)"
                className="w-full border rounded px-3 py-2"
                value={compraForm.tipo_cambio_aplicado}
                onChange={(e) => setCompraForm((f) => ({ ...f, tipo_cambio_aplicado: e.target.value }))}
              />
              <select
                className="w-full border rounded px-3 py-2"
                value={compraForm.metodo}
                onChange={(e) => setCompraForm((f) => ({ ...f, metodo: e.target.value }))}
              >
                <option value="PAYPAL">PAYPAL</option>
                <option value="TARJETA">TARJETA</option>
                <option value="TRANSFERENCIA">TRANSFERENCIA</option>
                <option value="OTRO">OTRO</option>
              </select>
              <textarea
                placeholder="Notas"
                className="w-full border rounded px-3 py-2"
                rows={2}
                value={compraForm.notas}
                onChange={(e) => setCompraForm((f) => ({ ...f, notas: e.target.value }))}
              />
              <div className="flex gap-2 justify-end pt-2">
                <button type="button" className="px-4 py-2 border rounded-lg" onClick={() => setCompraModal(false)}>
                  Cerrar
                </button>
                <button type="submit" className="px-4 py-2 rounded-lg bg-orange-500 text-white">
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
