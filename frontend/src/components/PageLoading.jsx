/**
 * Estado de carga para páginas completas.
 * Reemplaza el texto "Cargando..." con spinner + mensaje.
 */
import LoadingSpinner from './LoadingSpinner'

export default function PageLoading({ mensaje = 'Cargando...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 min-h-[200px]" role="status" aria-live="polite">
      <LoadingSpinner size="lg" className="mb-4" />
      <p className="text-slate-500 text-sm">{mensaje}</p>
    </div>
  )
}
