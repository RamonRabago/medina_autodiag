import { Link } from 'react-router-dom'
import {
  encabezadoGrupoPrioridad,
  SEVERIDAD_BADGE,
  SEVERIDAD_GRUPO_STRIPE,
  SEVERIDAD_ETIQUETA,
  mostrarBadgeSeveridad,
} from './dashboardV2Styles'

/**
 * Prioridades agrupadas — orden y severidad vienen del backend.
 */
export default function DashboardV2Prioridades({ prioridades }) {
  const grupos = Array.isArray(prioridades) ? prioridades : []
  if (grupos.length === 0) {
    return null
  }

  return (
    <section className="mb-4 sm:mb-5" aria-labelledby="dashboard-prioridades-titulo">
      <h2 id="dashboard-prioridades-titulo" className="text-sm font-medium text-slate-500 mb-2">
        Otras prioridades por área
      </h2>
      <div className="space-y-3">
        {grupos.map((grupo) => {
          const items = Array.isArray(grupo.items) ? grupo.items : []
          const sevGrupo = grupo.severidad_grupo ?? 'baja'
          const stripeClass = SEVERIDAD_GRUPO_STRIPE[sevGrupo] ?? SEVERIDAD_GRUPO_STRIPE.baja
          const total = grupo.total ?? items.length
          const titulo = encabezadoGrupoPrioridad(grupo.grupo, total)

          return (
            <div
              key={grupo.grupo ?? grupo.label}
              className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden border-l-4 ${stripeClass}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-slate-100 bg-slate-50/90">
                <h3 className="text-sm font-bold text-slate-900 min-w-0">{titulo}</h3>
                {mostrarBadgeSeveridad(sevGrupo) && (
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border shrink-0 ${SEVERIDAD_BADGE[sevGrupo]}`}
                  >
                    {SEVERIDAD_ETIQUETA[sevGrupo] ?? sevGrupo}
                  </span>
                )}
              </div>
              <ul className="divide-y divide-slate-100">
                {items.map((item) => {
                  const sevItem = item.severidad ?? 'baja'
                  const showItemBadge = mostrarBadgeSeveridad(sevItem)
                  const contenido = (
                    <>
                      <p className="text-[13px] font-medium text-slate-800 leading-snug">{item.titulo}</p>
                      {item.subtitulo && (
                        <p className="text-[11px] text-slate-500 mt-0.5">{item.subtitulo}</p>
                      )}
                    </>
                  )
                  const rowClass = 'px-3 py-2 hover:bg-slate-50/80 active:bg-slate-100/80'

                  return (
                    <li key={item.id ?? item.titulo}>
                      {item.to ? (
                        <Link
                          to={item.to}
                          className={`flex items-start justify-between gap-2 touch-manipulation ${rowClass}`}
                        >
                          <div className="min-w-0 flex-1">{contenido}</div>
                          {showItemBadge && (
                            <span
                              className={`text-[10px] px-1 py-0.5 rounded border shrink-0 ${SEVERIDAD_BADGE[sevItem]}`}
                            >
                              {SEVERIDAD_ETIQUETA[sevItem]}
                            </span>
                          )}
                        </Link>
                      ) : (
                        <div className={`flex items-start justify-between gap-2 ${rowClass}`}>
                          <div className="min-w-0 flex-1">{contenido}</div>
                          {showItemBadge && (
                            <span
                              className={`text-[10px] px-1 py-0.5 rounded border shrink-0 ${SEVERIDAD_BADGE[sevItem]}`}
                            >
                              {SEVERIDAD_ETIQUETA[sevItem]}
                            </span>
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
              {grupo.ver_todas?.to && (
                <div className="px-3 py-1 border-t border-slate-100 bg-slate-50/60">
                  <Link
                    to={grupo.ver_todas.to}
                    className="text-xs font-semibold text-primary-600 hover:text-primary-700 touch-manipulation inline-block py-1"
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
