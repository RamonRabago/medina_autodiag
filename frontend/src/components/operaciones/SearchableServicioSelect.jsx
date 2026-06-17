import { useState, useRef, useEffect } from 'react'

/**
 * Select buscable de servicios. Escribe para filtrar por código o nombre.
 */
export default function SearchableServicioSelect({
  servicios = [],
  value,
  onChange,
  placeholder = 'Buscar servicio...',
  className = '',
  required = false,
}) {
  const [abierto, setAbierto] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [highlightIdx, setHighlightIdx] = useState(0)
  const containerRef = useRef(null)

  const idServicio = (s) => s?.id ?? s?.id_servicio

  const serviciosFiltrados = servicios.filter((s) => {
    if (!s) return false
    const texto = `${s.codigo || ''} ${s.nombre || ''}`
    return texto.toLowerCase().includes((busqueda || '').toLowerCase().trim())
  })

  const seleccionado = servicios.find((s) => String(idServicio(s)) === String(value))
  const textoMostrar = seleccionado
    ? `${seleccionado.codigo ? `${seleccionado.codigo} - ` : ''}${seleccionado.nombre}`
    : busqueda

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setAbierto(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (!abierto) return
    setHighlightIdx(0)
  }, [abierto, busqueda])

  const seleccionar = (s) => {
    onChange(String(idServicio(s)))
    setBusqueda('')
    setAbierto(false)
  }

  const handleKeyDown = (e) => {
    if (!abierto) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        e.preventDefault()
        setAbierto(true)
      }
      return
    }
    if (e.key === 'Escape') {
      setAbierto(false)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightIdx((i) => Math.min(i + 1, serviciosFiltrados.length - 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIdx((i) => Math.max(i - 1, 0))
      return
    }
    if (e.key === 'Enter' && serviciosFiltrados[highlightIdx]) {
      e.preventDefault()
      seleccionar(serviciosFiltrados[highlightIdx])
    }
  }

  return (
    <div ref={containerRef} className="relative min-w-[200px] flex-1">
      <input
        type="text"
        value={abierto ? busqueda : textoMostrar}
        onChange={(e) => {
          setBusqueda(e.target.value)
          setAbierto(true)
        }}
        onFocus={() => setAbierto(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        required={required && !value}
        className={`w-full px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 touch-manipulation ${className}`}
      />
      {abierto && (
        <ul className="absolute z-30 mt-1 w-full max-h-48 overflow-auto bg-white border border-slate-200 rounded-lg shadow-lg py-1">
          {serviciosFiltrados.length === 0 ? (
            <li className="px-3 py-2 text-sm text-slate-500">Sin resultados</li>
          ) : (
            serviciosFiltrados.map((s, i) => (
              <li
                key={idServicio(s)}
                className={`px-3 py-2 text-sm cursor-pointer ${
                  i === highlightIdx ? 'bg-primary-50 text-primary-800' : 'hover:bg-slate-50'
                }`}
                onMouseEnter={() => setHighlightIdx(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  seleccionar(s)
                }}
              >
                {s.codigo ? `${s.codigo} - ` : ''}
                {s.nombre}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
