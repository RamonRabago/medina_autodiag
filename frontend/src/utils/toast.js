/**
 * Utilidad de notificaciones toast.
 * Reemplazo de alert() con diseño consistente y mejor UX.
 */
import toast from 'react-hot-toast'

function normalizeDetail(detail) {
  if (detail == null) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((x) => x?.msg ?? x).join(', ')
  return String(detail)
}

/**
 * Muestra error. Si se pasa un objeto error de axios, extrae detail.
 * @param {Error|string} errOrMsg - Error de axios o mensaje
 * @param {string} fallback - Mensaje si no hay detail
 */
export function showError(errOrMsg, fallback = 'Error') {
  const msg =
    errOrMsg?.response?.data?.detail != null
      ? normalizeDetail(errOrMsg.response.data.detail) || fallback
      : typeof errOrMsg === 'string'
        ? errOrMsg
        : fallback
  toast.error(msg)
}

/**
 * Muestra mensaje de éxito
 */
export function showSuccess(msg) {
  toast.success(msg)
}

/**
 * Muestra advertencia (validaciones, avisos)
 */
export function showWarning(msg) {
  toast(msg, { icon: '⚠️', style: { background: '#fef3c7', color: '#92400e' } })
}

export { toast }
