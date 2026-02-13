import { useState, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { seccionesManual } from '../content/manualContenido'

/** Componentes personalizados para ReactMarkdown */
const MarkdownComponents = {
  img: ({ src, alt }) => (
    <span className="block my-6">
      <img
        src={src}
        alt={alt || 'Referencia'}
        className="max-w-full h-auto rounded-lg border border-slate-200 shadow-md mx-auto"
        loading="lazy"
      />
      {alt && (
        <span className="block mt-2 text-center text-sm text-slate-500 italic">{alt}</span>
      )}
    </span>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-semibold text-slate-800 mt-8 mb-3 first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-slate-700 mt-6 mb-2">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="text-slate-600 leading-relaxed mb-4">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="list-disc pl-6 mb-4 space-y-2 text-slate-600">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal pl-6 mb-4 space-y-2 text-slate-600">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-800">{children}</strong>
  ),
}

function normalizeForSearch(text) {
  return String(text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

export default function Ayuda() {
  const idInicial = seccionesManual.find((s) => s.id === getHash())?.id || seccionesManual[0]?.id || ''
  const [seccionActiva, setSeccionActiva] = useState(idInicial)
  const [busqueda, setBusqueda] = useState('')

  function getHash() {
    const h = window.location.hash.slice(1)
    return h || null
  }

  const seccionesFiltradas = busqueda.trim()
    ? seccionesManual.filter((s) => {
        const q = normalizeForSearch(busqueda)
        return (
          normalizeForSearch(s.titulo).includes(q) ||
          normalizeForSearch(s.contenido).includes(q)
        )
      })
    : seccionesManual

  const irASeccion = useCallback((id) => {
    if (!id || !seccionesManual.find((s) => s.id === id)) return
    setSeccionActiva(id)
    window.history.replaceState(null, '', `#${id}`)
  }, [])

  useEffect(() => {
    const h = getHash()
    if (h && seccionesManual.some((s) => s.id === h) && h !== seccionActiva) {
      setSeccionActiva(h)
    }
  }, [])

  useEffect(() => {
    const handler = () => {
      const h = getHash()
      if (h && seccionesManual.some((s) => s.id === h)) setSeccionActiva(h)
    }
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  useEffect(() => {
    if (seccionActiva && !seccionesFiltradas.some((s) => s.id === seccionActiva) && seccionesFiltradas.length > 0) {
      setSeccionActiva(seccionesFiltradas[0].id)
    }
  }, [busqueda, seccionesFiltradas, seccionActiva])

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 mb-6">
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Manual de usuario</h1>
        <p className="mt-1 text-slate-600 text-[15px]">
          Guía de uso de MedinaAutoDiag. Selecciona un tema o busca por palabra.
        </p>
      </header>

      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        {/* Índice */}
        <nav
          className="lg:w-72 shrink-0 bg-white rounded-xl border border-slate-200 shadow-sm p-4 max-h-[400px] lg:max-h-[calc(100vh-14rem)] overflow-hidden flex flex-col"
          aria-label="Índice del manual"
        >
          <div className="shrink-0 mb-3">
            <input
              type="search"
              placeholder="Buscar en el manual..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-primary-500/25 focus:border-primary-400 placeholder:text-slate-400"
              aria-label="Buscar en el manual"
            />
          </div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Contenido</h2>
          <ul className="space-y-0.5 overflow-y-auto flex-1 min-h-0">
            {seccionesFiltradas.length === 0 ? (
              <li className="px-3 py-2 text-sm text-slate-500 italic">No hay resultados</li>
            ) : (
              seccionesFiltradas.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => irASeccion(s.id)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors duration-150 ${
                      seccionActiva === s.id
                        ? 'bg-primary-50 text-primary-700 font-medium'
                        : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'
                    }`}
                  >
                    {s.titulo}
                  </button>
                </li>
              ))
            )}
          </ul>
        </nav>

        {/* Contenido */}
        <article className="flex-1 min-w-0 overflow-y-auto bg-white rounded-xl border border-slate-200 shadow-sm">
          {seccionesFiltradas.map((s) => (
            <section
              key={s.id}
              id={s.id}
              className={`p-8 lg:p-10 scroll-mt-4 ${seccionActiva === s.id ? '' : 'hidden'}`}
              aria-hidden={seccionActiva !== s.id}
            >
              <h2 className="text-[1.25rem] font-bold text-slate-800 mb-6 pb-3 border-b border-slate-200">
                {s.titulo}
              </h2>
              <div className="prose prose-slate prose-sm max-w-3xl prose-headings:font-semibold prose-p:mb-4 prose-ul:my-4 prose-ol:my-4 prose-li:my-1 prose-img:rounded-lg prose-img:shadow-md">
                <ReactMarkdown components={MarkdownComponents}>
                  {s.contenido.trim()}
                </ReactMarkdown>
              </div>
            </section>
          ))}
        </article>
      </div>
    </div>
  )
}
