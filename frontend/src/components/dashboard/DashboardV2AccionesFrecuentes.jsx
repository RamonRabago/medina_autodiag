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
    <section className="mb-4 sm:mb-6" aria-labelledby="dashboard-acciones-titulo">
      <h2 id="dashboard-acciones-titulo" className="text-sm font-medium text-slate-500 mb-2">
        Acciones frecuentes
      </h2>
      <div className="flex flex-wrap gap-2">
        {lista.map((accion) => (
          <Link
            key={accion.id ?? accion.to}
            to={accion.to ?? '/'}
            className="inline-flex items-center min-h-[40px] px-4 py-2 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:border-primary-300 hover:text-primary-700 hover:bg-primary-50 transition-colors touch-manipulation shadow-sm"
          >
            {accion.label}
          </Link>
        ))}
      </div>
    </section>
  )
}
