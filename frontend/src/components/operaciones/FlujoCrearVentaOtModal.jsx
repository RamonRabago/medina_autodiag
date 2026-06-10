import { useEffect, useState } from 'react'
import Modal from '../Modal'
import api from '../../services/api'
import { ejecutarCrearVentaDesdeOt, debeRefetchA0TrasError } from '../../utils/accionesCajaApi'
import { showError, showSuccess } from '../../utils/toast'

function formatearMoneda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '—'
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(valor))
}

/**
 * Fase 3 — Crear venta desde OT con decisión explícita requiere_factura.
 * Sin cálculos de IVA en frontend; backend es autoridad del total.
 */
export default function FlujoCrearVentaOtModal({
  item,
  abierto,
  onCerrar,
  onExito,
  onErrorNegocio,
}) {
  const [requiereFactura, setRequiereFactura] = useState(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (abierto) {
      setRequiereFactura(null)
      setEnviando(false)
    }
  }, [abierto, item?.id])

  const cerrar = () => {
    if (enviando) return
    onCerrar?.()
  }

  const confirmar = async () => {
    if (!item?.id || requiereFactura === null || enviando) return
    setEnviando(true)
    try {
      const res = await ejecutarCrearVentaDesdeOt(api, item.id, requiereFactura)
      const idVenta = res.data?.id_venta
      const total = res.data?.total
      showSuccess(
        idVenta
          ? `Venta #${idVenta} creada${total != null ? ` — Total ${formatearMoneda(total)}` : ''}`
          : 'Venta creada desde la orden'
      )
      onExito?.(res.data)
    } catch (err) {
      showError(err, 'No se pudo crear la venta')
      if (debeRefetchA0TrasError(err)) {
        onErrorNegocio?.()
      }
    } finally {
      setEnviando(false)
    }
  }

  if (!item) return null

  return (
    <Modal
      titulo={`Crear venta — ${item.numero_orden || `OT #${item.id}`}`}
      abierto={abierto}
      onCerrar={cerrar}
    >
      <div className="space-y-4">
        <div className="text-sm text-slate-600 space-y-1">
          <p>{item.cliente_nombre || '—'}</p>
          <p>{item.vehiculo_resumen || '—'}</p>
          {item.total_orden != null && (
            <p className="text-slate-700">
              Total orden (referencia): {formatearMoneda(item.total_orden)}
            </p>
          )}
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800 mb-2">
            ¿Requiere factura? <span className="text-red-600">*</span>
          </legend>
          <label className="flex items-center gap-2 cursor-pointer min-h-[44px] touch-manipulation">
            <input
              type="radio"
              name="requiere_factura_ot"
              checked={requiereFactura === false}
              onChange={() => setRequiereFactura(false)}
              disabled={enviando}
              className="border-slate-300"
            />
            <span className="text-sm text-slate-700">No requiere factura</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer min-h-[44px] touch-manipulation">
            <input
              type="radio"
              name="requiere_factura_ot"
              checked={requiereFactura === true}
              onChange={() => setRequiereFactura(true)}
              disabled={enviando}
              className="border-slate-300"
            />
            <span className="text-sm text-slate-700">Requiere factura</span>
          </label>
        </fieldset>

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={cerrar}
            disabled={enviando}
            className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 touch-manipulation disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={confirmar}
            disabled={enviando || requiereFactura === null}
            className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 touch-manipulation disabled:opacity-50"
          >
            {enviando ? 'Creando...' : 'Confirmar y crear venta'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
