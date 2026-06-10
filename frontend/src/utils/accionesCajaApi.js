/**
 * Mutaciones delegadas Caja Operativa P4.1 — sin lógica de permisos local.
 */

/**
 * @param {import('axios').AxiosInstance} api
 * @param {number} ordenId
 * @param {boolean} requiereFactura
 */
export function ejecutarCrearVentaDesdeOt(api, ordenId, requiereFactura) {
  return api.post(`/ventas/desde-orden/${ordenId}`, null, {
    params: { requiere_factura: requiereFactura },
  })
}

/** Refetch A0 tras error de negocio desalineado (400/409). No aplica a red/timeout. */
export function debeRefetchA0TrasError(err) {
  const status = err?.response?.status
  return status === 400 || status === 409
}
