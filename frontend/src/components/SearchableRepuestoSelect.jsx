import { useState, useRef, useEffect } from 'react'

/**
 * Select buscable de repuestos. Escribe para filtrar por código o nombre.
 */
export default function SearchableRepuestoSelect({
  repuestos = [],
  value,
  onChange,
  placeholder = 'Repuesto...',
  className = '',
  required = false,
}) {
  const [abierto, setAbierto] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [highlightIdx, setHighlightIdx] = useState(0)
  const containerRef = useRef(null)

  const repuestosFiltrados = repuestos.filter((r) => {
    if (!r || r.eliminado) return false
    const texto = (r.codigo || '') + ' ' + (r.nombre || '')
    return texto.toLowerCase().includes((busqueda || '').toLowerCase().trim())
  })

  const seleccionado = repuestos.find((r) => r && r.id_repuesto === parseInt(value, 10))
  const textoMostrar = seleccionado ? `${seleccionado.codigo} - ${seleccionado.nombre}` : busqueda

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

  const seleccionar = (r) => {
    onChange(String(r.id_repuesto))
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
      setHighlightIdx((i) => Math.min(i + 1, repuestosFiltrados.length - 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIdx((i) => Math.max(i - 1, 0))
      return
    }
    if (e.key === 'Enter' && repuestosFiltrados[highlightIdx]) {
      e.preventDefault()
      seleccionar(repuestosFiltrados[highlightIdx])
    }
  }

  return (
    <div ref={containerRef} className="relative flex-1 min-w-[200px]">
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
        className={`w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${className}`}
      />
      {abierto && (
        <ul className="absolute z-20 mt-1 w-full max-h-48 overflow-auto bg-white border border-slate-200 rounded-lg shadow-lg py-1">
          {repuestosFiltrados.length === 0 ? (
            <li className="px-3 py-2 text-sm text-slate-500">Sin resultados</li>
          ) : (
            repuestosFiltrados.map((r, i) => (
              <li
                key={r.id_repuesto}
                className={`px-3 py-2 text-sm cursor-pointer ${
                  i === highlightIdx ? 'bg-primary-50 text-primary-800' : 'hover:bg-slate-50'
                }`}
                onMouseEnter={() => setHighlightIdx(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  seleccionar(r)
                }}
              >
                {r.codigo} - {r.nombre}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
