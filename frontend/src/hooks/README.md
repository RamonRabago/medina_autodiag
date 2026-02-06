# Hooks - TanStack Query

## useApiQuery (GET con caché)

```js
import { useApiQuery } from '../hooks/useApi'

const { data, isLoading, error, refetch } = useApiQuery(
  ['servicios', pagina, buscar],
  () => api.get('/servicios/', { params }).then(r => r.data),
  { enabled: !!user }
)
```

- **queryKey**: array único (cambia → refetch)
- **queryFn**: función async que retorna los datos
- **enabled**: false para no ejecutar (p. ej. cuando falta auth)

## useApiMutation (POST/PUT/DELETE)

```js
import { useApiMutation, useInvalidateQueries } from '../hooks/useApi'

const invalidate = useInvalidateQueries()
const mutation = useApiMutation(
  (payload) => api.post('/servicios/', payload),
  { invalidateKeys: [['servicios']] }
)
mutation.mutate(payload)
// O patrón manual:
await api.post('/servicios/', payload)
invalidate(['servicios'])
```

## Coexistencia

Los componentes que usan `api.get` + `useEffect` + `useState` siguen funcionando.
Migrar a `useApiQuery` cuando se quiera caché, reintentos y mejor UX.
