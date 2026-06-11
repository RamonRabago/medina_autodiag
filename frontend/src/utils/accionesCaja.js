/** Acciones financieras Caja Operativa P4.1 — alineado con evaluador A0 v2. */
export const ACCIONES_CAJA = [
  'crear_venta_desde_ot',
  'registrar_pago',
  'entregar_vehiculo',
]

export const ACCIONES_CAJA_LABELS = {
  crear_venta_desde_ot: 'Crear venta',
  registrar_pago: 'Registrar pago',
  entregar_vehiculo: 'Entregar vehículo',
}

/** Mensajes placeholder para acciones no implementadas en Caja Operativa. */
export function mensajeAccionPendiente(accion) {
  if (accion === 'crear_venta_desde_ot') {
    return 'Flujo crear venta desde OT — pendiente de Fase 3.'
  }
  return `Acción no disponible: ${accion}`
}
