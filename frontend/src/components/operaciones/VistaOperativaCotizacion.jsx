import { useState, useEffect, useMemo, useCallback } from 'react'
import api from '../../services/api'
import EstadoOTBadge from '../EstadoOTBadge'
import SearchableServicioSelect from './SearchableServicioSelect'
import SearchableRepuestoSelect from '../SearchableRepuestoSelect'
import { aEntero, aNumero } from '../../utils/numeros'
import { normalizeDetail, showError, showSuccess } from '../../utils/toast'

const idServicio = (s) => s?.id ?? s?.id_servicio
const idRepuesto = (r) => r?.id_repuesto ?? r?.id

function ordenToDraft(orden) {
  return {
    diagnostico_inicial: orden.diagnostico_inicial || '',
    observaciones_cliente: orden.observaciones_cliente || '',
    requiere_autorizacion: !!orden.requiere_autorizacion,
    cliente_proporciono_refacciones: !!orden.cliente_proporciono_refacciones,
    servicios: (orden.detalles_servicio || []).map((d) => ({
      servicio_id: d.servicio_id,
      cantidad: d.cantidad || 1,
      precio_unitario: d.precio_unitario ?? 0,
      descripcion: d.descripcion || null,
    })),
    repuestos: (orden.detalles_repuesto || []).map((d) => ({
      repuesto_id: d.repuesto_id ?? null,
      descripcion_libre: d.descripcion_libre || null,
      cantidad: d.cantidad || 1,
      precio_unitario: d.precio_unitario ?? 0,
      precio_compra_estimado: d.precio_compra_estimado ?? null,
    })),
  }
}

function lineSubtotal(cantidad, precio) {
  const c = aNumero(cantidad, 0)
  const p = aNumero(precio, 0)
  return c * p
}

/**
 * Vista operativa de cotización OT (P5.5.1) — captura en detalle sin salir de pantalla.
 */
