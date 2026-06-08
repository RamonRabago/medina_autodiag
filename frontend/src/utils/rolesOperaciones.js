/** Roles con acceso a recepción rápida (alineado con backend POST /recepcion-rapida). */
export const ROLES_RECEPCION = ['ADMIN', 'CAJA', 'EMPLEADO']

export function puedeRecepcionRapida(rol) {
  return ROLES_RECEPCION.includes(rol)
}
