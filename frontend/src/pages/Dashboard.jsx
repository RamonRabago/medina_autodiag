import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import PageLoading from '../components/PageLoading'
import DashboardV2Recomendacion from '../components/dashboard/DashboardV2Recomendacion'
import DashboardV2SaludOperativa from '../components/dashboard/DashboardV2SaludOperativa'
import DashboardV2Prioridades from '../components/dashboard/DashboardV2Prioridades'
import DashboardV2Resumen from '../components/dashboard/DashboardV2Resumen'
import DashboardV2AccionesFrecuentes from '../components/dashboard/DashboardV2AccionesFrecuentes'
import DashboardV2LazySections from '../components/dashboard/DashboardV2LazySections'
import { useApiQuery } from '../hooks/useApi'
import api from '../services/api'
import { getLandingPorRol, puedeRecepcionRapida } from '../utils/rolesOperaciones'

/**
 * Dashboard ADMIN — Centro de Decisión V2 (render puro del backend).
 * P5.1: solo ADMIN aterriza aquí; otros roles redirigen vía getLandingPorRol.
 */
export default function Dashboard() {
  const { user } = useAuth()
  const rol = user?.rol?.value ?? user?.rol ?? ''
  const landing = getLandingPorRol(rol)
  const esAdmin = rol === 'ADMIN'

  const { data, isLoading, isError } = useApiQuery(
    ['dashboard', 'v2', rol],
    () => api.get('/dashboard').then((r) => r.data),
    { staleTime: 45 * 1000 }
  )

  if (landing !== '/') {
    return <Navigate to={landing} replace />
  }

  if (isLoading) {
    return <PageLoading mensaje="Cargando dashboard..." />
  }

  const operativa = data?.operativa

  return (
    <div className="min-h-0">
      <PageHeader title="Dashboard" className="mb-4 sm:mb-6" />

      {esAdmin ? (
        <>
          {isError && (
            <p className="mb-4 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              No se pudo cargar el centro de decisión. Intenta recargar la página.
            </p>
          )}

          {!isError && !operativa && (
            <section className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
              El resumen operativo no está disponible en este momento. Puedes revisar las secciones
              detalladas más abajo.
            </section>
          )}

          {operativa && (
            <>
              <DashboardV2Recomendacion recomendacion={operativa.recomendacion_inteligente} />
              <DashboardV2SaludOperativa salud={operativa.salud_operativa} />
              <DashboardV2Prioridades prioridades={operativa.prioridades_agrupadas} />
              <DashboardV2Resumen resumen={operativa.resumen} />
              <DashboardV2AccionesFrecuentes acciones={operativa.acciones_frecuentes} />
            </>
          )}

          <DashboardV2LazySections esAdmin={esAdmin} />
        </>
      ) : (
        <DashboardFallbackNoAdmin data={data} rol={rol} />
      )}
    </div>
  )
}

/** Rol con landing `/` no reconocido — vista mínima sin lógica de negocio. */
function DashboardFallbackNoAdmin({ data, rol }) {
  return (
    <div className="space-y-4">
      {puedeRecepcionRapida(rol) && (
        <Link
          to="/operaciones/recepcion"
          className="flex items-center gap-4 p-4 bg-primary-600 text-white rounded-xl shadow-md hover:bg-primary-700 transition-colors touch-manipulation"
        >
          <span className="text-3xl" aria-hidden>
            📥
          </span>
          <div>
            <p className="font-semibold text-lg">Recepción rápida</p>
            <p className="text-sm text-primary-100">Registrar ingreso de vehículo</p>
          </div>
        </Link>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-slate-500 text-sm font-medium">Clientes</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{data?.clientes ?? '—'}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-slate-500 text-sm font-medium">Órdenes de trabajo</h3>
          <p className="text-2xl font-bold text-slate-800 mt-1">{data?.ordenes ?? '—'}</p>
        </div>
      </div>
    </div>
  )
}
