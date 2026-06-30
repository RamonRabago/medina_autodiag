import { Link } from 'react-router-dom'
import { SEVERIDAD_BADGE } from './dashboardV2Styles'

/**
 * Prioridades agrupadas — orden y severidad vienen del backend.
 */
export default function DashboardV2Prioridades({ prioridades }) {
  const grupos = Array.isArray(prioridades) ? prioridades : []
  if (grupos.length === 0) {
    return null
  }

  return (
    <section className="mb-4 sm:mb-6" aria-labelledby="dashboard-prioridades-titulo">
      <h2 id="dashboard-prioridades-titulo" className="text-base font-semibold text-slate-800 mb-3">
        Prioridades
      </h2>
      <div className="space-y-3">
        {grupos.map((grupo) => {
          const items = Array.isArray(grupo.items) ? grupo.items : []
          const sevGrupo = grupo.severidad_grupo ?? 'baja'
          const badgeClass = SEVERIDAD_BADGE[sevGrupo] ?? SEVERIDAD_BADGE.baja

          return (
            <div
              key={grupo.grupo ?? grupo.label}
              className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-slate-100 bg-slate-50/80">
                <div className="flex items-center gap-2 min-w-0">
                  <h3 className="text-sm font-semibold text-slate-800 truncate">{grupo.label}</h3>
                  <span className="text-xs text-slate-500">({grupo.total ?? items.length})</span>
                </div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full border shrink-0 ${badgeClass}`}>
                  {sevGrupo}
                </span>
              </div>
              <ul className="divide-y divide-slate-100">
                {items.map((item) => {
                  const sevItem = item.severidad ?? 'baja'
                  const itemBadge = SEVERIDAD_BADGE[sevItem] ?? SEVERIDAD_BADGE.baja
                  const contenido = (
                    <>
                      <p className="text-sm font-medium text-slate-800">{item.titulo}</p>
                      {item.subtitulo && (
                        <p className="text-xs text-slate-500 mt-0.5">{item.subtitulo}</p>
                      )}
                    </>
                  )
                  return (
                    <li key={item.id ?? item.titulo} className="px-4 py-3 hover:bg-slate-50/50">
                      {item.to ? (
                        <Link to={item.to} className="flex items-start justify-between gap-3 touch-manipulation">
                          <div className="min-w-0 flex-1">{contenido}</div>
                          <span className={`text-xs px-1.5 py-0.5 rounded border shrink-0 ${itemBadge}`}>
                            {sevItem}
                          </span>
                        </Link>
                      ) : (
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">{contenido}</div>
                          <span className={`text-xs px-1.5 py-0.5 rounded border shrink-0 ${itemBadge}`}>
                            {sevItem}
                          </span>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
              {grupo.ver_todas?.to && (
                <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/50">
                  <Link
                    to={grupo.ver_todas.to}
                    className="text-sm font-medium text-primary-600 hover:text-primary-700 touch-manipulation inline-block py-2"
                  >
                    {grupo.ver_todas.label ?? 'Ver todas'} →
                  </Link>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
