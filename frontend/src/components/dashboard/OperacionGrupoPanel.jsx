import { Link } from 'react-router-dom'
import DisclosurePanel, { DisclosureChevron } from '../ui/DisclosurePanel'
import KPIWidget from './KPIWidget'
import {
  getGrupoSeveridad,
  getGrupoSubtexto,
  getGrupoTotal,
  getKpiValueClassName,
} from '../../utils/operacionesGrupos'

const SEVERIDAD_DOT = {
  normal: 'text-slate-300',
  atencion: 'text-amber-500',
  urgente: 'text-amber-600',
}

function GrupoSeverityBadge({ severidad }) {
  return (
    <span
      className={`text-sm font-bold ${SEVERIDAD_DOT[severidad] ?? SEVERIDAD_DOT.normal}`}
      aria-label={
        severidad === 'urgente'
          ? 'Urgente'
          : severidad === 'atencion'
            ? 'Requiere atención'
            : 'Normal'
      }
    >
      ●
    </span>
  )
}

export default function OperacionGrupoPanel({
  grupo,
  metricas,
  expanded,
  onToggle,
}) {
  const total = getGrupoTotal(metricas, grupo.id)
  const severidad = getGrupoSeveridad(metricas, grupo.id)
  const subtexto = getGrupoSubtexto(metricas, grupo.id)

  return (
    <DisclosurePanel
      id={`grupo-${grupo.id}`}
      expanded={expanded}
      onToggle={onToggle}
      className="mb-3"
      actions={
        <Link
          to={grupo.route}
          className="min-h-[52px] min-w-[52px] flex items-center justify-center px-3 text-sm font-medium text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded-lg touch-manipulation"
          aria-label={`Ir a ${grupo.label}`}
        >
          Ir →
        </Link>
      }
      trigger={
        <>
          <span className="text-sm font-semibold uppercase tracking-wide text-slate-700 shrink-0">
            {grupo.label}
          </span>
          <GrupoSeverityBadge severidad={severidad} />
          <span className="text-sm font-medium text-slate-800 shrink-0">{total}</span>
          {subtexto && (
            <span className="hidden sm:inline text-xs text-slate-500 truncate min-w-0">
              {subtexto}
            </span>
          )}
          <DisclosureChevron expanded={expanded} />
        </>
      }
    >
      <div className="px-4 py-3">
        {subtexto && <p className="sm:hidden text-xs text-slate-500 mb-3">{subtexto}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {grupo.kpis.map((kpi) => {
            const value = metricas?.[kpi.metricKey] ?? 0
            return (
              <KPIWidget
                key={kpi.metricKey}
                label={kpi.label}
                value={value}
                to={kpi.to}
                hint={kpi.hint}
                valueClassName={getKpiValueClassName(kpi, value)}
              />
            )
          })}
        </div>
      </div>
    </DisclosurePanel>
  )
}
