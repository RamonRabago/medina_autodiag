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

/**
 * @param {import('axios').AxiosInstance} api
 * @param {{ id_venta: number, metodo: string, monto: number, referencia?: string }} payload
 */
export function ejecutarRegistrarPago(api, payload) {
  return api.post('/pagos/', payload)
}

/**
 * @param {import('axios').AxiosInstance} api
 * @param {number} ordenId
 * @param {string|null} observacionesEntrega
 */
export function ejecutarEntregarVehiculo(api, ordenId, observacionesEntrega = null) {
  return api.post(`/ordenes-trabajo/${ordenId}/entregar`, {
    observaciones_entrega: observacionesEntrega,
  })
}

/** Refetch A0 tras error de negocio desalineado (400/409). No aplica a red/timeout. */
export function debeRefetchA0TrasError(err) {
  const status = err?.response?.status
  return status === 400 || status === 409
}
