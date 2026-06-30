import { Link } from 'react-router-dom'
import {
  SEVERIDAD_BADGE,
  SEVERIDAD_HERO_BG,
  SEVERIDAD_HERO_BORDER,
  etiquetaHero,
  humanizarExplicacion,
  mostrarBadgeSeveridad,
  resolverCtaLabel,
  SEVERIDAD_ETIQUETA,
} from './dashboardV2Styles'

/**
 * Hero — recomendación inteligente (render puro del backend).
 */
export default function DashboardV2Recomendacion({ recomendacion }) {
  if (!recomendacion?.titulo) {
    return (
      <section className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        No hay recomendación disponible en este momento.
      </section>
    )
  }

  const severidad = recomendacion.severidad ?? 'estable'
  const borderClass = SEVERIDAD_HERO_BORDER[severidad] ?? SEVERIDAD_HERO_BORDER.estable
  const bgClass = SEVERIDAD_HERO_BG[severidad] ?? SEVERIDAD_HERO_BG.estable
  const grupo = recomendacion.grupo ?? ''
  const explicacion = (Array.isArray(recomendacion.explicacion) ? recomendacion.explicacion : [])
    .map((linea) => humanizarExplicacion(linea, grupo))
    .filter(Boolean)
    .slice(0, 2)
  const ctaLabel = resolverCtaLabel(recomendacion)

  return (
    <section
      className={`mb-4 sm:mb-5 rounded-xl border border-slate-200 shadow-lg border-l-[5px] ${borderClass} ${bgClass} overflow-hidden ring-1 ring-slate-900/5`}
      aria-labelledby="dashboard-recomendacion-titulo"
    >
      <div className="px-4 py-3 sm:px-5 sm:py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-primary-800">
              {etiquetaHero(severidad)}
            </span>
            {mostrarBadgeSeveridad(severidad) && (
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${SEVERIDAD_BADGE[severidad]}`}
              >
                {SEVERIDAD_ETIQUETA[severidad] ?? severidad}
              </span>
            )}
          </div>
          <h2
            id="dashboard-recomendacion-titulo"
            className="text-lg sm:text-xl font-bold text-slate-900 leading-tight"
          >
            {recomendacion.titulo}
          </h2>
          {explicacion.length > 0 && (
            <p className="mt-1.5 text-xs sm:text-sm text-slate-600 line-clamp-2">{explicacion.join(' · ')}</p>
          )}
        </div>
        {recomendacion.to && (
          <Link
            to={recomendacion.to}
            className="shrink-0 inline-flex items-center justify-center min-h-[44px] px-5 py-2 rounded-lg bg-primary-600 text-white font-semibold text-sm shadow-md hover:bg-primary-700 active:bg-primary-800 transition-colors touch-manipulation w-full sm:w-auto"
          >
            {ctaLabel} →
          </Link>
        )}
      </div>
    </section>
  )
}
