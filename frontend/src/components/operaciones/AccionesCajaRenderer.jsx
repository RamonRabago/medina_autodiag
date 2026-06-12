import { useState } from 'react'
import { ACCIONES_CAJA, ACCIONES_CAJA_LABELS, mensajeAccionPendiente } from '../../utils/accionesCaja'
import { CTA_FLUJO_CAJA, hayAccionCajaPermitida } from '../../utils/flujoCajaPasos'
import { showWarning } from '../../utils/toast'

/**
 * P4.2 — CTA único "Continuar proceso" + fallback a modales P4.1 individuales.
 */
export default function AccionesCajaRenderer({
  acciones = [],
  item,
  disabled = false,
  onCrearVentaDesdeOt,
  onRegistrarPago,
  onEntregarVehiculo,
  onIniciarFlujoGuiado,
}) {
  const [mostrarFallback, setMostrarFallback] = useState(false)
  const visibles = (acciones || []).filter((a) => ACCIONES_CAJA.includes(a.accion))
  const puedeFlujo = hayAccionCajaPermitida(acciones)

  if (visibles.length === 0) {
    return null
  }

  const handleClickAccion = (accion) => {
    if (!accion.permitida || disabled) return
    if (accion.accion === 'crear_venta_desde_ot') {
      if (item && onCrearVentaDesdeOt) onCrearVentaDesdeOt(item)
      return
    }
    if (accion.accion === 'registrar_pago') {
      if (item && onRegistrarPago) onRegistrarPago(item, accion)
      return
    }
    if (accion.accion === 'entregar_vehiculo') {
      if (item && onEntregarVehiculo) onEntregarVehiculo(item)
      return
    }
    showWarning(mensajeAccionPendiente(accion.accion))
  }

  const bloqueos = visibles.filter((a) => !a.permitida && a.motivo_bloqueo)

  return (
    <div className="flex flex-col gap-2 w-full">
      {puedeFlujo && onIniciarFlujoGuiado ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onIniciarFlujoGuiado(item)}
          className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 touch-manipulation"
        >
          {CTA_FLUJO_CAJA}
        </button>
      ) : null}

      {!puedeFlujo && bloqueos.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {bloqueos.map((accion) => (
            <span
              key={accion.accion}
              title={accion.motivo_bloqueo}
              className="inline-flex min-h-[36px] items-center px-3 py-1.5 text-xs rounded-lg bg-slate-100 text-slate-500 cursor-not-allowed"
            >
              {ACCIONES_CAJA_LABELS[accion.accion] || accion.accion}
            </span>
          ))}
        </div>
      ) : null}

      {puedeFlujo ? (
        <button
          type="button"
          onClick={() => setMostrarFallback((v) => !v)}
          className="text-xs text-slate-500 hover:text-slate-700 underline underline-offset-2 text-left touch-manipulation"
        >
          {mostrarFallback ? 'Ocultar acciones individuales' : 'Acciones individuales'}
        </button>
      ) : null}

      {mostrarFallback && puedeFlujo ? (
        <div className="flex flex-wrap gap-2">
          {visibles.map((accion) => {
            const label = ACCIONES_CAJA_LABELS[accion.accion] || accion.accion
            if (accion.permitida) {
              return (
                <button
                  key={accion.accion}
                  type="button"
                  disabled={disabled}
                  onClick={() => handleClickAccion(accion)}
                  className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 disabled:opacity-50 touch-manipulation"
                >
                  {label}
                </button>
              )
            }
            if (accion.motivo_bloqueo) {
              return (
                <span
                  key={accion.accion}
                  title={accion.motivo_bloqueo}
                  className="inline-flex min-h-[36px] items-center px-3 py-1.5 text-xs rounded-lg bg-slate-100 text-slate-500 cursor-not-allowed"
                >
                  {label}
                </span>
              )
            }
            return null
          })}
        </div>
      ) : null}
    </div>
  )
}
