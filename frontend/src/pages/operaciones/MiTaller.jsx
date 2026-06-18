import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import PageHeader from '../../components/PageHeader'
import PageLoading from '../../components/PageLoading'
import BandejaOtAccordionSection from '../../components/operaciones/BandejaOtAccordionSection'
import { useAuth } from '../../context/AuthContext'
import {
  BANDEJA_IDS,
  buildOperacionesScopeKey,
  invalidateAndRefetchMiTallerSlices,
  isMiTallerSlicesEnabled,
  MI_TALLER_LEGACY_RESUMEN_KEY,
  MI_TALLER_USER_SCOPE_KEY,
  removeOperacionesScopeQueries,
  useOperacionesBandeja,
  useOperacionesCapa0,
} from '../../hooks/useOperacionesSlices'
import { RESUMEN_QUERY_KEY, useOperacionesResumen } from '../../hooks/useOperacionesResumen'
import { puedeMiTaller } from '../../utils/rolesOperaciones'
import {
  computeDefaultExpandedMiTallerSections,
  metricasToBandejasTotals,
  MI_TALLER_BANDEJA_API_KEYS,
} from '../../utils/operacionesGrupos'
import { showError } from '../../utils/toast'

const SLICES_ENABLED = isMiTallerSlicesEnabled()

function sliceItems(sliceData, apiKey) {
  return sliceData?.bandejas?.[apiKey]?.items ?? []
}

function sliceLoading(isExpanded, sliceQuery) {
  return isExpanded && sliceQuery.isFetching && !sliceQuery.data
}

