import { Link } from 'react-router-dom'
import { badgeEstadoCita, labelEstadoCita } from '../../utils/citaEstados'
import AccionesCitaRenderer from './AccionesCitaRenderer'

const DefaultAccionesRenderer = AccionesCitaRenderer

function formatearFecha(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-MX', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

/**
 * Tarjeta mínima cita desde ítem A0 (bandejas citas_*).
 */
export default function CitaOperativaCard({
  item,
  onAccionExito,
  AccionesRenderer = DefaultAccionesRenderer,
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
        <div>
          <p className="font-semibold text-slate-900">Cita #{item.id}</p>
          <p className="text-sm text-slate-600">{item.cliente_nombre || '—'}</p>
          <p className="text-sm text-slate-500">{item.vehiculo_resumen || '—'}</p>
        </div>
        <span
          className={`inline-flex px-2 py-1 rounded text-xs font-medium ${badgeEstadoCita(item.estado)}`}
        >
          {labelEstadoCita(item.estado)}
        </span>
      </div>

      <dl className="grid grid-cols-1 gap-y-1 text-xs text-slate-500 mb-3">
        <div>
          <dt className="inline">Fecha: </dt>
          <dd className="inline text-slate-700">{formatearFecha(item.fecha_hora)}</dd>
        </div>
      </dl>

      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
        <AccionesRenderer
          acciones={item.acciones}
          citaId={item.id}
          item={item}
          onExito={onAccionExito}
        />
        <Link
          to="/citas"
          className="text-sm text-primary-600 hover:text-primary-700 min-h-[36px] inline-flex items-center touch-manipulation"
        >
          Ver en Citas
        </Link>
      </div>
    </article>
  )
}
