import api from '../services/api'
import { useApiQuery } from './useApi'

const RESUMEN_QUERY_KEY = ['operaciones', 'resumen']

/**
 * Resumen operativo A0 para bandejas (Mi Taller, futuro Centro Operativo).
 */
export function useOperacionesResumen(limitItems = 30) {
  return useApiQuery(
    [...RESUMEN_QUERY_KEY, limitItems],
    () =>
      api
        .get('/operaciones/resumen', {
          params: { limit_items: limitItems, incluir_items: true },
        })
        .then((r) => r.data),
    { staleTime: 15 * 1000 }
  )
}

export { RESUMEN_QUERY_KEY }
