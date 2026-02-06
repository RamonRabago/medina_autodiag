/**
 * Hooks para TanStack Query con la API existente.
 * - Caché de respuestas (staleTime por defecto 60s)
 * - Reintentos automáticos (retry: 2)
 * - Refetch e invalidación tras mutaciones
 *
 * Los componentes pueden seguir usando api.get/post directamente;
 * usar useApiQuery/useApiMutation donde se quiera caché y mejor UX.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'

/** Opciones por defecto para queries (caché 60s, 2 reintentos) */
const DEFAULT_QUERY_OPTIONS = {
  staleTime: 60 * 1000,
  retry: 2,
  refetchOnWindowFocus: false,
}

/**
 * useApiQuery: GET con caché, reintentos y refetch.
 * @param {string[]} queryKey - Clave única (ej: ['servicios', pagina, buscar])
 * @param {function} queryFn - () => api.get(url, { params }).then(r => r.data)
 * @param {object} options - enabled, staleTime, etc.
 */
export function useApiQuery(queryKey, queryFn, options = {}) {
  return useQuery({
    queryKey,
    queryFn,
    ...DEFAULT_QUERY_OPTIONS,
    ...options,
  })
}

/**
 * useApiMutation: POST/PUT/DELETE con invalidación opcional tras éxito.
 * @param {function} mutationFn - (vars) => api.post(url, vars)
 * @param {object} options - onSuccess, onError, invalidateKeys (string[][] para invalidar tras éxito)
 *
 * Ejemplo:
 *   const mut = useApiMutation(
 *     (payload) => api.post('/servicios/', payload),
 *     { invalidateKeys: [['servicios']] }
 *   )
 *   mut.mutate(payload)
 */
export function useApiMutation(mutationFn, options = {}) {
  const queryClient = useQueryClient()
  const { invalidateKeys = [], onSuccess, ...rest } = options

  return useMutation({
    mutationFn,
    onSuccess: (data, vars, ctx) => {
      invalidateKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }))
      onSuccess?.(data, vars, ctx)
    },
    ...rest,
  })
}

/**
 * useInvalidateQueries: invalida caché tras mutaciones.
 * Uso: const invalidate = useInvalidateQueries(); invalidate(['servicios']);
 */
export function useInvalidateQueries() {
  const queryClient = useQueryClient()
  return (queryKey) => queryClient.invalidateQueries({ queryKey })
}
