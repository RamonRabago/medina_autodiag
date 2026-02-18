/**
 * Tooltip simple: muestra texto de ayuda al pasar el mouse.
 * Usar title como fallback para accesibilidad.
 */
export default function Tooltip({ children, text, position = 'top' }) {
  if (!text) return children
  const posClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 -translate-y-2 mb-1',
    bottom: 'top-full left-1/2 -translate-x-1/2 translate-y-2 mt-1',
    right: 'left-full top-1/2 -translate-y-1/2 translate-x-2 ml-1',
    left: 'right-full top-1/2 -translate-y-1/2 -translate-x-2 mr-1',
  }
  const pos = posClasses[position] || posClasses.top
  return (
    <span className="relative inline-flex group/tip" title={text}>
      {children}
      <span
        className={`absolute z-50 px-2 py-1.5 text-xs font-medium text-white bg-slate-800 rounded shadow-lg whitespace-normal max-w-[220px] opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all duration-150 pointer-events-none ${pos}`}
      >
        {text}
      </span>
    </span>
  )
}
