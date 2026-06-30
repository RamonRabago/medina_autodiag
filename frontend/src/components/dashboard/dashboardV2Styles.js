/** Mapeo visual severidad/estado — solo presentación, sin lógica de negocio. */

export const SEVERIDAD_BADGE = {
  critica: 'bg-red-100 text-red-800 border-red-200',
  alta: 'bg-amber-100 text-amber-900 border-amber-200',
  media: 'bg-yellow-50 text-yellow-900 border-yellow-200',
  baja: 'bg-slate-100 text-slate-600 border-slate-200',
  estable: 'bg-emerald-100 text-emerald-800 border-emerald-200',
}

export const SEVERIDAD_HERO_BORDER = {
  critica: 'border-l-red-600',
  alta: 'border-l-amber-500',
  media: 'border-l-yellow-500',
  baja: 'border-l-primary-500',
  estable: 'border-l-emerald-500',
}

export const SEVERIDAD_HERO_BG = {
  critica: 'bg-gradient-to-r from-red-50 to-white',
  alta: 'bg-gradient-to-r from-amber-50 to-white',
  media: 'bg-gradient-to-r from-yellow-50/80 to-white',
  baja: 'bg-gradient-to-r from-primary-50/80 to-white',
  estable: 'bg-gradient-to-r from-emerald-50/70 to-white',
}

export const SEVERIDAD_GRUPO_STRIPE = {
  critica: 'border-l-red-500',
  alta: 'border-l-amber-500',
  media: 'border-l-yellow-400',
  baja: 'border-l-slate-200',
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

/** Títulos cortos por clave de grupo (presentación; orden viene del backend). */
export const GRUPO_TITULO_CORTO = {
  cobros: 'Cobros',
  entregas: 'Entregas',
  citas: 'Citas',
  autorizaciones: 'Autorizaciones',
  inventario: 'Inventario',
  caja: 'Caja',
}

export const SEVERIDAD_ETIQUETA = {
  critica: 'Urgente',
  alta: 'Alta prioridad',
  media: 'Atención',
  baja: 'Baja',
  estable: 'En orden',
}

/** Badges visibles solo cuando aportan a la decisión. */
export function mostrarBadgeSeveridad(severidad) {
  const sev = (severidad ?? '').toLowerCase()
  return sev === 'critica' || sev === 'alta' || sev === 'media'
}

export function etiquetaHero(severidad) {
  const sev = (severidad ?? 'estable').toLowerCase()
  if (sev === 'estable') return 'Operación en orden'
  if (sev === 'critica' || sev === 'alta') return 'Atención requerida'
  return 'Tu prioridad en este momento'
}

export function formatoMoneda(valor) {
  return `$${(Number(valor) || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
}
