import { useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import PageHeader from '../../components/PageHeader'
import RecepcionRapidaForm from '../../components/operaciones/RecepcionRapidaForm'
import { ROLES_RECEPCION } from '../../utils/rolesOperaciones'

/**
 * Recepción rápida operativa — OT mínima en un solo paso.
 * Modo avanzado: /ordenes-trabajo/nueva
 *
 * P2: ?cita_id=42 precargará datos (hook reservado, sin implementar aún).
 */
export default function RecepcionRapida() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, loading: authLoading } = useAuth()

  const citaId = searchParams.get('cita_id')
  const initialValues = citaId ? { cita_id: Number(citaId) } : {}

  useEffect(() => {
    if (!authLoading && user?.rol && !ROLES_RECEPCION.includes(user.rol)) {
      navigate('/ordenes-trabajo', { replace: true })
    }
  }, [authLoading, user?.rol, navigate])

  const handleExito = (orden) => {
    const id = orden?.id ?? orden?.id_orden
    if (id) {
      navigate(`/ordenes-trabajo/${id}`, { replace: true })
    } else {
      navigate('/ordenes-trabajo', { replace: true })
    }
  }

  if (authLoading || (user?.rol && !ROLES_RECEPCION.includes(user.rol))) {
    return null
  }

  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader
        title="Recepción rápida"
        subtitle="Registra la entrada del vehículo en mostrador. El técnico agregará servicios después."
      >
        <Link
          to="/ordenes-trabajo/nueva"
          className="min-h-[44px] px-4 py-2 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 inline-flex items-center touch-manipulation"
        >
          Modo avanzado
        </Link>
      </PageHeader>

      <p className="text-sm text-slate-500 mb-6 mt-4">
        Solo necesitas cliente, vehículo y motivo. La orden quedará en estado{' '}
        <strong className="font-medium text-slate-700">PENDIENTE</strong>.
      </p>

      <RecepcionRapidaForm
        initialValues={initialValues}
        onExito={handleExito}
        userRol={user?.rol}
      />
    </div>
  )
}