export default function MiTaller() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, loading: authLoading } = useAuth()
  const scopeKey = buildOperacionesScopeKey(user)

  const legacyQuery = useOperacionesResumen(30, {
    enabled: !SLICES_ENABLED,
  })
  const capa0Query = useOperacionesCapa0(30, {
    scopeKey,
    enabled: SLICES_ENABLED && !authLoading,
  })

  const defaultsApplied = useRef(false)
  const userInteracted = useRef(false)
  const [expandedSections, setExpandedSections] = useState(() => new Set())

  const pendientesExpanded = expandedSections.has(BANDEJA_IDS.PENDIENTES)
  const enProcesoExpanded = expandedSections.has(BANDEJA_IDS.EN_PROCESO)
  const completadasExpanded = expandedSections.has(BANDEJA_IDS.COMPLETADAS)

  const pendientesSlice = useOperacionesBandeja(MI_TALLER_BANDEJA_API_KEYS[BANDEJA_IDS.PENDIENTES], 30, {
    scopeKey,
    enabled: SLICES_ENABLED && pendientesExpanded,
  })
  const enProcesoSlice = useOperacionesBandeja(MI_TALLER_BANDEJA_API_KEYS[BANDEJA_IDS.EN_PROCESO], 30, {
    scopeKey,
    enabled: SLICES_ENABLED && enProcesoExpanded,
  })
  const completadasSlice = useOperacionesBandeja(MI_TALLER_BANDEJA_API_KEYS[BANDEJA_IDS.COMPLETADAS], 30, {
    scopeKey,
    enabled: SLICES_ENABLED && completadasExpanded,
  })

  const activeQuery = SLICES_ENABLED ? capa0Query : legacyQuery
  const { isLoading, isError, error, isFetching } = activeQuery

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
    if (authLoading || !scopeKey) return

    const previousScope = queryClient.getQueryData(MI_TALLER_USER_SCOPE_KEY)
    if (previousScope === scopeKey) return

    queryClient.setQueryData(MI_TALLER_USER_SCOPE_KEY, scopeKey)
    defaultsApplied.current = false
    userInteracted.current = false
    setExpandedSections(new Set())

    if (previousScope) {
      removeOperacionesScopeQueries(queryClient, previousScope)
    }
    queryClient.removeQueries({ queryKey: MI_TALLER_LEGACY_RESUMEN_KEY })
  }, [authLoading, scopeKey, queryClient])

  useEffect(() => {
    if (defaultsApplied.current || userInteracted.current) return

    if (SLICES_ENABLED) {
      if (!capa0Query.data?.metricas || capa0Query.isFetching) return
      defaultsApplied.current = true
      setExpandedSections(
        computeDefaultExpandedMiTallerSections(
          user?.rol,
          metricasToBandejasTotals(capa0Query.data.metricas)
        )
      )
      return
    }

    if (!legacyQuery.data?.bandejas || legacyQuery.isFetching) return
    defaultsApplied.current = true
    setExpandedSections(
      computeDefaultExpandedMiTallerSections(user?.rol, legacyQuery.data.bandejas)
    )
  }, [
    capa0Query.data?.metricas,
    capa0Query.isFetching,
    legacyQuery.data?.bandejas,
    legacyQuery.isFetching,
    user?.rol,
  ])

  const invalidar = useCallback(async () => {
    if (SLICES_ENABLED) {
      await invalidateAndRefetchMiTallerSlices(queryClient, scopeKey, expandedSections)
      return
    }
    queryClient.invalidateQueries({ queryKey: RESUMEN_QUERY_KEY })
    legacyQuery.refetch()
  }, [queryClient, scopeKey, expandedSections, legacyQuery])

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

  if (isLoading && !activeQuery.data) {
    return <PageLoading mensaje="Cargando Mi Taller..." />
  }

  const metricas = SLICES_ENABLED
    ? capa0Query.data?.metricas ?? {}
    : {
        ot_pendientes: legacyQuery.data?.bandejas?.ot_pendientes?.total ?? 0,
        ot_en_proceso: legacyQuery.data?.bandejas?.ot_en_proceso?.total ?? 0,
        ot_completadas: legacyQuery.data?.bandejas?.ot_completadas?.total ?? 0,
      }

  const bandejasLegacy = legacyQuery.data?.bandejas || {}
  const showTecnico = user?.rol === 'ADMIN'

  const pendientesItems = SLICES_ENABLED
    ? sliceItems(pendientesSlice.data, MI_TALLER_BANDEJA_API_KEYS[BANDEJA_IDS.PENDIENTES])
    : bandejasLegacy.ot_pendientes?.items ?? []
  const enProcesoItems = SLICES_ENABLED
    ? sliceItems(enProcesoSlice.data, MI_TALLER_BANDEJA_API_KEYS[BANDEJA_IDS.EN_PROCESO])
    : bandejasLegacy.ot_en_proceso?.items ?? []
  const completadasItems = SLICES_ENABLED
    ? sliceItems(completadasSlice.data, MI_TALLER_BANDEJA_API_KEYS[BANDEJA_IDS.COMPLETADAS])
    : bandejasLegacy.ot_completadas?.items ?? []

  const refreshing =
    isFetching ||
    (SLICES_ENABLED &&
      ((pendientesExpanded && pendientesSlice.isFetching) ||
        (enProcesoExpanded && enProcesoSlice.isFetching) ||
        (completadasExpanded && completadasSlice.isFetching)))

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
          disabled={refreshing}
          className="min-h-[44px] px-4 py-2 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 touch-manipulation disabled:opacity-50"
        >
          {refreshing ? 'Actualizando...' : 'Actualizar'}
        </button>
      </PageHeader>

      <BandejaOtAccordionSection
        sectionId="mi-taller-pendientes"
        titulo="Pendientes"
        total={metricas.ot_pendientes ?? 0}
        items={pendientesItems}
        vacio={
          sliceLoading(pendientesExpanded, pendientesSlice)
            ? 'Cargando órdenes...'
            : 'No tienes órdenes pendientes asignadas'
        }
        showTecnico={showTecnico}
        onAccionExito={invalidar}
        expanded={pendientesExpanded}
        onToggle={() => toggleSection(BANDEJA_IDS.PENDIENTES)}
      />

      <BandejaOtAccordionSection
        sectionId="mi-taller-en-proceso"
        titulo="En proceso"
        total={metricas.ot_en_proceso ?? 0}
        items={enProcesoItems}
        vacio={
          sliceLoading(enProcesoExpanded, enProcesoSlice)
            ? 'Cargando órdenes...'
            : 'No hay trabajos en proceso'
        }
        showTecnico={showTecnico}
        onAccionExito={invalidar}
        expanded={enProcesoExpanded}
        onToggle={() => toggleSection(BANDEJA_IDS.EN_PROCESO)}
      />

      <BandejaOtAccordionSection
        sectionId="mi-taller-completadas"
        titulo="Completadas"
        total={metricas.ot_completadas ?? 0}
        items={completadasItems}
        vacio={
          sliceLoading(completadasExpanded, completadasSlice)
            ? 'Cargando órdenes...'
            : 'No hay órdenes completadas recientes'
        }
        showTecnico={showTecnico}
        soloLectura
        expanded={completadasExpanded}
        onToggle={() => toggleSection(BANDEJA_IDS.COMPLETADAS)}
      />
    </div>
  )
}
