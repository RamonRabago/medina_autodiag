import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import PageHeader from '../../components/PageHeader'
import PageLoading from '../../components/PageLoading'
import BandejaOtSection from '../../components/operaciones/BandejaOtSection'
import { useAuth } from '../../context/AuthContext'
import { RESUMEN_QUERY_KEY, useOperacionesResumen } from '../../hooks/useOperacionesResumen'
import { puedeMiTaller } from '../../utils/rolesOperaciones'
import { showError } from '../../utils/toast'

export default function MiTaller() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, loading: authLoading } = useAuth()
  const { data, isLoading, isError, error, refetch, isFetching } = useOperacionesResumen(30)

  useEffect(() => {
    if (!authLoading && user?.rol && !puedeMiTaller(user.rol)) {
      navigate('/', { replace: true })
    }
  }, [authLoading, user?.rol, navigate])

  useEffect(() => {
    if (isError && error) {
      showError(error, 'No se pudo cargar Mi Taller')
    }
  }, [isError, error])

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: RESUMEN_QUERY_KEY })
    refetch()
  }

  if (authLoading || (user?.rol && !puedeMiTaller(user.rol))) {
    return null
  }

  if (isLoading && !data) {
    return <PageLoading mensaje="Cargando Mi Taller..." />
  }

  const bandejas = data?.bandejas || {}
  const showTecnico = user?.rol === 'ADMIN'

  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader
        title="Mi Taller"
        subtitle={
          user?.rol === 'ADMIN'
            ? 'Supervisión operativa de órdenes de trabajo'
            : 'Tus trabajos pendientes, en proceso y completados recientes'
        }
      >
        <button
          type="button"
          onClick={() => invalidar()}
          disabled={isFetching}
          className="min-h-[44px] px-4 py-2 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 touch-manipulation disabled:opacity-50"
        >
          {isFetching ? 'Actualizando...' : 'Actualizar'}
        </button>
      </PageHeader>

      <BandejaOtSection
        titulo="Pendientes"
        total={bandejas.ot_pendientes?.total ?? 0}
        items={bandejas.ot_pendientes?.items ?? []}
        vacio="No tienes órdenes pendientes asignadas"
        showTecnico={showTecnico}
        onAccionExito={invalidar}
      />

      <BandejaOtSection
        titulo="En proceso"
        total={bandejas.ot_en_proceso?.total ?? 0}
        items={bandejas.ot_en_proceso?.items ?? []}
        vacio="No hay trabajos en proceso"
        showTecnico={showTecnico}
        onAccionExito={invalidar}
      />

      <BandejaOtSection
        titulo="Completadas"
        total={bandejas.ot_completadas?.total ?? 0}
        items={bandejas.ot_completadas?.items ?? []}
        vacio="No hay órdenes completadas recientes"
        showTecnico={showTecnico}
        soloLectura
      />
    </div>
  )
}
