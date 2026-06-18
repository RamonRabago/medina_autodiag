/**
 * Primitivo accordion accesible (UX-1A).
 * `actions` (p. ej. «Ir →») queda fuera del botón expandir/colapsar.
 */
export default function DisclosurePanel({
  id,
  expanded,
  onToggle,
  trigger,
  actions,
  children,
  className = '',
}) {
  const contentId = `${id}-content`

  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden ${className}`}>
      <div className="flex items-stretch min-h-[52px]">
        <button
          type="button"
          id={`${id}-trigger`}
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={onToggle}
          className="flex flex-1 items-center gap-2 sm:gap-3 px-4 py-3 text-left touch-manipulation min-h-[52px] hover:bg-slate-50 active:bg-slate-100 transition-colors min-w-0"
        >
          {trigger}
        </button>
        {actions && (
          <div className="flex items-center shrink-0 border-l border-slate-100 px-1">
            {actions}
          </div>
        )}
      </div>
      {expanded && (
        <div id={contentId} role="region" aria-labelledby={`${id}-trigger`} className="border-t border-slate-100">
          {children}
        </div>
      )}
    </div>
  )
}

export function DisclosureChevron({ expanded }) {
  return (
    <span
      aria-hidden
      className={`ml-auto shrink-0 text-slate-400 transition-transform duration-200 ${
        expanded ? 'rotate-90' : ''
      }`}
    >
      ▶
    </span>
  )
}
