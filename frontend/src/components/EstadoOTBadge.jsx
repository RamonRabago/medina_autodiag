import { getEstadoOTConfig } from '../utils/estadoOperativo'

/**
 * Badge de estado operativo para órdenes de trabajo.
 */
export default function EstadoOTBadge({ estado, className = '', size = 'sm' }) {
  const { label, className: estadoClass } = getEstadoOTConfig(estado)
  const sizeClass = size === 'md' ? 'text-sm px-2.5 py-1' : 'text-xs px-2 py-1'
  return (
    <span
      className={`inline-flex items-center rounded font-medium ${sizeClass} ${estadoClass} ${className}`.trim()}
    >
      {label}
    </span>
  )
}
