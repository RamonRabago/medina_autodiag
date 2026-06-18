import { useEffect, useRef, useState } from 'react'
import OperacionGrupoPanel from './OperacionGrupoPanel'
import {
  GRUPOS_DASHBOARD,
  computeDefaultExpandedGroups,
} from '../../utils/operacionesGrupos'

/**
 * Contenedor dashboard operativo: 4 grupos disclosure (UX-1A).
 * Estado expandedGroups solo en memoria React.
 */
export default function OperacionesDashboardView({ metricas }) {
  const defaultsApplied = useRef(false)
  const [expandedGroups, setExpandedGroups] = useState(() => new Set())

  useEffect(() => {
    if (metricas && !defaultsApplied.current) {
      defaultsApplied.current = true
      setExpandedGroups(computeDefaultExpandedGroups(metricas))
    }
  }, [metricas])

  const toggleGroup = (grupoId) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(grupoId)) next.delete(grupoId)
      else next.add(grupoId)
      return next
    })
  }

  return (
    <div>
      {GRUPOS_DASHBOARD.map((grupo) => (
        <OperacionGrupoPanel
          key={grupo.id}
          grupo={grupo}
          metricas={metricas}
          expanded={expandedGroups.has(grupo.id)}
          onToggle={() => toggleGroup(grupo.id)}
        />
      ))}
    </div>
  )
}
