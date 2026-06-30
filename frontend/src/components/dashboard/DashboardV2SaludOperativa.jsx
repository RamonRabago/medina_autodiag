import {
  mensajeSaludArea,
  mensajeSaludGlobal,
  SALUD_AREA_LABELS,
  SALUD_ESTADO,
  SEVERIDAD_BADGE,
  mostrarBadgeSeveridad,
} from './dashboardV2Styles'

const SALUD_GLOBAL_LABEL = {
  verde: 'Todo en orden',
  amarillo: 'Revisar pendientes',
  rojo: 'Acción inmediata',
}

const AREA_CARD = {
  verde: 'border-slate-100 bg-slate-50/80',
  amarillo: 'border-amber-200 bg-amber-50/60',
  rojo: 'border-red-200 bg-red-50/70',
}

/**
 * Salud operativa por áreas — render puro.
 */
export default function DashboardV2SaludOperativa({ salud }) {
  if (!salud) {
    return null
  }

  const globalEstado = salud.global ?? 'verde'
  const areas = salud.areas ?? {}
  const requiereAtencion = globalEstado !== 'verde'

  return (
    <section className="mb-4 sm:mb-5" aria-labelledby="dashboard-salud-titulo">
      <h2 id="dashboard-salud-titulo" className="text-sm font-medium text-slate-500 mb-2">
        Salud del taller
      </h2>
      <div
        className={`rounded-xl border bg-white shadow-sm p-3 sm:p-4 ${
          requiereAtencion ? 'border-amber-200' : 'border-slate-200'
        }`}
      >
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${SALUD_ESTADO[globalEstado] ?? SALUD_ESTADO.verde}`}
            aria-hidden
          />
          <p className={`text-sm font-semibold ${requiereAtencion ? 'text-slate-900' : 'text-slate-700'}`}>
            {mensajeSaludGlobal(salud)}
          </p>
          {mostrarBadgeSeveridad(globalEstado === 'rojo' ? 'critica' : globalEstado === 'amarillo' ? 'media' : 'estable') && (
            <span
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${
                globalEstado === 'rojo'
                  ? SEVERIDAD_BADGE.critica
                  : SEVERIDAD_BADGE.alta
              }`}
            >
              {SALUD_GLOBAL_LABEL[globalEstado]}
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {Object.entries(SALUD_AREA_LABELS).map(([key, label]) => {
            const area = areas[key]
            if (!area) return null
            const estado = area.estado ?? 'verde'
            const cardClass = AREA_CARD[estado] ?? AREA_CARD.verde
            const atencion = estado !== 'verde'

            return (
              <div
                key={key}
                className={`rounded-lg border px-2.5 py-1.5 min-h-[52px] ${cardClass} ${
                  atencion ? 'border-l-[3px] border-l-current' : ''
                } ${estado === 'rojo' ? 'border-l-red-500' : estado === 'amarillo' ? 'border-l-amber-400' : ''}`}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${SALUD_ESTADO[estado] ?? SALUD_ESTADO.verde}`}
                    aria-hidden
                  />
                  <span className={`text-xs font-semibold ${atencion ? 'text-slate-900' : 'text-slate-600'}`}>
                    {label}
                  </span>
                </div>
                <p
                  className={`text-[11px] leading-snug line-clamp-2 ${
                    atencion ? 'text-slate-700 font-medium' : 'text-slate-500'
                  }`}
                >
                  {mensajeSaludArea(area, globalEstado)}
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
