/**
 * Encabezado de página con franja roja y botones con iconos.
 * Estilo uniforme para Inventario, Clientes, Vehículos, Citas, etc.
 */

export function IconDownload() {
  return (
    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  )
}

export function IconPlus() {
  return (
    <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  )
}

/** Clases para botón Exportar (verde) */
export const btnExport =
  'min-h-[44px] px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-medium shadow-sm hover:bg-emerald-700 hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation inline-flex items-center gap-2'

/** Clases para botón Nuevo/Primario (azul) */
export const btnNuevo =
  'min-h-[44px] px-4 py-2 rounded-xl bg-primary-600 text-white text-sm font-medium shadow-sm hover:bg-primary-700 hover:shadow transition-all touch-manipulation inline-flex items-center gap-2'

/**
 * Encabezado con título, subtítulo opcional y franja roja.
 * @param {string} title - Título principal
 * @param {string} [subtitle] - Subtítulo opcional
 * @param {React.ReactNode} [children] - Botones de acción
 */
export default function PageHeader({ title, subtitle, children, className = '' }) {
  return (
    <div className={`flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 ${className}`.trim()}>
      <div className="border-l-4 border-red-500 pl-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800 tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap gap-2">{children}</div>}
    </div>
  )
}
