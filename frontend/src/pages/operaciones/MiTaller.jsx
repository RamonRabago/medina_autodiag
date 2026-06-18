import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import PageHeader from '../../components/PageHeader'
import PageLoading from '../../components/PageLoading'
import BandejaOtAccordionSection from '../../components/operaciones/BandejaOtAccordionSection'
import { useAuth } from '../../context/AuthContext'
import { RESUMEN_QUERY_KEY, useOperacionesResumen } from '../../hooks/useOperacionesResumen'
import { puedeMiTaller } from '../../utils/rolesOperaciones'
import {
  BANDEJA_IDS,
  computeDefaultExpandedMiTallerSections,
} from '../../utils/operacionesGrupos'
import { showError } from '../../utils/toast'

const MI_TALLER_RESUMEN_KEY = [...RESUMEN_QUERY_KEY, 30, true]
const MI_TALLER_USER_SCOPE_KEY = ['mi-taller', 'accordion-user-scope']

function buildUserScope(user) {
  if (user?.id_usuario == null) return null
  return `${user.id_usuario}:${user.rol ?? ''}`
}

export default function MiTaller() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, loading: authLoading } = useAuth()
  const { data, isLoading, isError, error, refetch, isFetching } = useOperacionesResumen(30)

  const defaultsApplied = useRef(false)
  const userInteracted = useRef(false)
  const [expandedSections, setExpandedSections] = useState(() => new Set())

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

  // UX-ISSUE-001: al cambiar usuario/rol, descartar resumen cacheado de otro rol.
  useEffect(() => {
    const scope = buildUserScope(user)
    if (authLoading || !scope) return

    const previousScope = queryClient.getQueryData(MI_TALLER_USER_SCOPE_KEY)
    if (previousScope === scope) return

    queryClient.setQueryData(MI_TALLER_USER_SCOPE_KEY, scope)
    defaultsApplied.current = false
    userInteracted.current = false
    setExpandedSections(new Set())
    queryClient.removeQueries({ queryKey: MI_TALLER_RESUMEN_KEY })
  }, [authLoading, user?.id_usuario, user?.rol, queryClient])

  useEffect(() => {
    if (!data?.bandejas || defaultsApplied.current || userInteracted.current) return
    if (isFetching) return

    defaultsApplied.current = true
    setExpandedSections(computeDefaultExpandedMiTallerSections(user?.rol, data.bandejas))
  }, [data?.bandejas, user?.rol, isFetching])

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: RESUMEN_QUERY_KEY })
    refetch()
  }

  const toggleSection = (sectionId) => {
    userInteracted.current = true
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(sectionId)) next.delete(sectionId)
      else next.add(sectionId)
      return next
    })
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

      <BandejaOtAccordionSection
        sectionId="mi-taller-pendientes"
        titulo="Pendientes"
        total={bandejas.ot_pendientes?.total ?? 0}
        items={bandejas.ot_pendientes?.items ?? []}
        vacio="No tienes órdenes pendientes asignadas"
        showTecnico={showTecnico}
        onAccionExito={invalidar}
        expanded={expandedSections.has(BANDEJA_IDS.PENDIENTES)}
        onToggle={() => toggleSection(BANDEJA_IDS.PENDIENTES)}
      />

      <BandejaOtAccordionSection
        sectionId="mi-taller-en-proceso"
        titulo="En proceso"
        total={bandejas.ot_en_proceso?.total ?? 0}
        items={bandejas.ot_en_proceso?.items ?? []}
        vacio="No hay trabajos en proceso"
        showTecnico={showTecnico}
        onAccionExito={invalidar}
        expanded={expandedSections.has(BANDEJA_IDS.EN_PROCESO)}
        onToggle={() => toggleSection(BANDEJA_IDS.EN_PROCESO)}
      />

      <BandejaOtAccordionSection
        sectionId="mi-taller-completadas"
        titulo="Completadas"
        total={bandejas.ot_completadas?.total ?? 0}
        items={bandejas.ot_completadas?.items ?? []}
        vacio="No hay órdenes completadas recientes"
        showTecnico={showTecnico}
        soloLectura
        expanded={expandedSections.has(BANDEJA_IDS.COMPLETADAS)}
        onToggle={() => toggleSection(BANDEJA_IDS.COMPLETADAS)}
      />
    </div>
  )
}
