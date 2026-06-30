import { Link } from 'react-router-dom'

/**
 * Atajos estáticos servidos por backend — orden del array, sin reordenar.
 */
export default function DashboardV2AccionesFrecuentes({ acciones }) {
  const lista = Array.isArray(acciones) ? acciones : []
  if (lista.length === 0) {
    return null
  }

  return (
    <section className="mb-4 sm:mb-5" aria-labelledby="dashboard-acciones-titulo">
      <h2 id="dashboard-acciones-titulo" className="text-xs font-medium text-slate-400 mb-1.5">
        Atajos
      </h2>
      <div className="flex flex-wrap gap-1.5">
        {lista.map((accion) => (
          <Link
            key={accion.id ?? accion.to}
            to={accion.to ?? '/'}
            className="inline-flex items-center min-h-[36px] px-3 py-1.5 rounded-md border border-dashed border-slate-200 bg-transparent text-xs font-medium text-slate-600 hover:border-slate-300 hover:text-slate-800 hover:bg-slate-50 transition-colors touch-manipulation"
          >
            {accion.label}
          </Link>
        ))}
      </div>
    </section>
  )
}
