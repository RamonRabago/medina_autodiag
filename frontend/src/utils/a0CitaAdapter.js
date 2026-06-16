/**
 * Adapta ítem cita A0 al shape esperado por modales/helpers de Citas V2.
 */
export function a0CitaItemToCitaShape(item) {
  if (!item) return null
  return {
    id_cita: item.id,
    estado: item.estado,
    estado_meta: item.estado_meta,
  }
}
