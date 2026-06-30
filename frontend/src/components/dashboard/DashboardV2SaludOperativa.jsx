import { SALUD_AREA_LABELS, SALUD_ESTADO, SEVERIDAD_BADGE } from './dashboardV2Styles'

/**
 * Salud operativa por áreas — render puro.
 */
export default function DashboardV2SaludOperativa({ salud }) {
  if (!salud) {
    return null
  }

  const globalEstado = salud.global ?? 'verde'
  const areas = salud.areas ?? {}

  return (
    <section className="mb-4 sm:mb-6" aria-labelledby="dashboard-salud-titulo">
      <h2 id="dashboard-salud-titulo" className="text-base font-semibold text-slate-800 mb-3">
        Salud operativa
      </h2>
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <span
            className={`w-3 h-3 rounded-full shrink-0 ${SALUD_ESTADO[globalEstado] ?? SALUD_ESTADO.verde}`}
            aria-hidden
          />
          <p className="text-sm font-medium text-slate-800">{salud.mensaje ?? 'Estado del taller'}</p>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
              globalEstado === 'rojo'
                ? SEVERIDAD_BADGE.critica
                : globalEstado === 'amarillo'
                  ? SEVERIDAD_BADGE.alta
                  : SEVERIDAD_BADGE.estable
            }`}
          >
            {globalEstado}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(SALUD_AREA_LABELS).map(([key, label]) => {
            const area = areas[key]
            if (!area) return null
            const estado = area.estado ?? 'verde'
            return (
              <div
                key={key}
                className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3 min-h-[72px]"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`w-2.5 h-2.5 rounded-full shrink-0 ${SALUD_ESTADO[estado] ?? SALUD_ESTADO.verde}`}
                    aria-hidden
                  />
                  <span className="text-sm font-semibold text-slate-800">{label}</span>
                </div>
                <p className="text-xs text-slate-600 leading-snug">{area.mensaje}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
