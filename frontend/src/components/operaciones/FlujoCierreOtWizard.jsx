import { useCallback, useEffect, useState } from 'react'
import Modal from '../Modal'
import FlujoCrearVentaOtModal from './FlujoCrearVentaOtModal'
import FlujoRegistrarPagoModal from './FlujoRegistrarPagoModal'
import FlujoEntregarVehiculoModal from './FlujoEntregarVehiculoModal'
import {
  PASO_CREAR_VENTA,
  PASO_ENTREGAR,
  PASO_REGISTRAR_PAGO,
  accionPorCodigo,
  buscarItemEnBandejas,
  etiquetaPaso,
  indicePaso,
  primerPasoPermitido,
  siguientePasoPermitido,
} from '../../utils/flujoCajaPasos'

function formatearMoneda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '—'
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(valor))
}

function tituloWizard(item) {
  if (item?.tipo_entidad === 'venta') {
    return `Continuar proceso — Venta #${item.id}`
  }
  return `Continuar proceso — ${item?.numero_orden || `OT #${item?.id}`}`
}

/**
 * P4.2 — Wizard guiado: crear venta → pago → entrega.
 * Orquesta modales P4.1 en modo embedded; mutaciones vía accionesCajaApi.
 */
export default function FlujoCierreOtWizard({
  itemInicial,
  abierto,
  onCerrar,
  onRefetchA0,
  onExitoFinal,
  onErrorNegocio,
}) {
  const [itemActual, setItemActual] = useState(null)
  const [pasoActual, setPasoActual] = useState(null)
  const [refetching, setRefetching] = useState(false)
  const [mensajeParcial, setMensajeParcial] = useState(null)
  const [bloqueoPaso, setBloqueoPaso] = useState(null)

  useEffect(() => {
    if (abierto && itemInicial) {
      setItemActual(itemInicial)
      setPasoActual(primerPasoPermitido(itemInicial.acciones))
      setMensajeParcial(null)
      setBloqueoPaso(null)
      setRefetching(false)
    }
  }, [abierto, itemInicial])

  const cerrar = useCallback(() => {
    if (refetching) return
    onCerrar?.()
  }, [refetching, onCerrar])

  const sincronizarTrasMutacion = useCallback(
    async (pasoCompletado, resultadoPago) => {
      setRefetching(true)
      setBloqueoPaso(null)
      setMensajeParcial(null)
      try {
        const data = await onRefetchA0()
        if (!data?.bandejas) {
          onExitoFinal?.()
          onCerrar?.()
          return
        }

        const actualizado = buscarItemEnBandejas(data.bandejas, itemActual || itemInicial)
        const refItem = itemInicial

        if (pasoCompletado === PASO_REGISTRAR_PAGO) {
          const estadoVenta = resultadoPago?.estado_venta?.toUpperCase?.() || ''
          if (estadoVenta && estadoVenta !== 'PAGADA') {
            const saldo =
              actualizado?.saldo_pendiente ??
              accionPorCodigo(actualizado?.acciones, 'registrar_pago')?.contexto?.saldo_pendiente
            setMensajeParcial(
              saldo != null
                ? `Pago parcial registrado. Saldo pendiente: ${formatearMoneda(saldo)}.`
                : 'Pago parcial registrado. Aún hay saldo pendiente.'
            )
            setItemActual(actualizado || refItem)
            setPasoActual(null)
            return
          }
        }

        if (!actualizado) {
          onExitoFinal?.()
          onCerrar?.()
          return
        }

        setItemActual(actualizado)
        const siguiente = siguientePasoPermitido(actualizado.acciones, pasoCompletado)

        if (siguiente === PASO_ENTREGAR) {
          const entrega = accionPorCodigo(actualizado.acciones, 'entregar_vehiculo')
          if (!entrega?.permitida) {
            setBloqueoPaso({
              paso: PASO_ENTREGAR,
              motivo: entrega?.motivo_bloqueo || 'La entrega no está disponible todavía.',
            })
            setPasoActual(null)
            return
          }
        }

        if (siguiente) {
          if (siguiente === PASO_REGISTRAR_PAGO) {
            const pago = accionPorCodigo(actualizado.acciones, 'registrar_pago')
            if (!pago?.permitida) {
              setBloqueoPaso({
                paso: PASO_REGISTRAR_PAGO,
                motivo: pago?.motivo_bloqueo || 'No se puede registrar el pago.',
                codigo: pago?.codigo_bloqueo,
              })
              setPasoActual(null)
              return
            }
          }
          setPasoActual(siguiente)
          return
        }

        onExitoFinal?.()
        onCerrar?.()
      } finally {
        setRefetching(false)
      }
    },
    [itemActual, itemInicial, onRefetchA0, onExitoFinal, onCerrar]
  )

  const handleCrearVentaExito = useCallback(
    async (data) => {
      await sincronizarTrasMutacion(PASO_CREAR_VENTA, data)
    },
    [sincronizarTrasMutacion]
  )

  const handlePagoExito = useCallback(
    async (data) => {
      await sincronizarTrasMutacion(PASO_REGISTRAR_PAGO, data)
    },
    [sincronizarTrasMutacion]
  )

  const handleEntregaExito = useCallback(async () => {
    setRefetching(true)
    try {
      await onRefetchA0()
      onExitoFinal?.()
      onCerrar?.()
    } finally {
      setRefetching(false)
    }
  }, [onRefetchA0, onExitoFinal, onCerrar])

  if (!itemInicial) return null

  const accionPago = itemActual
    ? accionPorCodigo(itemActual.acciones, 'registrar_pago')
    : null

  const pasoVisible = pasoActual && !mensajeParcial && !bloqueoPaso

  return (
    <Modal titulo={tituloWizard(itemActual || itemInicial)} abierto={abierto} onCerrar={cerrar}>
      <div className="space-y-4">
        {pasoVisible && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="font-medium text-primary-700">
              Paso {indicePaso(pasoActual)} de 3
            </span>
            <span>—</span>
            <span>{etiquetaPaso(pasoActual)}</span>
          </div>
        )}

        {refetching && (
          <p className="text-sm text-slate-600 py-2">Actualizando bandejas...</p>
        )}

        {mensajeParcial && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <p className="font-medium">Proceso pausado</p>
            <p className="mt-1">{mensajeParcial}</p>
            <button
              type="button"
              onClick={cerrar}
              className="mt-3 min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 touch-manipulation"
            >
              Cerrar
            </button>
          </div>
        )}

        {bloqueoPaso && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800">
            <p className="font-medium">No se puede continuar — {etiquetaPaso(bloqueoPaso.paso)}</p>
            <p className="mt-1 text-slate-600">{bloqueoPaso.motivo}</p>
            {bloqueoPaso.codigo === 'TURNO_CERRADO' && (
              <p className="mt-2 text-xs text-slate-500">
                Abre turno en el módulo Caja y vuelve a intentar desde esta bandeja.
              </p>
            )}
            <button
              type="button"
              onClick={cerrar}
              className="mt-3 min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 touch-manipulation"
            >
              Cerrar
            </button>
          </div>
        )}

        {!refetching && !mensajeParcial && !bloqueoPaso && pasoActual === PASO_CREAR_VENTA && (
          <FlujoCrearVentaOtModal
            item={itemActual || itemInicial}
            abierto
            embedded
            onCerrar={cerrar}
            onExito={handleCrearVentaExito}
            onErrorNegocio={onErrorNegocio}
          />
        )}

        {!refetching && !mensajeParcial && !bloqueoPaso && pasoActual === PASO_REGISTRAR_PAGO && (
          <FlujoRegistrarPagoModal
            item={itemActual || itemInicial}
            accionRegistrarPago={accionPago}
            abierto
            embedded
            onCerrar={cerrar}
            onExito={handlePagoExito}
            onErrorNegocio={onErrorNegocio}
          />
        )}

        {!refetching && !mensajeParcial && !bloqueoPaso && pasoActual === PASO_ENTREGAR && (
          <FlujoEntregarVehiculoModal
            item={itemActual || itemInicial}
            abierto
            embedded
            onCerrar={cerrar}
            onExito={handleEntregaExito}
            onErrorNegocio={onErrorNegocio}
          />
        )}
      </div>
    </Modal>
  )
}
