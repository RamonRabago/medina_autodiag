import { Link } from 'react-router-dom'
import { formatoMoneda } from './dashboardV2Styles'

/**
 * KPIs compactos de contexto — secundarios visualmente.
 */
export default function DashboardV2Resumen({ resumen }) {
  if (!resumen) {
    return null
  }

  const turnoAbierto = resumen.caja?.turno_abierto

  const items = [
    {
      label: 'Cobrado hoy',
      value: formatoMoneda(resumen.cobrado_hoy),
      valueClass: 'text-emerald-700',
    },
    {
      label: 'Ventas hoy',
      value: formatoMoneda(resumen.ventas_hoy),
    },
    {
      label: 'OT activas',
      value: resumen.ot_activas ?? 0,
    },
    {
      label: 'Citas próx. 24 h',
      value: resumen.citas_proximas_24h ?? 0,
      to: '/citas',
    },
    {
      label: 'Por cobrar',
      value: formatoMoneda(resumen.por_cobrar),
      valueClass: (Number(resumen.por_cobrar) || 0) > 0 ? 'text-amber-700' : 'text-slate-800',
      to: '/operaciones/caja',
    },
    {
      label: 'Turno caja',
      value: turnoAbierto ? 'Abierto' : 'Cerrado',
      valueClass: turnoAbierto ? 'text-emerald-700' : 'text-slate-600',
      to: '/operaciones/caja',
    },
  ]

  return (
    <section className="mb-4 sm:mb-6" aria-labelledby="dashboard-resumen-titulo">
      <h2 id="dashboard-resumen-titulo" className="text-sm font-medium text-slate-500 mb-2">
        Contexto de hoy
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3">
        {items.map((item) => {
          const inner = (
            <>
              <p className="text-xs text-slate-500 font-medium">{item.label}</p>
              <p className={`text-base sm:text-lg font-semibold mt-0.5 ${item.valueClass ?? 'text-slate-800'}`}>
                {item.value}
              </p>
            </>
          )
          const className =
            'rounded-lg border border-slate-100 bg-white px-3 py-2.5 shadow-sm min-h-[64px] flex flex-col justify-center'

          if (item.to) {
            return (
              <Link
                key={item.label}
                to={item.to}
                className={`${className} hover:border-primary-200 hover:shadow transition-colors touch-manipulation`}
              >
                {inner}
              </Link>
            )
          }
          return (
            <div key={item.label} className={className}>
              {inner}
            </div>
          )
        })}
      </div>
    </section>
  )
}
