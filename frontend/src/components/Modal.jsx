import { useEffect } from 'react'

export default function Modal({ titulo, abierto, onCerrar, children }) {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onCerrar}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-4 py-3 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-800">{titulo}</h2>
          <button onClick={onCerrar} className="text-slate-400 hover:text-slate-600 text-2xl leading-none">&times;</button>
        </div>
        <div className="p-4 overflow-y-auto flex-1">
          {children}
        </div>
      </div>
    </div>
  )
}
