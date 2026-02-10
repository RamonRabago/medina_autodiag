import { useEffect } from 'react'

export default function Modal({ titulo, abierto, onCerrar, children, size = 'default' }) {
  useEffect(() => {
    const handle = (e) => e.key === 'Escape' && onCerrar?.()
    if (abierto) {
      document.addEventListener('keydown', handle)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handle)
      document.body.style.overflow = ''
    }
  }, [abierto, onCerrar])

  if (!abierto) return null

  return (
    <div className="fixed inset-0 z-50 min-h-screen flex items-center justify-center py-8 px-4 sm:py-12 sm:px-6 bg-black/50 overflow-y-auto" onClick={onCerrar}>
      <div
        className={`bg-white rounded-lg shadow-xl w-full max-h-[85vh] overflow-hidden flex flex-col ${size === 'xl' ? 'max-w-3xl' : size === 'lg' ? 'max-w-2xl' : 'max-w-lg'}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-4 py-3 border-b border-slate-200 shrink-0">
          <h2 className="text-lg font-semibold text-slate-800 truncate pr-2">{titulo}</h2>
          <button type="button" onClick={onCerrar} aria-label="Cerrar" className="min-h-[44px] min-w-[44px] flex items-center justify-center text-slate-400 hover:text-slate-600 active:bg-slate-100 rounded touch-manipulation text-2xl leading-none -mr-2">&times;</button>
        </div>
        <div className="p-4 overflow-y-auto flex-1">
          {children}
        </div>
      </div>
    </div>
  )
}
