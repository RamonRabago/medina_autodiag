import api from '../services/api'
import { useApiQuery } from './useApi'

const RESUMEN_QUERY_KEY = ['operaciones', 'resumen']

/**
 * Resumen operativo A0 para bandejas (Mi Taller, Caja) o dashboard ADMIN ligero.
 * @param {number} limitItems
 * @param {{ incluirItems?: boolean, enabled?: boolean }} [options]
 */
export function useOperacionesResumen(limitItems = 30, { incluirItems = true, enabled = true } = {}) {
  return useApiQuery(
    [...RESUMEN_QUERY_KEY, limitItems, incluirItems],
    () =>
      api
        .get('/operaciones/resumen', {
          params: { limit_items: limitItems, incluir_items: incluirItems },
        })
        .then((r) => r.data),
    { staleTime: 15 * 1000, enabled }
  )
}

export { RESUMEN_QUERY_KEY }
