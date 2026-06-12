import { ACCIONES_CAJA } from './accionesCaja'

/** CTA único P4.2 — neutral para cobro (O1/V1) y entrega (O2). */
export const CTA_FLUJO_CAJA = 'Continuar proceso'

export const PASO_CREAR_VENTA = 'crear_venta'
export const PASO_REGISTRAR_PAGO = 'registrar_pago'
export const PASO_ENTREGAR = 'entregar_vehiculo'

const MAP_ACCION_PASO = {
  crear_venta_desde_ot: PASO_CREAR_VENTA,
  registrar_pago: PASO_REGISTRAR_PAGO,
  entregar_vehiculo: PASO_ENTREGAR,
}

const ORDEN_PASOS = [PASO_CREAR_VENTA, PASO_REGISTRAR_PAGO, PASO_ENTREGAR]

export function accionPorCodigo(acciones, codigo) {
  return (acciones || []).find((a) => a.accion === codigo)
}

/** True si alguna acción financiera caja está permitida en el ítem. */
export function hayAccionCajaPermitida(acciones) {
  return ACCIONES_CAJA.some((codigo) => accionPorCodigo(acciones, codigo)?.permitida === true)
}

/** Primer paso del wizard según prioridad canónica y acciones[] A0. */
export function primerPasoPermitido(acciones) {
  for (const codigo of ACCIONES_CAJA) {
    const acc = accionPorCodigo(acciones, codigo)
    if (acc?.permitida) {
      return MAP_ACCION_PASO[codigo]
    }
  }
  return null
}

/** Siguiente paso tras refetch; null si el flujo guiado debe terminar. */
export function siguientePasoPermitido(acciones, pasoActual) {
  const idx = ORDEN_PASOS.indexOf(pasoActual)
  if (idx < 0) return null
  for (let i = idx + 1; i < ORDEN_PASOS.length; i += 1) {
    const paso = ORDEN_PASOS[i]
    const codigo = Object.entries(MAP_ACCION_PASO).find(([, p]) => p === paso)?.[0]
    if (codigo && accionPorCodigo(acciones, codigo)?.permitida) {
      return paso
    }
  }
  return null
}

/** Localiza ítem actualizado en bandejas A0 tras refetch. */
export function buscarItemEnBandejas(bandejas, itemRef) {
  if (!bandejas || !itemRef) return null
  const id = itemRef.id
  const tipo = itemRef.tipo_entidad
  const listas = [
    bandejas.ot_pendientes_cobro?.items,
    bandejas.ot_listas_entrega?.items,
    bandejas.ventas_saldo_pendiente?.items,
  ]
  for (const items of listas) {
    if (!items?.length) continue
    const found = items.find(
      (i) => i.id === id && (!tipo || i.tipo_entidad === tipo || !i.tipo_entidad)
    )
    if (found) return found
  }
  for (const items of listas) {
    if (!items?.length) continue
    const found = items.find((i) => i.id === id)
    if (found) return found
  }
  return null
}

export function etiquetaPaso(paso) {
  switch (paso) {
    case PASO_CREAR_VENTA:
      return 'Crear venta'
    case PASO_REGISTRAR_PAGO:
      return 'Registrar pago'
    case PASO_ENTREGAR:
      return 'Entregar vehículo'
    default:
      return paso
  }
}

export function indicePaso(paso) {
  const idx = ORDEN_PASOS.indexOf(paso)
  return idx >= 0 ? idx + 1 : 1
}
