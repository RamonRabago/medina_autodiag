/** Mapeo visual severidad/estado — solo presentación, sin lógica de negocio. */

export const SEVERIDAD_BADGE = {
  critica: 'bg-red-100 text-red-800 border-red-200',
  alta: 'bg-amber-100 text-amber-900 border-amber-200',
  media: 'bg-yellow-50 text-yellow-900 border-yellow-200',
  baja: 'bg-slate-100 text-slate-700 border-slate-200',
  estable: 'bg-emerald-100 text-emerald-800 border-emerald-200',
}

export const SEVERIDAD_HERO_BORDER = {
  critica: 'border-l-red-500',
  alta: 'border-l-amber-500',
  media: 'border-l-yellow-500',
  baja: 'border-l-slate-400',
  estable: 'border-l-emerald-500',
}

export const SALUD_ESTADO = {
  verde: 'bg-emerald-500',
  amarillo: 'bg-amber-400',
  rojo: 'bg-red-500',
}

export const SALUD_AREA_LABELS = {
  recepcion: 'Recepción',
  caja: 'Caja',
  taller: 'Taller',
  inventario: 'Inventario',
}

export function formatoMoneda(valor) {
  return `$${(Number(valor) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
}
