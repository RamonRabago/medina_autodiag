/** Acciones cita soportadas en Recepción P5.2 — alineado con evaluador A0. */
export const ACCIONES_CITA_RECEPCION = ['marcar_asistencia_cita', 'convertir_cita_ot']

export const ACCIONES_CITA_LABELS = {
  marcar_asistencia_cita: 'Marcar asistencia',
  convertir_cita_ot: 'Completar recepción',
}

/**
 * PATCH /citas/{id}/estado
 * @param {import('axios').AxiosInstance} api
 */
export async function patchEstadoCita(api, idCita, payload) {
  const res = await api.patch(`/citas/${idCita}/estado`, payload)
  return res.data
}

/**
 * Marcación inicial o corrección simple de asistencia.
 * @param {import('axios').AxiosInstance} api
 * @param {string} nuevoEstado SI_ASISTIO | NO_ASISTIO | etc.
 */
export async function marcarAsistenciaCita(api, idCita, nuevoEstado) {
  return patchEstadoCita(api, idCita, { estado_nuevo: nuevoEstado })
}

/**
 * POST /citas/{id}/convertir-orden — reservado; Recepción P5.2 usa navegación ?cita_id= como CTA principal.
 * @param {import('axios').AxiosInstance} api
 */
export async function convertirCitaOt(api, idCita) {
  const res = await api.post(`/citas/${idCita}/convertir-orden`)
  return res.data
}
