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
  const porCobrar = Number(resumen.por_cobrar) || 0
  const porCobrarDestacado = porCobrar > 0

  const items = [
    {
      label: 'Cobrado hoy',
      value: formatoMoneda(resumen.cobrado_hoy),
      valueClass: 'text-slate-700',
    },
    {
      label: 'Ventas hoy',
      value: formatoMoneda(resumen.ventas_hoy),
      valueClass: 'text-slate-700',
    },
    {
      label: 'OT activas',
      value: resumen.ot_activas ?? 0,
      valueClass: 'text-slate-700',
    },
    {
      label: 'Citas 24 h',
      value: resumen.citas_proximas_24h ?? 0,
      valueClass: 'text-slate-700',
      to: '/citas',
    },
    {
      label: 'Por cobrar',
      value: formatoMoneda(resumen.por_cobrar),
      valueClass: porCobrarDestacado ? 'text-amber-800' : 'text-slate-700',
      to: '/operaciones/caja',
      destacado: porCobrarDestacado,
    },
    {
      label: 'Turno caja',
      value: turnoAbierto ? 'Abierto' : 'Cerrado',
      valueClass: turnoAbierto ? 'text-emerald-700' : 'text-slate-500',
      to: '/operaciones/caja',
    },
  ]

  return (
    <section
      className="mb-4 sm:mb-5 pt-3 border-t border-slate-100"
      aria-labelledby="dashboard-resumen-titulo"
    >
      <h2 id="dashboard-resumen-titulo" className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
        Contexto de hoy
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5 sm:gap-2">
        {items.map((item) => {
          const inner = (
            <>
              <p className="text-[11px] text-slate-400 font-medium">{item.label}</p>
              <p
                className={`text-sm font-semibold mt-0.5 tabular-nums ${item.valueClass ?? 'text-slate-700'} ${
                  item.destacado ? 'text-base' : ''
                }`}
              >
                {item.value}
              </p>
            </>
          )
          const baseClass =
            'rounded-md border px-2.5 py-2 min-h-[52px] flex flex-col justify-center bg-slate-50/50'
          const className = item.destacado
            ? `${baseClass} border-amber-200 bg-amber-50/40 sm:col-span-1 ring-1 ring-amber-100`
            : `${baseClass} border-slate-100/80`

          if (item.to) {
            return (
              <Link
                key={item.label}
                to={item.to}
                className={`${className} hover:border-slate-200 transition-colors touch-manipulation`}
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
