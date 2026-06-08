/**
 * Presentación de estados y motivos de citas (sin reglas de negocio).
 */
import { normalizeDetail } from './toast'
import { extraerDetalleEstructurado } from './citaOt'

export const ESTADOS_CITA_LABELS = {
  CONFIRMADA: 'Confirmada',
  SI_ASISTIO: 'Sí asistió',
  NO_ASISTIO: 'No asistió',
  CANCELADA: 'Cancelada',
}

export const ESTADOS_CITA_BADGE = {
  CONFIRMADA: 'bg-blue-100 text-blue-800',
  SI_ASISTIO: 'bg-green-100 text-green-800',
  NO_ASISTIO: 'bg-red-100 text-red-800',
  CANCELADA: 'bg-slate-200 text-slate-700',
}

export const MOTIVOS_CORRECCION = [
  { codigo: 'ERROR_CAPTURA', label: 'Corrección por error de captura' },
  { codigo: 'CLIENTE_TARDE', label: 'Cliente llegó tarde' },
  { codigo: 'CLIENTE_CONFIRMO_DESPUES', label: 'Cliente confirmó después' },
  { codigo: 'ERROR_RECEPCION', label: 'Error de recepción' },
  { codigo: 'OTRO', label: 'Otro' },
]

export const MOTIVO_DETALLE_MIN = 10

export function labelEstadoCita(estado) {
  return ESTADOS_CITA_LABELS[estado] || estado || '-'
}

export function badgeEstadoCita(estado) {
  return ESTADOS_CITA_BADGE[estado] || 'bg-slate-100 text-slate-700'
}

export function labelMotivoCorreccion(codigo) {
  return MOTIVOS_CORRECCION.find((m) => m.codigo === codigo)?.label || codigo
}

/**
 * Mensaje de error legible para PATCH /citas/{id}/estado.
 */
export function mensajeErrorCambioEstado(err) {
  const status = err?.response?.status
  const detail = err?.response?.data?.detail
  const structured = extraerDetalleEstructurado(err)

  if (structured?.mensaje) {
    return structured.mensaje
  }

  if (status === 403) {
    const text = normalizeDetail(detail) || ''
    if (/t[eé]cnico/i.test(text)) {
      return 'Tu rol no permite corregir estados cerrados. Solicita apoyo de recepción o un administrador.'
    }
    if (/24/.test(text) || /ventana/i.test(text)) {
      return 'La ventana de corrección de 24 horas expiró. Solo un administrador puede corregir esta cita.'
    }
    if (/OT vinculada|solo ADMIN/i.test(text)) {
      return 'Solo un administrador puede corregir el estado de una cita con OT vinculada.'
    }
    if (/reactivar/i.test(text)) {
      return 'Solo ADMIN o CAJA pueden reactivar una cita cancelada.'
    }
    return text || 'No tienes permiso para este cambio de estado.'
  }

  if (status === 409) {
    if (structured?.accion === 'CITA_ESTADO_BLOQUEADO_FINANCIERO') {
      return structured.mensaje || 'La cita está vinculada a una OT con venta o pagos. Corrige desde OT/Venta o solicita autorización administrativa.'
    }
    if (structured?.accion === 'ESTADO_NO_CONVERTIBLE') {
      return structured.mensaje || 'Esta cita no puede cambiar a ese estado en las condiciones actuales.'
    }
    return structured?.mensaje || normalizeDetail(detail) || 'Conflicto al cambiar el estado de la cita.'
  }

  if (status === 400) {
    return normalizeDetail(detail) || 'Datos inválidos para el cambio de estado.'
  }

  return normalizeDetail(detail) || null
}
