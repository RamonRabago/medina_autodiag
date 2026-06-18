/** @typedef {'normal' | 'atencion' | 'urgente'} GrupoSeveridad */

export const GRUPO_IDS = {
  CAJA: 'caja',
  RECEPCION: 'recepcion',
  MI_TALLER: 'mi_taller',
  REFACCIONES: 'refacciones',
}

export const BANDEJA_IDS = {
  PENDIENTES: 'pendientes',
  EN_PROCESO: 'en_proceso',
  COMPLETADAS: 'completadas',
}

const AUTO_EXPAND_PRIORITY = [GRUPO_IDS.CAJA, GRUPO_IDS.RECEPCION, GRUPO_IDS.MI_TALLER]

/** @type {import('./operacionesGrupos.js').GrupoDashboardConfig[]} */
export const GRUPOS_DASHBOARD = [
  {
    id: GRUPO_IDS.CAJA,
    label: 'Caja',
    route: '/operaciones/caja',
    kpis: [
      {
        metricKey: 'ot_pendientes_cobro',
        label: 'Por cobrar (O1)',
        hint: 'Completadas pendientes de cobro',
        to: '/operaciones/caja',
        urgentWhen: (v) => v > 0,
      },
      {
        metricKey: 'ot_listas_entrega',
        label: 'Listas para entrega (O2)',
        hint: 'Listas para entregar',
        to: '/operaciones/caja',
      },
      {
        metricKey: 'ventas_saldo_pendiente',
        label: 'Ventas con saldo (V1)',
        hint: 'Saldo pendiente en mostrador',
        to: '/operaciones/caja',
        urgentWhen: (v) => v > 0,
      },
    ],
  },
  {
    id: GRUPO_IDS.RECEPCION,
    label: 'Recepción',
    route: '/operaciones/recepcion',
    kpis: [
      {
        metricKey: 'citas_pendientes_asistencia',
        label: 'Citas sin asistencia',
        hint: 'Confirmadas sin registrar asistencia',
        to: '/citas',
        urgentWhen: (v) => v > 0,
      },
      {
        metricKey: 'citas_convertibles',
        label: 'Citas convertibles',
        hint: 'Listas para recepción',
        to: '/operaciones/recepcion',
        attentionWhen: (v) => v > 0,
      },
    ],
  },
  {
    id: GRUPO_IDS.MI_TALLER,
    label: 'Mi Taller',
    route: '/operaciones/mi-taller',
    kpis: [
      {
        metricKey: 'ot_pendientes',
        label: 'OT pendientes',
        hint: 'Por iniciar',
        to: '/operaciones/mi-taller',
        attentionWhen: (v) => v > 0,
      },
      {
        metricKey: 'ot_en_proceso',
        label: 'OT en proceso',
        hint: 'En taller',
        to: '/operaciones/mi-taller',
      },
      {
        metricKey: 'ot_completadas',
        label: 'OT completadas',
        hint: 'Finalizadas',
        to: '/operaciones/mi-taller',
      },
    ],
  },
  {
    id: GRUPO_IDS.REFACCIONES,
    label: 'Refacciones',
    route: '/cotizaciones-refaccion',
    kpis: [
      {
        metricKey: 'refacciones_en_compra',
        label: 'Refacciones en compra',
        hint: 'Cotizaciones en compra',
        to: '/cotizaciones-refaccion',
        attentionWhen: (v) => v > 0,
      },
      {
        metricKey: 'refacciones_recibidas_pendiente_entrega',
        label: 'Refacciones recibidas',
        hint: 'Pendientes de entrega',
        to: '/cotizaciones-refaccion',
        urgentWhen: (v) => v > 0,
      },
    ],
  },
]

function metricValue(metricas, key) {
  return metricas?.[key] ?? 0
}

export function getGrupoTotal(metricas, grupoId) {
  const grupo = GRUPOS_DASHBOARD.find((g) => g.id === grupoId)
  if (!grupo) return 0
  return grupo.kpis.reduce((sum, kpi) => sum + metricValue(metricas, kpi.metricKey), 0)
}

/**
 * @param {Record<string, number>|undefined} metricas
 * @param {string} grupoId
 * @returns {GrupoSeveridad}
 */
