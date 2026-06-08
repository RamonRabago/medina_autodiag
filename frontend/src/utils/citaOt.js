/**
 * Construye motivo de recepción desde datos de cita (espejo de backend construir_motivo_desde_cita).
 */
export function construirMotivoDesdeCita(cita) {
  const partes = []
  if (cita?.motivo?.trim()) partes.push(cita.motivo.trim())
  if (cita?.notas?.trim()) {
    const notas = cita.notas.trim()
    if (!partes.includes(notas)) partes.push(notas)
  }
  if (partes.length === 0) {
    const tip = (cita?.tipo || 'OTRO').replace(/_/g, ' ')
    partes.push(`Cita ${tip.charAt(0) + tip.slice(1).toLowerCase()}`)
  }
  let texto = partes.length > 1 ? partes.join(' — ') : partes[0]
  if (texto.length < 10) {
    texto = `${texto} (cita #${cita.id_cita})`
  }
  return texto.slice(0, 2000)
}

/**
 * Extrae payload estructurado de error FastAPI (detail dict).
 */
export function extraerDetalleEstructurado(err) {
  const detail = err?.response?.data?.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    return detail
  }
  return null
}

/** Estados de cita elegibles para conversión directa a OT (P2). */
export const ESTADOS_CITA_CONVERTIBLES_OT = ['CONFIRMADA', 'SI_ASISTIO']

export function puedeConvertirCitaAOT(cita, userRol, puedeRecepcionFn) {
  if (!cita || cita.id_orden) return false
  if (!ESTADOS_CITA_CONVERTIBLES_OT.includes(cita.estado)) return false
  return typeof puedeRecepcionFn === 'function' ? puedeRecepcionFn(userRol) : false
}
