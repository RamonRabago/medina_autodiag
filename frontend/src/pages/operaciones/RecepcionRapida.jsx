import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../../services/api'
import { useAuth } from '../../context/AuthContext'
import PageHeader from '../../components/PageHeader'
import PageLoading from '../../components/PageLoading'
import RecepcionRapidaForm from '../../components/operaciones/RecepcionRapidaForm'
import { ROLES_RECEPCION } from '../../utils/rolesOperaciones'
import { construirMotivoDesdeCita } from '../../utils/citaOt'
import { showError } from '../../utils/toast'

/**
 * Recepción rápida operativa — OT mínima en un solo paso.
 * Con ?cita_id= precarga datos de la cita (P2).
 */
export default function RecepcionRapida() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { user, loading: authLoading } = useAuth()
  const citaId = searchParams.get('cita_id')

  const [initialValues, setInitialValues] = useState({})
  const [cargandoCita, setCargandoCita] = useState(false)
  const [bannerCita, setBannerCita] = useState(null)

  useEffect(() => {
    if (!authLoading && user?.rol && !ROLES_RECEPCION.includes(user.rol)) {
      navigate('/ordenes-trabajo', { replace: true })
    }
  }, [authLoading, user?.rol, navigate])

  useEffect(() => {
    if (!citaId) {
      setInitialValues({})
      setBannerCita(null)
      return
    }
    let cancelado = false
    setCargandoCita(true)
    api
      .get(`/citas/${citaId}`)
      .then((r) => {
        if (cancelado) return
        const c = r.data
        if (c.id_orden) {
          navigate(`/ordenes-trabajo/${c.id_orden}`, { replace: true })
          return
        }
        if (c.estado === 'CANCELADA') {
          showError('Esta cita está cancelada y no puede convertirse a OT.')
          setBannerCita(null)
          setInitialValues({})
          return
        }
        setBannerCita({
          id: c.id_cita,
          fecha: c.fecha_hora,
          cliente: c.cliente_nombre,
        })
        setInitialValues({
          cita_id: c.id_cita,
          cliente_id: String(c.id_cliente),
          vehiculo_id: c.id_vehiculo ? String(c.id_vehiculo) : '',
          motivo: construirMotivoDesdeCita(c),
          cliente: c.cliente_nombre
            ? { id_cliente: c.id_cliente, nombre: c.cliente_nombre }
            : null,
        })
      })
      .catch((err) => {
        if (!cancelado) showError(err, 'No se pudo cargar la cita')
      })
      .finally(() => {
        if (!cancelado) setCargandoCita(false)
      })
    return () => {
      cancelado = true
    }
  }, [citaId, navigate])

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

  if (cargandoCita) {
    return <PageLoading mensaje="Cargando datos de la cita..." />
  }

  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader
        title="Recepción rápida"
        subtitle={
          bannerCita
            ? `Completando recepción desde cita #${bannerCita.id}${bannerCita.cliente ? ` — ${bannerCita.cliente}` : ''}`
            : 'Registra la entrada del vehículo en mostrador. El técnico agregará servicios después.'
        }
      >
        <Link
          to="/ordenes-trabajo/nueva"
          className="min-h-[44px] px-4 py-2 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 inline-flex items-center touch-manipulation"
        >
          Modo avanzado
        </Link>
      </PageHeader>

      {bannerCita && (
        <div className="mb-4 p-3 rounded-lg bg-blue-50 border border-blue-100 text-sm text-blue-900">
          Datos precargados desde la cita. Completa el vehículo si falta y confirma la recepción.
        </div>
      )}

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
