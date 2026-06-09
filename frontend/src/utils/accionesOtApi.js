/** Acciones OT soportadas en Mi Taller P3.1 — alineado con evaluador backend. */
export const ACCIONES_OT_MI_TALLER = ['iniciar_ot', 'finalizar_ot']

export const ACCIONES_OT_LABELS = {
  iniciar_ot: 'Iniciar',
  finalizar_ot: 'Finalizar',
}

/**
 * Ejecuta mutación OT según nombre de acción del evaluador.
 * @param {import('axios').AxiosInstance} api
 */
export function ejecutarAccionOt(api, accion, ordenId) {
  switch (accion) {
    case 'iniciar_ot':
      return api.post(`/ordenes-trabajo/${ordenId}/iniciar`, {})
    case 'finalizar_ot':
      return api.post(`/ordenes-trabajo/${ordenId}/finalizar`, {})
    default:
      return Promise.reject(new Error(`Acción no soportada en Mi Taller: ${accion}`))
  }
}