export function getGrupoSeveridad(metricas, grupoId) {
  const o1 = metricValue(metricas, 'ot_pendientes_cobro')
  const v1 = metricValue(metricas, 'ventas_saldo_pendiente')
  const o2 = metricValue(metricas, 'ot_listas_entrega')
  const sinAsistencia = metricValue(metricas, 'citas_pendientes_asistencia')
  const convertibles = metricValue(metricas, 'citas_convertibles')
  const otPendientes = metricValue(metricas, 'ot_pendientes')
  const enCompra = metricValue(metricas, 'refacciones_en_compra')
  const recibidas = metricValue(metricas, 'refacciones_recibidas_pendiente_entrega')

  switch (grupoId) {
    case GRUPO_IDS.CAJA:
      if (o1 > 0 || v1 > 0) return 'urgente'
      if (o2 > 0) return 'atencion'
      return 'normal'
    case GRUPO_IDS.RECEPCION:
      if (sinAsistencia > 0) return 'urgente'
      if (convertibles > 0) return 'atencion'
      return 'normal'
    case GRUPO_IDS.MI_TALLER:
      if (otPendientes > 0) return 'atencion'
      return 'normal'
    case GRUPO_IDS.REFACCIONES:
      if (recibidas > 0) return 'urgente'
      if (enCompra > 0) return 'atencion'
      return 'normal'
    default:
      return 'normal'
  }
}

const SUBTEXTO_PARTS = {
  [GRUPO_IDS.CAJA]: (m) => {
    const parts = []
    const o1 = metricValue(m, 'ot_pendientes_cobro')
    const o2 = metricValue(m, 'ot_listas_entrega')
    const v1 = metricValue(m, 'ventas_saldo_pendiente')
    if (o1 > 0) parts.push(`${o1} por cobrar`)
    if (o2 > 0) parts.push(`${o2} entrega${o2 === 1 ? '' : 's'}`)
    if (v1 > 0) parts.push(`${v1} venta${v1 === 1 ? '' : 's'} saldo`)
    return parts
  },
  [GRUPO_IDS.RECEPCION]: (m) => {
    const parts = []
    const sinAsistencia = metricValue(m, 'citas_pendientes_asistencia')
    const convertibles = metricValue(m, 'citas_convertibles')
    if (sinAsistencia > 0) parts.push(`${sinAsistencia} sin asistencia`)
    if (convertibles > 0) parts.push(`${convertibles} convertible${convertibles === 1 ? '' : 's'}`)
    return parts
  },
  [GRUPO_IDS.MI_TALLER]: (m) => {
    const parts = []
    const pendientes = metricValue(m, 'ot_pendientes')
    const enProceso = metricValue(m, 'ot_en_proceso')
    if (pendientes > 0) parts.push(`${pendientes} pendiente${pendientes === 1 ? '' : 's'}`)
    if (enProceso > 0) parts.push(`${enProceso} en proceso`)
    return parts
  },
  [GRUPO_IDS.REFACCIONES]: (m) => {
    const parts = []
    const enCompra = metricValue(m, 'refacciones_en_compra')
    const recibidas = metricValue(m, 'refacciones_recibidas_pendiente_entrega')
    if (enCompra > 0) parts.push(`${enCompra} en compra`)
    if (recibidas > 0) parts.push(`${recibidas} pend. entrega`)
    return parts
  },
}

/** Subtexto de 1 línea para grupos con severidad atención/urgente. */
export function getGrupoSubtexto(metricas, grupoId) {
  const severidad = getGrupoSeveridad(metricas, grupoId)
  if (severidad === 'normal') return null
  const parts = SUBTEXTO_PARTS[grupoId]?.(metricas) ?? []
  return parts.length ? parts.join(' · ') : null
}

/**
 * Máx. 2 grupos auto-abiertos: Caja > Recepción > Mi Taller.
 * @param {Record<string, number>|undefined} metricas
 * @returns {Set<string>}
 */
export function computeDefaultExpandedGroups(metricas) {
  const expanded = new Set()
  for (const grupoId of AUTO_EXPAND_PRIORITY) {
    if (expanded.size >= 2) break
    const total = getGrupoTotal(metricas, grupoId)
    const severidad = getGrupoSeveridad(metricas, grupoId)
    if (total > 0 || severidad !== 'normal') {
      expanded.add(grupoId)
    }
  }
  return expanded
}

/**
 * Defaults Mi Taller (memoria React, sin persistencia).
 * ADMIN híbrido: En proceso si hay OT activas; si no, Pendientes si hay cola.
 */
export function computeDefaultExpandedMiTallerSections(rol, bandejas) {
  const pendientes = bandejas?.ot_pendientes?.total ?? 0
  const enProceso = bandejas?.ot_en_proceso?.total ?? 0
  const expanded = new Set()

  if (rol === 'ADMIN') {
    if (enProceso > 0) {
      expanded.add(BANDEJA_IDS.EN_PROCESO)
    } else if (pendientes > 0) {
      expanded.add(BANDEJA_IDS.PENDIENTES)
    }
  } else {
    if (pendientes > 0) expanded.add(BANDEJA_IDS.PENDIENTES)
    if (enProceso > 0) expanded.add(BANDEJA_IDS.EN_PROCESO)
  }

  return expanded
}

export function getKpiValueClassName(kpi, value) {
  if (kpi.urgentWhen?.(value)) return 'text-amber-600'
  return 'text-slate-800'
}
