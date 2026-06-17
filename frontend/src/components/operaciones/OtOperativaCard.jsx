import { Link } from 'react-router-dom'
import EstadoOTBadge from '../EstadoOTBadge'
import AccionesOtRenderer from './AccionesOtRenderer'
import { formatearFechaIngresoOtLocal } from '../../utils/fechas'

const DefaultAccionesRenderer = AccionesOtRenderer

function formatearFechaEvento(iso) {
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

function formatearMoneda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '—'
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(valor))
}

/**
 * Tarjeta mínima OT desde ítem A0 (bandejas ot_*).
 */
export default function OtOperativaCard({
  item,
  showTecnico = false,
  onAccionExito,
  soloLectura = false,
  AccionesRenderer = DefaultAccionesRenderer,
}) {
  const fechaDisplay = item.fecha_finalizacion
    ? formatearFechaEvento(item.fecha_finalizacion)
    : formatearFechaIngresoOtLocal(item.fecha_ingreso)
  const etiqueta = item.etiqueta_estado || item.estado_operativo || item.estado
  const prioridad = item.prioridad_sugerida || item.prioridad

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
        <div>
          <p className="font-semibold text-slate-900">{item.numero_orden}</p>
          <p className="text-sm text-slate-600">{item.cliente_nombre || '—'}</p>
          <p className="text-sm text-slate-500">{item.vehiculo_resumen || '—'}</p>
        </div>
        <EstadoOTBadge estado={item.estado_operativo || item.estado} size="md" />
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500 mb-3">
        <div>
          <dt className="inline">Estado: </dt>
          <dd className="inline text-slate-700">{etiqueta}</dd>
        </div>
        <div>
          <dt className="inline">Prioridad: </dt>
          <dd className="inline text-slate-700">{prioridad || '—'}</dd>
        </div>
        <div className="col-span-2">
          <dt className="inline">Fecha: </dt>
          <dd className="inline text-slate-700">{fechaDisplay}</dd>
        </div>
        {showTecnico && item.tecnico_nombre && (
          <div className="col-span-2">
            <dt className="inline">Técnico: </dt>
            <dd className="inline text-slate-700">{item.tecnico_nombre}</dd>
          </div>
        )}
        {item.id_venta != null && (
          <div>
            <dt className="inline">Venta: </dt>
            <dd className="inline text-slate-700">#{item.id_venta}</dd>
          </div>
        )}
        {item.saldo_pendiente != null && (
          <div>
            <dt className="inline">Saldo: </dt>
            <dd className="inline font-medium text-amber-700">
              {formatearMoneda(item.saldo_pendiente)}
            </dd>
          </div>
        )}
      </dl>

      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
        {!soloLectura ? (
          <AccionesRenderer
            acciones={item.acciones}
            ordenId={item.id}
            item={item}
            onExito={onAccionExito}
          />
        ) : (
          <span className="text-xs text-slate-400">Solo lectura</span>
        )}
        <Link
          to={`/ordenes-trabajo/${item.id}`}
          className="text-sm text-primary-600 hover:text-primary-700 min-h-[36px] inline-flex items-center touch-manipulation"
        >
          Ver detalle
        </Link>
      </div>
    </article>
  )
}
