import { useEffect, useState } from 'react'
import Modal from '../Modal'
import api from '../../services/api'
import { debeRefetchA0TrasError, ejecutarEntregarVehiculo } from '../../utils/accionesCajaApi'
import { showError, showSuccess } from '../../utils/toast'

/**
 * Fase 4B — Entregar vehículo delegado a POST /api/ordenes-trabajo/{id}/entregar.
 * Permisos desde acciones[] A0 (bandeja O2); sin lógica local de autorización.
 */
export default function FlujoEntregarVehiculoModal({
  item,
  abierto,
  onCerrar,
  onExito,
  onErrorNegocio,
  embedded = false,
}) {
  const [observaciones, setObservaciones] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (abierto) {
      setObservaciones('')
      setEnviando(false)
    }
  }, [abierto, item?.id])

  const cerrar = () => {
    if (enviando) return
    onCerrar?.()
  }

  const confirmar = async () => {
    if (!item?.id || enviando) return
    setEnviando(true)
    try {
      const res = await ejecutarEntregarVehiculo(
        api,
        item.id,
        observaciones.trim() || null
      )
      const numero = res.data?.numero_orden || item.numero_orden
      showSuccess(numero ? `Vehículo entregado — ${numero}` : 'Vehículo entregado')
      onExito?.(res.data)
    } catch (err) {
      showError(err, 'No se pudo entregar el vehículo')
      if (debeRefetchA0TrasError(err)) {
        onErrorNegocio?.()
      }
    } finally {
      setEnviando(false)
    }
  }

  if (!item) return null

  const contenido = (
    <div className="space-y-4">
        <div className="text-sm text-slate-600 space-y-1">
          <p>{item.cliente_nombre || '—'}</p>
          <p>{item.vehiculo_resumen || '—'}</p>
          {item.id_venta != null && (
            <p className="text-slate-700">Venta #{item.id_venta} — cobrada</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Observaciones de entrega (opcional)
          </label>
          <textarea
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            disabled={enviando}
            rows={3}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm touch-manipulation disabled:opacity-50"
            placeholder="Ej. Cliente recogió llaves y factura"
          />
        </div>

        <p className="text-xs text-slate-500">
          La orden pasará a estado ENTREGADA. Esta acción no se puede deshacer desde Caja
          Operativa.
        </p>

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={cerrar}
            disabled={enviando}
            className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 touch-manipulation disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={confirmar}
            disabled={enviando}
            className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 touch-manipulation disabled:opacity-50"
          >
            {enviando ? 'Entregando...' : 'Confirmar entrega'}
          </button>
        </div>
      </div>
  )

  if (embedded) {
    if (!abierto) return null
    return contenido
  }

  return (
    <Modal
      titulo={`Entregar vehículo — ${item.numero_orden || `OT #${item.id}`}`}
      abierto={abierto}
      onCerrar={cerrar}
    >
      {contenido}
    </Modal>
  )
}
