/** Roles con acceso a recepción rápida (alineado con backend POST /recepcion-rapida). */
export const ROLES_RECEPCION = ['ADMIN', 'CAJA', 'EMPLEADO']

export function puedeRecepcionRapida(rol) {
  return ROLES_RECEPCION.includes(rol)
}

/** Alta rápida operativa de cliente (alineado con backend POST /clientes/). */
export const ROLES_ALTA_RAPIDA_CLIENTE = ['ADMIN', 'CAJA', 'EMPLEADO']

export function puedeAltaRapidaCliente(rol) {
  return ROLES_ALTA_RAPIDA_CLIENTE.includes(rol)
}
