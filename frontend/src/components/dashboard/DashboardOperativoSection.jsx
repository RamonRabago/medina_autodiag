import { Link } from 'react-router-dom'
import AlertasOperativasBanner from './AlertasOperativasBanner'
import KPIWidget from './KPIWidget'
import TurnoCajaBanner from '../operaciones/TurnoCajaBanner'

const CTAS_OPERACIONES = [
  { to: '/operaciones/recepcion', label: 'Recepción', hint: 'Ingreso de vehículos' },
  { to: '/operaciones/caja', label: 'Caja operativa', hint: 'Cobro y entrega' },
  { to: '/operaciones/mi-taller', label: 'Mi taller', hint: 'OT en proceso' },
  { to: '/citas', label: 'Citas', hint: 'Agenda y asistencia' },
]

/**
 * Sección operativa ADMIN: alertas A0, turno caja, CTAs y contadores (sin bandejas).
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

      <div className="mb-4 sm:mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
        {CTAS_OPERACIONES.map((cta) => (
          <Link
            key={cta.to}
            to={cta.to}
            className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm hover:border-primary-300 hover:shadow transition-colors touch-manipulation min-h-[56px]"
          >
            <div>
              <p className="font-medium text-slate-800">{cta.label}</p>
              <p className="text-xs text-slate-500">{cta.hint}</p>
            </div>
            <span className="ml-auto text-primary-600 text-xs hidden sm:inline">Ir →</span>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <KPIWidget
          label="Citas sin asistencia"
          value={metricas.citas_pendientes_asistencia}
          to="/citas"
          hint="Confirmadas sin registrar asistencia"
          valueClassName={
            (metricas.citas_pendientes_asistencia ?? 0) > 0 ? 'text-amber-600' : 'text-slate-800'
          }
        />
        <KPIWidget
          label="Citas convertibles"
          value={metricas.citas_convertibles}
          to="/operaciones/recepcion"
          hint="Listas para recepción"
        />
        <KPIWidget
          label="OT pendientes"
          value={metricas.ot_pendientes}
          to="/operaciones/mi-taller"
          hint="Por iniciar"
        />
        <KPIWidget
          label="OT en proceso"
          value={metricas.ot_en_proceso}
          to="/operaciones/mi-taller"
          hint="En taller"
        />
        <KPIWidget
          label="OT completadas"
          value={metricas.ot_completadas}
          to="/operaciones/mi-taller"
          hint="Finalizadas"
        />
        <KPIWidget
          label="Por cobrar (O1)"
          value={metricas.ot_pendientes_cobro}
          to="/operaciones/caja"
          hint="Completadas pendientes de cobro"
          valueClassName={
            (metricas.ot_pendientes_cobro ?? 0) > 0 ? 'text-amber-600' : 'text-slate-800'
          }
        />
        <KPIWidget
          label="Listas entrega (O2)"
          value={metricas.ot_listas_entrega}
          to="/operaciones/caja"
          hint="Listas para entregar"
        />
        <KPIWidget
          label="Ventas con saldo (V1)"
          value={metricas.ventas_saldo_pendiente}
          to="/operaciones/caja"
          hint="Saldo pendiente en mostrador"
          valueClassName={
            (metricas.ventas_saldo_pendiente ?? 0) > 0 ? 'text-amber-600' : 'text-slate-800'
          }
        />
        <KPIWidget
          label="Refacciones en compra"
          value={metricas.refacciones_en_compra}
          to="/cotizaciones-refaccion"
          hint="Cotizaciones en compra"
        />
        <KPIWidget
          label="Refacciones recibidas"
          value={metricas.refacciones_recibidas_pendiente_entrega}
          to="/cotizaciones-refaccion"
          hint="Pendientes de entrega"
        />
      </div>
    </section>
  )
}
