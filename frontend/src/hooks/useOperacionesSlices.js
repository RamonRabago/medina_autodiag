import api from '../services/api'
import { useApiQuery } from './useApi'
import { RESUMEN_QUERY_KEY } from './useOperacionesResumen'
import { BANDEJA_IDS, MI_TALLER_BANDEJA_API_KEYS } from '../utils/operacionesGrupos'

export const MI_TALLER_LIMIT_ITEMS = 30

export const MI_TALLER_CAPA0_STALE_TIME = 15000
export const MI_TALLER_SLICE_STALE_TIME = 30000

const SLICES_ENV = import.meta.env.VITE_A0_SLICES_MI_TALLER

/** Default false — safe before UX-1B.0 deploy in prod. */
export function isMiTallerSlicesEnabled() {
  return SLICES_ENV === 'true'
}

export function buildOperacionesScopeKey(user) {
  if (user?.id_usuario == null) return null
  return `${user.id_usuario}:${user.rol ?? ''}`
}

export function capa0QueryKey(limitItems, scopeKey) {
  return ['operaciones', 'resumen', 'capa0', { limit: limitItems, scopeKey }]
}

export function bandejaQueryKey(bandejaKey, limitItems, scopeKey) {
  return ['operaciones', 'resumen', 'bandeja', bandejaKey, { limit: limitItems, scopeKey }]
}

export function miTallerHeavyQueryKey(limitItems, scopeKey) {
  return ['operaciones', 'resumen', 'heavy', { limit: limitItems, scopeKey }]
}

/** Legacy key pre-UX-1B.1 (flag OFF). */
export const MI_TALLER_LEGACY_RESUMEN_KEY = [...RESUMEN_QUERY_KEY, MI_TALLER_LIMIT_ITEMS, true]

export const MI_TALLER_USER_SCOPE_KEY = ['mi-taller', 'accordion-user-scope']

const MI_TALLER_BANDEJA_KEYS = Object.values(MI_TALLER_BANDEJA_API_KEYS)

function fetchCapa0(limitItems) {
  return api
    .get('/operaciones/resumen', {
      params: { limit_items: limitItems, incluir_items: false },
    })
    .then((r) => r.data)
}

function fetchBandeja(bandejaKey, limitItems) {
  return api
    .get('/operaciones/resumen', {
      params: { limit_items: limitItems, bandejas: bandejaKey },
    })
    .then((r) => r.data)
}

function fetchHeavy(limitItems) {
  return api
    .get('/operaciones/resumen', {
      params: { limit_items: limitItems, incluir_items: true },
    })
    .then((r) => r.data)
}

export function useOperacionesCapa0(limitItems = MI_TALLER_LIMIT_ITEMS, { scopeKey, enabled = true } = {}) {
  return useApiQuery(capa0QueryKey(limitItems, scopeKey), () => fetchCapa0(limitItems), {
    staleTime: MI_TALLER_CAPA0_STALE_TIME,
    enabled: enabled && !!scopeKey,
  })
}

export function useOperacionesBandeja(
  bandejaKey,
  limitItems = MI_TALLER_LIMIT_ITEMS,
  { scopeKey, enabled = true } = {}
) {
  return useApiQuery(
    bandejaQueryKey(bandejaKey, limitItems, scopeKey),
    () => fetchBandeja(bandejaKey, limitItems),
    {
      staleTime: MI_TALLER_SLICE_STALE_TIME,
      enabled: enabled && !!scopeKey && !!bandejaKey,
    }
  )
}

export function useOperacionesHeavy(limitItems = MI_TALLER_LIMIT_ITEMS, { scopeKey, enabled = true } = {}) {
  return useApiQuery(miTallerHeavyQueryKey(limitItems, scopeKey), () => fetchHeavy(limitItems), {
    staleTime: MI_TALLER_CAPA0_STALE_TIME,
    enabled: enabled && !!scopeKey,
  })
}

export function bandejaApiKeyForSection(sectionId) {
  return MI_TALLER_BANDEJA_API_KEYS[sectionId] ?? null
}

export function bandejaApiKeysForExpandedSections(expandedSections) {
  return [...expandedSections]
    .map((sectionId) => bandejaApiKeyForSection(sectionId))
    .filter(Boolean)
}

export function removeOperacionesScopeQueries(queryClient, scopeKey) {
  if (!scopeKey) return
  queryClient.removeQueries({ queryKey: capa0QueryKey(MI_TALLER_LIMIT_ITEMS, scopeKey) })
  queryClient.removeQueries({ queryKey: miTallerHeavyQueryKey(MI_TALLER_LIMIT_ITEMS, scopeKey) })
  for (const bandejaKey of MI_TALLER_BANDEJA_KEYS) {
    queryClient.removeQueries({
      queryKey: bandejaQueryKey(bandejaKey, MI_TALLER_LIMIT_ITEMS, scopeKey),
    })
  }
}

export async function invalidateAndRefetchMiTallerSlices(
  queryClient,
  scopeKey,
  expandedSections
) {
  if (!scopeKey) return

  const limit = MI_TALLER_LIMIT_ITEMS
  await queryClient.invalidateQueries({ queryKey: capa0QueryKey(limit, scopeKey) })
  await queryClient.refetchQueries({ queryKey: capa0QueryKey(limit, scopeKey), type: 'active' })

  const openBandejas = bandejaApiKeysForExpandedSections(expandedSections)
  for (const bandejaKey of openBandejas) {
    const key = bandejaQueryKey(bandejaKey, limit, scopeKey)
    await queryClient.invalidateQueries({ queryKey: key })
    await queryClient.refetchQueries({ queryKey: key, type: 'active' })
  }
}

export { BANDEJA_IDS }
