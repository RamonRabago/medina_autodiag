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

/** Mensaje global coherente cuando el backend dice «verde» pero hay copy de áreas ambiguo. */
export function mensajeSaludGlobal(salud) {
  const global = (salud?.global ?? 'verde').toLowerCase()
  if (global === 'verde') return 'Operación estable'
  return salud?.mensaje ?? 'Estado del taller'
}

/** Suaviza mensajes de área verde cuando el global también es verde. */
export function mensajeSaludArea(area, globalEstado) {
  const msg = area?.mensaje ?? ''
  const estado = (area?.estado ?? 'verde').toLowerCase()
  const global = (globalEstado ?? 'verde').toLowerCase()

  if (global === 'verde' && estado === 'verde') {
    if (/^sin pendientes relevantes/i.test(msg)) return msg
    if (/^atención baja/i.test(msg)) return 'Pendientes menores, sin urgencia'
  }
  return msg || 'Sin pendientes relevantes'
}

/** Oculta líneas con score; humaniza antigüedad y montos del backend. */
export function humanizarExplicacion(linea, grupo) {
  if (!linea || typeof linea !== 'string') return null
  if (/score|decision_score|prioridad operativa \(score/i.test(linea)) return null

  const diasMatch = linea.match(/Lleva\s+([\d.]+)\s+d[ií]as?\s+sin atenci[oó]n/i)
  if (diasMatch) {
    const dias = Math.round(parseFloat(diasMatch[1]))
    const unidad = dias === 1 ? 'día' : 'días'
    if (grupo === 'cobros' || /cobro/i.test(linea)) {
      return `Este cobro lleva ${dias} ${unidad} detenido`
    }
    return `Hace ${dias} ${unidad} que está pendiente`
  }

  const horasMatch = linea.match(/Lleva\s+([\d.]+)\s+h\s+sin atenci[oó]n/i)
  if (horasMatch) {
    const horas = Math.round(parseFloat(horasMatch[1]))
    const unidad = horas === 1 ? 'hora' : 'horas'
    if (grupo === 'cobros') return `Este cobro lleva ${horas} ${unidad} detenido`
    return `Hace ${horas} ${unidad} que está pendiente`
  }

  const minMatch = linea.match(/Lleva\s+([\d.]+)\s+min\s+sin atenci[oó]n/i)
  if (minMatch) {
    const min = Math.round(parseFloat(minMatch[1]))
    if (grupo === 'cobros') return `Este cobro lleva ${min} min detenido`
    return `Hace ${min} min que está pendiente`
  }

  const montoMatch = linea.match(/Monto involucrado:\s*(.+)/i)
  if (montoMatch) return `Monto pendiente: ${montoMatch[1].trim()}`

  const eventoMatch = linea.match(/Evento en\s+(.+)/i)
  if (eventoMatch) return `Próximo evento en ${eventoMatch[1].trim()}`

  return linea
}

/** CTA: respeta accion_label del backend; si es genérico, infiere acción por grupo/título. */
export function resolverCtaLabel(recomendacion) {
  const custom = recomendacion?.accion_label?.trim()
  if (custom && !/^ir(\s+ahora)?$/i.test(custom)) return custom

  const grupo = (recomendacion?.grupo ?? '').toLowerCase()
  const titulo = (recomendacion?.titulo ?? '').toLowerCase()

  if (grupo === 'cobros' || titulo.includes('cobro')) return 'Registrar cobro'
  if (grupo === 'entregas' || titulo.includes('entrega')) return 'Gestionar entrega'
  if (grupo === 'citas' || titulo.includes('cita')) return 'Atender cita'
  if (grupo === 'autorizaciones' || titulo.includes('autoriz')) return 'Revisar autorización'
  if (grupo === 'inventario' || titulo.includes('stock') || titulo.includes('inventario')) {
    return 'Revisar inventario'
  }
  if (grupo === 'caja') return 'Ir a caja'
  if (titulo.includes('ot ') || titulo.startsWith('ot ')) return 'Ver OT'

  return 'Ir ahora'
}

/** Encabezado escaneable por grupo — solo presenta total del backend. */
export function encabezadoGrupoPrioridad(grupo, total) {
  const t = Number(total) || 0
  const titulo = GRUPO_TITULO_CORTO[grupo] ?? grupo ?? 'Prioridades'

  const sufijos = {
    cobros: `${t} pendiente${t !== 1 ? 's' : ''}`,
    entregas: `${t} vehículo${t !== 1 ? 's' : ''} listo${t !== 1 ? 's' : ''}`,
    citas: `${t} requieren atención`,
    autorizaciones: `${t} pendiente${t !== 1 ? 's' : ''}`,
    inventario: `${t} alerta${t !== 1 ? 's' : ''}`,
    caja: `${t} pendiente${t !== 1 ? 's' : ''}`,
  }

  const sufijo = sufijos[grupo] ?? `${t} pendiente${t !== 1 ? 's' : ''}`
  return `${titulo} — ${sufijo}`
}
