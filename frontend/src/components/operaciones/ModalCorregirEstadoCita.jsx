import { useEffect, useMemo, useState } from 'react'
import api from '../../services/api'
import Modal from '../Modal'
import {
  MOTIVOS_CORRECCION,
  MOTIVO_DETALLE_MIN,
  badgeEstadoCita,
  labelEstadoCita,
  mensajeErrorCambioEstado,
} from '../../utils/citaEstados'
import { showSuccess } from '../../utils/toast'

/**
 * Corrección de estado de cita usando transiciones permitidas por el backend.
 */
export default function ModalCorregirEstadoCita({ cita, abierto, onCerrar, onSuccess }) {
  const [estadoDestino, setEstadoDestino] = useState('')
  const [motivoCodigo, setMotivoCodigo] = useState('ERROR_CAPTURA')
  const [motivoDetalle, setMotivoDetalle] = useState('')
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const meta = cita?.estado_meta
  const transiciones = meta?.transiciones_permitidas ?? []
  const tieneOt = meta?.tiene_ot || Boolean(cita?.id_orden)
  const esCancelacion = estadoDestino === 'CANCELADA'

  const transicionesCorreccion = useMemo(
    () => transiciones.filter((t) => t !== cita?.estado),
    [transiciones, cita?.estado]
  )

  useEffect(() => {
    if (!abierto) return
    setError('')
    setMotivoCodigo('ERROR_CAPTURA')
    setMotivoDetalle('')
    setMotivoCancelacion('')
    setEstadoDestino(transicionesCorreccion[0] || '')
  }, [abierto, cita?.id_cita, transicionesCorreccion])

  const validar = () => {
    if (!estadoDestino) {
      setError('Selecciona el estado destino.')
      return false
    }
    if (esCancelacion) {
      if (!(motivoCancelacion || '').trim()) {
        setError('Indica el motivo de la cancelación.')
        return false
      }
      return true
    }
    if (!motivoCodigo) {
      setError('Selecciona el motivo de la corrección.')
      return false
    }
    if (motivoCodigo === 'OTRO') {
      const det = (motivoDetalle || '').trim()
      if (det.length < MOTIVO_DETALLE_MIN) {
        setError(`Describe el motivo con al menos ${MOTIVO_DETALLE_MIN} caracteres.`)
        return false
      }
    }
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!validar()) return

    const confirmMsg = tieneOt
      ? 'Esta cita tiene OT vinculada. La corrección quedará auditada. ¿Continuar?'
      : `¿Confirmar cambio de "${labelEstadoCita(cita.estado)}" a "${labelEstadoCita(estadoDestino)}"?`

    if (!window.confirm(confirmMsg)) return

    const payload = { estado_nuevo: estadoDestino }
    if (esCancelacion) {
      payload.motivo_cancelacion = motivoCancelacion.trim()
      if (motivoCodigo) {
        payload.motivo_codigo = motivoCodigo
        if (motivoCodigo === 'OTRO' && motivoDetalle.trim()) {
          payload.motivo_detalle = motivoDetalle.trim()
        } else if (motivoCodigo !== 'OTRO') {
          payload.motivo_detalle = motivoDetalle.trim() || undefined
        }
      }
    } else {
      payload.motivo_codigo = motivoCodigo
      if (motivoCodigo === 'OTRO') {
        payload.motivo_detalle = motivoDetalle.trim()
      } else if (motivoDetalle.trim()) {
        payload.motivo_detalle = motivoDetalle.trim()
      }
    }

    setEnviando(true)
    try {
      const res = await api.patch(`/citas/${cita.id_cita}/estado`, payload)
      showSuccess('Estado de la cita actualizado.')
      onSuccess?.(res.data)
      onCerrar?.()
    } catch (err) {
      setError(mensajeErrorCambioEstado(err) || 'No se pudo corregir el estado de la cita.')
    } finally {
      setEnviando(false)
    }
  }

  if (!cita) return null

  return (
    <Modal
      titulo={cita.estado === 'CANCELADA' ? 'Reactivar cita' : 'Corregir estado'}
      abierto={abierto}
      onCerrar={onCerrar}
      zIndex={60}
    >
      {transicionesCorreccion.length === 0 ? (
        <p className="text-sm text-slate-600">
          No hay correcciones disponibles para esta cita con tu rol o en el estado actual.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-100">{error}</div>
          )}

          <div>
            <p className="text-sm text-slate-600 mb-1">Estado actual</p>
            <span className={`inline-flex px-2 py-1 rounded text-sm font-medium ${badgeEstadoCita(cita.estado)}`}>
              {labelEstadoCita(cita.estado)}
            </span>
          </div>

          {tieneOt && (
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-900">
              Esta cita tiene una OT vinculada. La corrección requiere autorización administrativa y queda registrada en auditoría.
            </div>
          )}

          {meta?.bloqueo_financiero && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
              Esta cita no puede corregirse porque la OT tiene venta o pagos asociados.
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Estado destino</label>
            <select
              value={estadoDestino}
              onChange={(e) => setEstadoDestino(e.target.value)}
              className="w-full px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-sm"
              required
            >
              {transicionesCorreccion.map((t) => (
                <option key={t} value={t}>
                  {labelEstadoCita(t)}
                </option>
              ))}
            </select>
          </div>

          {esCancelacion ? (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Motivo de cancelación</label>
              <textarea
                value={motivoCancelacion}
                onChange={(e) => setMotivoCancelacion(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                placeholder="Ej: cliente reprogramó, emergencia..."
                required
              />
            </div>
          ) : null}

          {!esCancelacion && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Motivo de corrección</label>
                <select
                  value={motivoCodigo}
                  onChange={(e) => setMotivoCodigo(e.target.value)}
                  className="w-full px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-sm"
                  required
                >
                  {MOTIVOS_CORRECCION.map((m) => (
                    <option key={m.codigo} value={m.codigo}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Detalle {motivoCodigo === 'OTRO' ? `(mín. ${MOTIVO_DETALLE_MIN} caracteres)` : '(opcional)'}
                </label>
                <textarea
                  value={motivoDetalle}
                  onChange={(e) => setMotivoDetalle(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="Describe brevemente la corrección..."
                  required={motivoCodigo === 'OTRO'}
                />
              </div>
            </>
          )}

          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onCerrar}
              className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando || meta?.bloqueo_financiero}
              className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {enviando ? 'Guardando...' : 'Confirmar corrección'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}
