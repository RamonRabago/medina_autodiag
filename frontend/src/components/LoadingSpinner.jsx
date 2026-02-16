/**
 * Spinner de carga reutilizable.
 * @param {string} size - 'sm' | 'md' | 'lg'
 * @param {string} className - clases adicionales
 */
export default function LoadingSpinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-12 h-12 border-[3px]',
  }
  return (
    <div
      className={`animate-spin rounded-full border-primary-500 border-t-transparent ${sizes[size]} ${className}`}
      role="status"
      aria-label="Cargando"
    />
  )
}
