import { Link } from 'react-router-dom'
import { SEVERIDAD_BADGE, SEVERIDAD_HERO_BORDER } from './dashboardV2Styles'

/**
 * Hero — recomendación inteligente (render puro del backend).
 */
export default function DashboardV2Recomendacion({ recomendacion }) {
  if (!recomendacion?.titulo) {
    return (
      <section className="mb-4 sm:mb-6 rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
        No hay recomendación disponible en este momento.
      </section>
    )
  }

  const severidad = recomendacion.severidad ?? 'estable'
  const borderClass = SEVERIDAD_HERO_BORDER[severidad] ?? SEVERIDAD_HERO_BORDER.estable
  const badgeClass = SEVERIDAD_BADGE[severidad] ?? SEVERIDAD_BADGE.estable
  const explicacion = Array.isArray(recomendacion.explicacion) ? recomendacion.explicacion : []

  return (
    <section
      className={`mb-4 sm:mb-6 rounded-xl border border-slate-200 bg-white shadow-md border-l-4 ${borderClass} overflow-hidden`}
      aria-labelledby="dashboard-recomendacion-titulo"
    >
      <div className="p-4 sm:p-6">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Siguiente acción
          </span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${badgeClass}`}>
            {severidad}
          </span>
        </div>
        <h2 id="dashboard-recomendacion-titulo" className="text-xl sm:text-2xl font-bold text-slate-900 leading-snug">
          {recomendacion.titulo}
        </h2>
        {explicacion.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm text-slate-600 list-disc list-inside">
            {explicacion.map((linea, i) => (
              <li key={i}>{linea}</li>
            ))}
          </ul>
        )}
        {recomendacion.to && recomendacion.accion_label && (
          <Link
            to={recomendacion.to}
            className="mt-4 inline-flex items-center justify-center min-h-[44px] px-5 py-2.5 rounded-lg bg-primary-600 text-white font-semibold text-sm hover:bg-primary-700 active:bg-primary-800 transition-colors touch-manipulation"
          >
            {recomendacion.accion_label}
          </Link>
        )}
      </div>
    </section>
  )
}
