import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../services/api'
import { mensajeErrorCambioEstado } from '../../utils/citaEstados'
import {
  ACCIONES_CITA_LABELS,
  ACCIONES_CITA_RECEPCION,
  marcarAsistenciaCita,
} from '../../utils/accionesCitaApi'
import { showError, showSuccess } from '../../utils/toast'

/**
 * Renderiza acciones cita desde acciones[] A0 — sin lógica local de rol/estado.
 */
export default function AccionesCitaRenderer({
  acciones = [],
  citaId,
  disabled = false,
  onExito,
}) {
  const navigate = useNavigate()
  const [ejecutando, setEjecutando] = useState(null)

  const visibles = (acciones || []).filter((a) => ACCIONES_CITA_RECEPCION.includes(a.accion))
  if (visibles.length === 0) {
    return null
  }

  const accionAsistencia = visibles.find((a) => a.accion === 'marcar_asistencia_cita')
  const accionConvertir = visibles.find((a) => a.accion === 'convertir_cita_ot')

  const handleMarcar = async (nuevoEstado) => {
    if (!accionAsistencia?.permitida || ejecutando || disabled) return
    setEjecutando(nuevoEstado)
    try {
      await marcarAsistenciaCita(api, citaId, nuevoEstado)
      showSuccess('Asistencia registrada correctamente.')
      onExito?.('marcar_asistencia_cita')
    } catch (err) {
      showError(mensajeErrorCambioEstado(err) || err, 'No se pudo registrar la asistencia')
    } finally {
      setEjecutando(null)
    }
  }

  const handleCompletarRecepcion = () => {
    if (!accionConvertir?.permitida || disabled) return
    navigate(`/operaciones/recepcion?cita_id=${citaId}`)
  }

  const renderBloqueo = (accion) => {
    if (accion.permitida || !accion.motivo_bloqueo) return null
    return (
      <span
        key={`bloqueo-${accion.accion}`}
        title={accion.motivo_bloqueo}
        className="inline-flex min-h-[36px] items-center px-3 py-1.5 text-xs rounded-lg bg-slate-100 text-slate-500 cursor-not-allowed"
      >
        {ACCIONES_CITA_LABELS[accion.accion] || accion.accion}
      </span>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {accionAsistencia?.permitida ? (
        <>
          <button
            type="button"
            disabled={disabled || !!ejecutando}
            onClick={() => handleMarcar('SI_ASISTIO')}
            className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 touch-manipulation"
          >
            {ejecutando === 'SI_ASISTIO' ? '...' : 'Sí asistió'}
          </button>
          <button
            type="button"
            disabled={disabled || !!ejecutando}
            onClick={() => handleMarcar('NO_ASISTIO')}
            className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 touch-manipulation"
          >
            {ejecutando === 'NO_ASISTIO' ? '...' : 'No asistió'}
          </button>
        </>
      ) : (
        renderBloqueo(accionAsistencia)
      )}

      {accionConvertir?.permitida ? (
        <button
          type="button"
          disabled={disabled || !!ejecutando}
          onClick={handleCompletarRecepcion}
          className="min-h-[36px] px-3 py-1.5 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 touch-manipulation"
        >
          {ACCIONES_CITA_LABELS.convertir_cita_ot}
        </button>
      ) : (
        renderBloqueo(accionConvertir)
      )}
    </div>
  )
}
