import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { seccionesManual } from '../content/manualContenido'

export default function Ayuda() {
  const [seccionActiva, setSeccionActiva] = useState(seccionesManual[0]?.id || '')

  return (
    <div className="min-h-0 flex flex-col">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4">Manual de usuario</h1>
      <p className="text-slate-600 mb-4">
        Guía de uso de MedinaAutoDiag. Selecciona un tema en el índice o desplázate por el contenido.
      </p>

      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0 max-h-[calc(100vh-14rem)]">
        {/* Índice */}
        <nav
          className="lg:w-56 shrink-0 bg-white rounded-lg border border-slate-200 p-4 max-h-[280px] lg:max-h-none overflow-y-auto"
          aria-label="Índice del manual"
        >
          <h2 className="text-sm font-semibold text-slate-500 uppercase mb-3">Índice</h2>
          <ul className="space-y-1">
            {seccionesManual.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => setSeccionActiva(s.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm min-h-[40px] touch-manipulation transition-colors ${
                    seccionActiva === s.id
                      ? 'bg-primary-100 text-primary-800 font-medium'
                      : 'text-slate-600 hover:bg-slate-100 active:bg-slate-200'
                  }`}
                >
                  {s.titulo}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Contenido */}
        <div className="flex-1 min-w-0 overflow-y-auto bg-white rounded-lg border border-slate-200 p-6 sm:p-8">
          {seccionesManual.map((s) => (
            <section
              key={s.id}
              id={s.id}
              className={`${seccionActiva === s.id ? '' : 'hidden'}`}
            >
              <h2 className="text-lg font-bold text-slate-800 mb-4 pb-2 border-b border-slate-200">
                {s.titulo}
              </h2>
              <div className="prose prose-slate max-w-none prose-headings:text-slate-800 prose-p:text-slate-600 prose-li:text-slate-600 prose-strong:text-slate-800">
                <ReactMarkdown>{s.contenido.trim()}</ReactMarkdown>
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
