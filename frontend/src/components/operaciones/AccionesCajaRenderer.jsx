import { ACCIONES_CAJA, ACCIONES_CAJA_LABELS, mensajeAccionPendiente } from '../../utils/accionesCaja'
import { showWarning } from '../../utils/toast'

/**
 * Botones financieros gobernados por acciones[] A0 v2.
 * Fase 2: solo preview — sin POST/PUT/PATCH/DELETE.
 */
export default function AccionesCajaRenderer({ acciones = [], disabled = false }) {
  const visibles = (acciones || []).filter((a) => ACCIONES_CAJA.includes(a.accion))

  if (visibles.length === 0) {
    return null
  }

  const handleClick = (accion) => {
    if (!accion.permitida || disabled) return
    showWarning(mensajeAccionPendiente(accion.accion))
  }

  return (
    <div className="flex flex-wrap gap-2">
      {visibles.map((accion) => {
        const label = ACCIONES_CAJA_LABELS[accion.accion] || accion.accion
        if (accion.permitida) {
          return (
            <button
              key={accion.accion}
              type="button"
              disabled={disabled}
              onClick={() => handleClick(accion)}
              className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 touch-manipulation"
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
  )
}
