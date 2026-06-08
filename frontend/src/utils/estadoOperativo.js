/**
 * Configuración visual de estados de orden de trabajo (compartido ERP).
 */
export const ESTADOS_OT = {
  PENDIENTE: { className: 'bg-orange-100 text-orange-800' },
  COTIZADA: { className: 'bg-orange-100 text-orange-800' },
  ESPERANDO_AUTORIZACION: { className: 'bg-orange-100 text-orange-800' },
  EN_PROCESO: { className: 'bg-green-100 text-green-800' },
  ESPERANDO_REPUESTOS: { className: 'bg-green-100 text-green-800' },
  COMPLETADA: { className: 'bg-blue-100 text-blue-800' },
  ENTREGADA: { className: 'bg-blue-100 text-blue-800' },
  CANCELADA: { className: 'bg-slate-200 text-slate-700' },
}

export function getEstadoOTConfig(estado) {
  const key = (estado || '').toUpperCase()
  const cfg = ESTADOS_OT[key]
  if (cfg) {
    return { label: estado || '-', className: cfg.className }
  }
  return { label: estado || '-', className: 'bg-slate-100 text-slate-700' }
}
