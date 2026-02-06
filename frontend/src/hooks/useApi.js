/**
 * Hooks para usar TanStack Query con la API existente.
 * Proporciona caché, reintentos y refetch automático.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'

/**
 * useApiQuery: caché de GET con reintentos y refetch.
 * @param {string[]} queryKey - Clave única para la caché (ej: ['servicios', pagina, buscar])
 * @param {function} queryFn - Función async () => api.get(url, { params }).then(r => r.data)
 * @param {object} options - Opciones adicionales de useQuery
 */
export function useApiQuery(queryKey, queryFn, options = {}) {
  return useQuery({
    queryKey,
    queryFn,
    ...options,
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
