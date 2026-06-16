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

/** Mi Taller P3.1 — vista operativa técnico / supervisión admin. */
export const ROLES_MI_TALLER = ['ADMIN', 'TECNICO']

export function puedeMiTaller(rol) {
  return ROLES_MI_TALLER.includes(rol)
}

/** Caja Operativa P4.1 — Modo Mostrador (ADMIN y CAJA; misma UI). */
export const ROLES_CAJA_OPERATIVA = ['ADMIN', 'CAJA']

export function puedeCajaOperativa(rol) {
  return ROLES_CAJA_OPERATIVA.includes(rol)
}

/** Landing post-login y guard en `/` (P5.1). */
const LANDING_POR_ROL = {
  ADMIN: '/',
  CAJA: '/operaciones/caja',
  TECNICO: '/operaciones/mi-taller',
  EMPLEADO: '/operaciones/recepcion',
}

export function getLandingPorRol(rol) {
  return LANDING_POR_ROL[rol] ?? '/'
}