export default function VistaOperativaCotizacion({
  orden,
  onGuardado,
  onDescargarPdf,
  descargandoPdf = false,
}) {
  const [catalogoServicios, setCatalogoServicios] = useState([])
  const [catalogoRepuestos, setCatalogoRepuestos] = useState([])
  const [cargandoCatalogos, setCargandoCatalogos] = useState(true)
  const [draft, setDraft] = useState(() => ordenToDraft(orden))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  const [nuevoServicio, setNuevoServicio] = useState({ id: '', cantidad: 1, precio: '' })
  const [nuevoRepuesto, setNuevoRepuesto] = useState({
    tipo: 'catalogo',
    id: '',
    descripcion_libre: '',
    cantidad: 1,
    precio: '',
  })

  useEffect(() => {
    setDraft(ordenToDraft(orden))
    setError('')
  }, [orden])

  useEffect(() => {
    let cancel = false
    setCargandoCatalogos(true)
    Promise.all([
      api.get('/servicios/', { params: { limit: 100 } }),
      api.get('/repuestos/', { params: { limit: 500 } }),
    ])
      .then(([rs, rr]) => {
        if (cancel) return
        const sv = rs.data?.servicios ?? rs.data ?? []
        const rawRep = rr.data
        const rp = Array.isArray(rawRep) ? rawRep : rawRep?.items ?? rawRep?.repuestos ?? []
        setCatalogoServicios(Array.isArray(sv) ? sv : [])
        setCatalogoRepuestos(
          (Array.isArray(rp) ? rp : []).map((r) => ({
            ...r,
            id_repuesto: idRepuesto(r),
          }))
        )
      })
      .catch((err) => {
        if (!cancel) setError(normalizeDetail(err?.response?.data?.detail) || 'Error al cargar catálogos')
      })
      .finally(() => {
        if (!cancel) setCargandoCatalogos(false)
      })
    return () => {
      cancel = true
    }
  }, [])

  const subtotalServicios = useMemo(
    () =>
      (draft.servicios || []).reduce(
        (acc, s) => acc + lineSubtotal(s.cantidad, s.precio_unitario),
        0
      ),
    [draft.servicios]
  )

  const subtotalRepuestos = useMemo(
    () =>
      (draft.repuestos || []).reduce(
        (acc, r) => acc + lineSubtotal(r.cantidad, r.precio_unitario),
        0
      ),
    [draft.repuestos]
  )

  const totalDraft = subtotalServicios + subtotalRepuestos - aNumero(orden.descuento, 0)
  const tieneConceptos = (draft.servicios?.length || 0) > 0 || (draft.repuestos?.length || 0) > 0
  const listaParaPdf = tieneConceptos && subtotalServicios + subtotalRepuestos > 0

  const nombreServicio = useCallback(
    (s) => {
      const cat = catalogoServicios.find((x) => idServicio(x) === s.servicio_id)
      return s.descripcion || cat?.nombre || `Servicio #${s.servicio_id}`
    },
    [catalogoServicios]
  )

  const nombreRepuesto = useCallback(
    (r) => {
      if (r.descripcion_libre) return r.descripcion_libre
      const cat = catalogoRepuestos.find((x) => idRepuesto(x) === r.repuesto_id)
      return cat?.nombre || `Repuesto #${r.repuesto_id || 'N/A'}`
    },
    [catalogoRepuestos]
  )

  const hayServiciosQueRequierenRepuestos = (draft.servicios || []).some((fs) => {
    const s = catalogoServicios.find((x) => idServicio(x) === fs.servicio_id)
    return !!s?.requiere_repuestos
  })
  const advertenciaRepuestos =
    hayServiciosQueRequierenRepuestos &&
    (draft.repuestos?.length || 0) === 0 &&
    !draft.cliente_proporciono_refacciones

  const actualizarServicio = (idx, campo, valor) => {
    setDraft((prev) => {
      const servicios = [...(prev.servicios || [])]
      servicios[idx] = { ...servicios[idx], [campo]: valor }
      return { ...prev, servicios }
    })
  }

  const actualizarRepuesto = (idx, campo, valor) => {
    setDraft((prev) => {
      const repuestos = [...(prev.repuestos || [])]
      repuestos[idx] = { ...repuestos[idx], [campo]: valor }
      return { ...prev, repuestos }
    })
  }

  const agregarServicio = () => {
    const servicioId = aEntero(nuevoServicio.id, 0)
    if (!servicioId) {
      showError('Selecciona un servicio')
      return
    }
    const cat = catalogoServicios.find((x) => idServicio(x) === servicioId)
    const cantidad = aEntero(nuevoServicio.cantidad, 1)
    if (cantidad < 1) {
      showError('Cantidad inválida')
      return
    }
    const precio =
      nuevoServicio.precio !== '' && nuevoServicio.precio != null
        ? aNumero(nuevoServicio.precio, 0)
        : Number(cat?.precio_base) || 0
    if (
      cat?.requiere_repuestos &&
      (draft.repuestos?.length || 0) === 0 &&
      !draft.cliente_proporciono_refacciones
    ) {
      if (
        !window.confirm(
          `"${cat.nombre}" suele requerir refacciones. ¿Agregar el servicio de todos modos?`
        )
      ) {
        return
      }
    }
    setDraft((prev) => ({
      ...prev,
      servicios: [
        ...(prev.servicios || []),
        {
          servicio_id: servicioId,
          cantidad,
          precio_unitario: precio,
          descripcion: cat?.nombre || null,
        },
      ],
    }))
    setNuevoServicio({ id: '', cantidad: 1, precio: '' })
  }

  const agregarRepuesto = () => {
    const cantidad = aNumero(nuevoRepuesto.cantidad, 1)
    if (cantidad < 0.001) {
      showError('Cantidad inválida')
      return
    }
    if (nuevoRepuesto.tipo === 'catalogo') {
      const repId = aEntero(nuevoRepuesto.id, 0)
      if (!repId) {
        showError('Selecciona una refacción del catálogo')
        return
      }
      const cat = catalogoRepuestos.find((x) => idRepuesto(x) === repId)
      const precio =
        nuevoRepuesto.precio !== '' && nuevoRepuesto.precio != null
          ? aNumero(nuevoRepuesto.precio, 0)
          : Number(cat?.precio_venta) || 0
      setDraft((prev) => ({
        ...prev,
        repuestos: [
          ...(prev.repuestos || []),
          {
            repuesto_id: repId,
            descripcion_libre: null,
            cantidad,
            precio_unitario: precio,
            precio_compra_estimado: null,
          },
        ],
      }))
    } else {
      const desc = (nuevoRepuesto.descripcion_libre || '').trim()
      if (!desc) {
        showError('Indica la descripción de la refacción')
        return
      }
      const precio = aNumero(nuevoRepuesto.precio, 0)
      setDraft((prev) => ({
        ...prev,
        repuestos: [
          ...(prev.repuestos || []),
          {
            repuesto_id: null,
            descripcion_libre: desc,
            cantidad,
            precio_unitario: precio,
            precio_compra_estimado: null,
          },
        ],
      }))
    }
    setNuevoRepuesto({ tipo: 'catalogo', id: '', descripcion_libre: '', cantidad: 1, precio: '' })
  }

  const descartarCambios = () => {
    setDraft(ordenToDraft(orden))
    setError('')
    showSuccess('Cambios descartados')
  }

  const guardar = async () => {
    const diag = (draft.diagnostico_inicial || '').trim()
    const obs = (draft.observaciones_cliente || '').trim()
    if (!diag) {
      showError('El diagnóstico inicial es obligatorio')
      return
    }
    if (!obs) {
      showError('Las observaciones del cliente son obligatorias')
      return
    }
    if (!tieneConceptos) {
      showError('Agrega al menos un servicio o refacción')
      return
    }
    if (advertenciaRepuestos) {
      if (
        !window.confirm(
          'Hay servicios que suelen requerir refacciones. ¿Guardar sin refacciones ni marcar "Cliente proporcionó refacciones"?'
        )
      ) {
        return
      }
    }
    setGuardando(true)
    setError('')
    try {
      const payload = {
        tecnico_id: orden.tecnico_id ?? null,
        id_vendedor: orden.id_vendedor ?? null,
        prioridad: orden.prioridad || 'NORMAL',
        fecha_promesa: orden.fecha_promesa || null,
        observaciones_tecnico: orden.observaciones_tecnico?.trim() || null,
        diagnostico_inicial: diag,
        observaciones_cliente: obs,
        requiere_autorizacion: draft.requiere_autorizacion,
        cliente_proporciono_refacciones: draft.cliente_proporciono_refacciones,
        servicios: (draft.servicios || []).map((s) => ({
          servicio_id: s.servicio_id,
          cantidad: aEntero(s.cantidad, 1),
          precio_unitario: aNumero(s.precio_unitario, 0),
          descripcion: s.descripcion || null,
        })),
        repuestos: (draft.repuestos || []).map((r) => ({
          repuesto_id: r.repuesto_id ?? null,
          descripcion_libre: r.descripcion_libre || null,
          cantidad: aNumero(r.cantidad, 1),
          precio_unitario: aNumero(r.precio_unitario, 0),
          precio_compra_estimado: r.precio_compra_estimado ?? null,
        })),
      }
      await api.put(`/ordenes-trabajo/${orden.id}`, payload)
      showSuccess('Cotización guardada')
      onGuardado?.()
    } catch (err) {
      const msg = normalizeDetail(err?.response?.data?.detail) || 'Error al guardar'
      setError(msg)
      showError(err, 'Error al guardar')
    } finally {
      setGuardando(false)
    }
  }

  const clienteNombre = orden.cliente?.nombre ?? orden.cliente_nombre ?? '-'
  const vehiculoTexto = orden.vehiculo
    ? `${orden.vehiculo.marca} ${orden.vehiculo.modelo} ${orden.vehiculo.anio || ''}`.trim()
    : orden.vehiculo_info ?? '-'

  return (
    <div className="border-2 border-primary-200 rounded-xl overflow-hidden bg-white shadow-sm">
      {/* Encabezado */}
      <div className="bg-primary-50 border-b border-primary-100 px-4 py-4 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Cotización — Vista operativa</h2>
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-sm text-slate-700">
              <p>
                <span className="font-medium text-slate-600">Cliente:</span> {clienteNombre}
              </p>
              <p>
                <span className="font-medium text-slate-600">Vehículo:</span> {vehiculoTexto}
              </p>
              <p>
                <span className="font-medium text-slate-600">OT:</span> {orden.numero_orden}
              </p>
              <p className="flex items-center gap-2">
                <span className="font-medium text-slate-600">Estado:</span>
                <EstadoOTBadge estado={orden.estado} />
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onDescargarPdf}
            disabled={descargandoPdf || !listaParaPdf}
            title={listaParaPdf ? 'Descargar cotización PDF' : 'Guarda al menos un concepto antes del PDF'}
            className="shrink-0 min-h-[44px] px-4 py-2 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700 disabled:opacity-50 touch-manipulation"
          >
            {descargandoPdf ? 'Generando PDF...' : 'Generar PDF'}
          </button>
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-5">
        {error && <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>}
        {cargandoCatalogos && (
          <p className="text-sm text-slate-500">Cargando catálogos de servicios y refacciones...</p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Diagnóstico inicial *</label>
            <textarea
              value={draft.diagnostico_inicial}
              onChange={(e) => setDraft((p) => ({ ...p, diagnostico_inicial: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              placeholder="Qué reporta el cliente o hallazgo inicial"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones del cliente *</label>
            <textarea
              value={draft.observaciones_cliente}
              onChange={(e) => setDraft((p) => ({ ...p, observaciones_cliente: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              placeholder="Preferencias, urgencias"
            />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 text-sm">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={!!draft.requiere_autorizacion}
              onChange={(e) => setDraft((p) => ({ ...p, requiere_autorizacion: e.target.checked }))}
            />
            <span>Requiere autorización del cliente</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={!!draft.cliente_proporciono_refacciones}
              onChange={(e) => setDraft((p) => ({ ...p, cliente_proporciono_refacciones: e.target.checked }))}
            />
            <span>Cliente proporcionó refacciones</span>
          </label>
        </div>

        {/* Mano de obra */}
        <section>
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Mano de obra / Servicios</h3>
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-sm min-w-[520px]">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Descripción</th>
                  <th className="text-right px-2 py-2 font-medium w-20">Cant.</th>
                  <th className="text-right px-2 py-2 font-medium w-28">P. unit.</th>
                  <th className="text-right px-3 py-2 font-medium w-28">Subtotal</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(draft.servicios || []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-4 text-center text-slate-500">
                      Sin servicios. Agrega uno abajo.
                    </td>
                  </tr>
                ) : (
                  (draft.servicios || []).map((s, idx) => (
                    <tr key={`sv-${idx}`}>
                      <td className="px-3 py-2 text-slate-800">{nombreServicio(s)}</td>
                      <td className="px-2 py-1">
                        <input
                          type="number"
                          min={1}
                          step={1}
                          value={s.cantidad}
                          onChange={(e) => actualizarServicio(idx, 'cantidad', aEntero(e.target.value, 1))}
                          className="w-full px-2 py-1.5 text-right border border-slate-300 rounded text-sm"
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input
                          type="number"
                          min={0}
                          step={0.01}
                          value={s.precio_unitario}
                          onChange={(e) =>
                            actualizarServicio(idx, 'precio_unitario', aNumero(e.target.value, 0))
                          }
                          className="w-full px-2 py-1.5 text-right border border-slate-300 rounded text-sm"
                        />
                      </td>
                      <td className="px-3 py-2 text-right font-medium">
                        ${lineSubtotal(s.cantidad, s.precio_unitario).toFixed(2)}
                      </td>
                      <td className="px-1 py-1">
                        <button
                          type="button"
                          onClick={() =>
                            setDraft((p) => ({
                              ...p,
                              servicios: p.servicios.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-red-600 hover:text-red-800 text-xs px-1"
                          aria-label="Eliminar servicio"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <SearchableServicioSelect
              servicios={catalogoServicios}
              value={nuevoServicio.id}
              onChange={(v) => {
                const cat = catalogoServicios.find((x) => String(idServicio(x)) === String(v))
                setNuevoServicio({
                  id: v,
                  cantidad: 1,
                  precio: cat ? String(cat.precio_base ?? '') : '',
                })
              }}
              placeholder="Buscar servicio..."
              className="min-w-[180px]"
            />
            <input
              type="number"
              min={1}
              step={1}
              value={nuevoServicio.cantidad}
              onChange={(e) => setNuevoServicio((p) => ({ ...p, cantidad: e.target.value }))}
              className="w-16 px-2 py-2 border border-slate-300 rounded-lg text-sm min-h-[44px]"
              title="Cantidad"
            />
            <input
              type="number"
              min={0}
              step={0.01}
              value={nuevoServicio.precio}
              onChange={(e) => setNuevoServicio((p) => ({ ...p, precio: e.target.value }))}
              placeholder="Precio"
              className="w-24 px-2 py-2 border border-slate-300 rounded-lg text-sm min-h-[44px]"
            />
            <button
              type="button"
              onClick={agregarServicio}
              className="min-h-[44px] px-3 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 touch-manipulation"
            >
              + Agregar servicio
            </button>
          </div>
        </section>

        {/* Refacciones */}
        <section>
          <h3 className="text-sm font-semibold text-slate-800 mb-2">Refacciones</h3>
          {advertenciaRepuestos && (
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg mb-2">
              Hay servicios que suelen requerir refacciones. Agrega piezas o marca &quot;Cliente proporcionó
              refacciones&quot;.
            </p>
          )}
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-sm min-w-[520px]">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Descripción</th>
                  <th className="text-right px-2 py-2 font-medium w-20">Cant.</th>
                  <th className="text-right px-2 py-2 font-medium w-28">P. unit.</th>
                  <th className="text-right px-3 py-2 font-medium w-28">Subtotal</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(draft.repuestos || []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-4 text-center text-slate-500">
                      Sin refacciones.
                    </td>
                  </tr>
                ) : (
                  (draft.repuestos || []).map((r, idx) => (
                    <tr key={`rp-${idx}`}>
                      <td className="px-3 py-2 text-slate-800">{nombreRepuesto(r)}</td>
                      <td className="px-2 py-1">
                        <input
                          type="number"
                          min={0.001}
                          step={0.001}
                          value={r.cantidad}
                          onChange={(e) => actualizarRepuesto(idx, 'cantidad', aNumero(e.target.value, 1))}
                          className="w-full px-2 py-1.5 text-right border border-slate-300 rounded text-sm"
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input
                          type="number"
                          min={0}
                          step={0.01}
                          value={r.precio_unitario}
                          onChange={(e) =>
                            actualizarRepuesto(idx, 'precio_unitario', aNumero(e.target.value, 0))
                          }
                          className="w-full px-2 py-1.5 text-right border border-slate-300 rounded text-sm"
                        />
                      </td>
                      <td className="px-3 py-2 text-right font-medium">
                        ${lineSubtotal(r.cantidad, r.precio_unitario).toFixed(2)}
                      </td>
                      <td className="px-1 py-1">
                        <button
                          type="button"
                          onClick={() =>
                            setDraft((p) => ({
                              ...p,
                              repuestos: p.repuestos.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-red-600 hover:text-red-800 text-xs px-1"
                          aria-label="Eliminar refacción"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap gap-2 items-center">
              <select
                value={nuevoRepuesto.tipo}
                onChange={(e) =>
                  setNuevoRepuesto((p) => ({
                    ...p,
                    tipo: e.target.value,
                    id: '',
                    descripcion_libre: '',
                  }))
                }
                className="px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-sm"
              >
                <option value="catalogo">Catálogo</option>
                <option value="libre">Descripción libre</option>
              </select>
              {nuevoRepuesto.tipo === 'catalogo' ? (
                <SearchableRepuestoSelect
                  repuestos={catalogoRepuestos}
                  value={nuevoRepuesto.id}
                  onChange={(v) => {
                    const cat = catalogoRepuestos.find((x) => String(idRepuesto(x)) === String(v))
                    setNuevoRepuesto((p) => ({
                      ...p,
                      id: v,
                      precio: cat ? String(cat.precio_venta ?? '') : '',
                    }))
                  }}
                  placeholder="Buscar refacción..."
                  className="min-w-[180px] min-h-[44px]"
                />
              ) : (
                <input
                  type="text"
                  value={nuevoRepuesto.descripcion_libre}
                  onChange={(e) =>
                    setNuevoRepuesto((p) => ({ ...p, descripcion_libre: e.target.value }))
                  }
                  placeholder="Ej. Aceite 5W-30"
                  className="flex-1 min-w-[160px] px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-sm"
                />
              )}
              <input
                type="number"
                min={0.001}
                step={0.001}
                value={nuevoRepuesto.cantidad}
                onChange={(e) => setNuevoRepuesto((p) => ({ ...p, cantidad: e.target.value }))}
                className="w-16 px-2 py-2 border border-slate-300 rounded-lg text-sm min-h-[44px]"
              />
              <input
                type="number"
                min={0}
                step={0.01}
                value={nuevoRepuesto.precio}
                onChange={(e) => setNuevoRepuesto((p) => ({ ...p, precio: e.target.value }))}
                placeholder="Precio"
                className="w-24 px-2 py-2 border border-slate-300 rounded-lg text-sm min-h-[44px]"
              />
              <button
                type="button"
                onClick={agregarRepuesto}
                className="min-h-[44px] px-3 py-2 bg-slate-700 text-white rounded-lg text-sm hover:bg-slate-800 touch-manipulation"
              >
                + Agregar refacción
              </button>
            </div>
          </div>
        </section>

        {/* Resumen */}
        <div className="sticky bottom-0 bg-slate-50 border border-slate-200 rounded-lg p-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1 text-sm">
              <div className="flex justify-between sm:justify-start sm:gap-8">
                <span className="text-slate-600">Subtotal mano de obra:</span>
                <span className="font-medium">${subtotalServicios.toFixed(2)}</span>
              </div>
              <div className="flex justify-between sm:justify-start sm:gap-8">
                <span className="text-slate-600">Subtotal refacciones:</span>
                <span className="font-medium">${subtotalRepuestos.toFixed(2)}</span>
              </div>
              {aNumero(orden.descuento, 0) > 0 && (
                <div className="flex justify-between sm:justify-start sm:gap-8 text-amber-800">
                  <span>Descuento (guardado en OT):</span>
                  <span>-${aNumero(orden.descuento, 0).toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between sm:justify-start sm:gap-8 text-base font-bold text-slate-900 pt-1 border-t border-slate-200">
                <span>Total estimado:</span>
                <span>${Math.max(0, totalDraft).toFixed(2)}</span>
              </div>
              <p
                className={`text-xs font-medium mt-1 ${listaParaPdf ? 'text-green-700' : 'text-amber-700'}`}
              >
                {listaParaPdf ? 'Lista para generar PDF' : 'Faltan conceptos — agrega servicios o refacciones'}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={descartarCambios}
                className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm hover:bg-white touch-manipulation"
              >
                Descartar cambios
              </button>
              <button
                type="button"
                onClick={guardar}
                disabled={guardando}
                className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 touch-manipulation"
              >
                {guardando ? 'Guardando...' : 'Guardar cambios'}
              </button>
              <button
                type="button"
                onClick={onDescargarPdf}
                disabled={descargandoPdf || !listaParaPdf}
                className="min-h-[44px] px-4 py-2 bg-orange-600 text-white rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50 touch-manipulation"
              >
                Generar PDF
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
