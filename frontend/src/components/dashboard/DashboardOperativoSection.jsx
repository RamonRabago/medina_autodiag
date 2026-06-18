import AlertasOperativasBanner from './AlertasOperativasBanner'
import OperacionesDashboardView from './OperacionesDashboardView'
import TurnoCajaBanner from '../operaciones/TurnoCajaBanner'

/**
 * Sección operativa ADMIN: alertas A0, turno caja, grupos disclosure (UX-1A).
 */
export default function DashboardOperativoSection({ data, isLoading, isError }) {
  if (isLoading) {
    return (
      <section className="mb-4 sm:mb-6 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        Cargando resumen operativo...
      </section>
    )
  }

  if (isError) {
    return (
      <section className="mb-4 sm:mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        El resumen operativo no está disponible en este momento.
      </section>
    )
  }

  const metricas = data?.metricas ?? {}

  return (
    <section className="mb-4 sm:mb-6">
      <h2 className="text-lg font-semibold text-slate-800 mb-3 sm:mb-4">Operaciones</h2>

      <div className="mb-4">
        <AlertasOperativasBanner alertas={data?.alertas_operativas ?? []} />
      </div>

      {data?.caja && (
        <div className="mb-4">
          <TurnoCajaBanner caja={data.caja} />
        </div>
      )}

      <OperacionesDashboardView metricas={metricas} />
    </section>
  )
}
