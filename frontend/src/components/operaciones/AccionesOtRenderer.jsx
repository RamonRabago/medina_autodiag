import { useState } from 'react'
import api from '../../services/api'
import { showError } from '../../utils/toast'
import {
  ACCIONES_OT_LABELS,
  ACCIONES_OT_MI_TALLER,
  ejecutarAccionOt,
} from '../../utils/accionesOtApi'

/**
 * Renderiza botones desde acciones[] del evaluador — sin lógica local de estado/rol.
 */
export default function AccionesOtRenderer({ acciones = [], ordenId, onExito, disabled = false }) {
  const [ejecutando, setEjecutando] = useState(null)

  const visibles = (acciones || []).filter((a) => ACCIONES_OT_MI_TALLER.includes(a.accion))

  if (visibles.length === 0) {
    return null
  }

  const handleClick = async (accion) => {
    if (!accion.permitida || ejecutando) return
    setEjecutando(accion.accion)
    try {
      await ejecutarAccionOt(api, accion.accion, ordenId)
      onExito?.(accion.accion)
    } catch (err) {
      showError(err, ACCIONES_OT_LABELS[accion.accion] || 'Error en acción')
    } finally {
      setEjecutando(null)
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {visibles.map((accion) => {
        const label = ACCIONES_OT_LABELS[accion.accion] || accion.accion
        const loading = ejecutando === accion.accion
        if (accion.permitida) {
          return (
            <button
              key={accion.accion}
              type="button"
              disabled={disabled || loading || !!ejecutando}
              onClick={() => handleClick(accion)}
              className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 touch-manipulation"
            >
              {loading ? '...' : label}
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
