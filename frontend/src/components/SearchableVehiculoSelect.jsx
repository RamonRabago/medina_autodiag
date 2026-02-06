import { useState, useRef, useEffect } from 'react'

/**
 * Select buscable de vehículos del catálogo. Escribe para filtrar por año, marca, modelo, versión o motor.
 */
export default function SearchableVehiculoSelect({
  vehiculos = [],
  value,
  onChange,
  placeholder = 'Buscar por año, marca, modelo...',
  className = '',
}) {
  const [abierto, setAbierto] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [highlightIdx, setHighlightIdx] = useState(0)
  const containerRef = useRef(null)

  const textoVehiculo = (v) => v?.descripcion || [v?.marca, v?.modelo, v?.anio].filter(Boolean).join(' ')

  const vehiculosFiltrados = vehiculos.filter((v) => {
    if (!v) return false
    const texto = textoVehiculo(v) + ' ' + (v.version_trim || '') + ' ' + (v.motor || '')
    return texto.toLowerCase().includes((busqueda || '').toLowerCase().trim())
  })

  const seleccionado = vehiculos.find((v) => v && String(v.id) === String(value))
  const textoMostrar = seleccionado ? textoVehiculo(seleccionado) : 'Ninguno'

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
    setHighlightIdx(-1) // -1 = Ninguno, 0+ = vehículos
  }, [abierto, busqueda])

  const seleccionar = (v) => {
    onChange(v ? String(v.id) : '')
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
    const totalOpciones = vehiculosFiltrados.length + 1 // +1 por "Ninguno"
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightIdx((i) => Math.min(i + 1, totalOpciones - 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIdx((i) => Math.max(i - 1, -1))
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      if (highlightIdx === -1) seleccionar(null)
      else if (vehiculosFiltrados[highlightIdx]) seleccionar(vehiculosFiltrados[highlightIdx])
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
        className={`w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${className}`}
      />
      {abierto && (
        <ul className="absolute z-20 mt-1 w-full max-h-48 overflow-auto bg-white border border-slate-200 rounded-lg shadow-lg py-1">
          <li
            className={`px-3 py-2 text-sm cursor-pointer hover:bg-slate-50 ${
              highlightIdx === -1 ? 'bg-primary-50 text-primary-800' : ''
            }`}
            onMouseEnter={() => setHighlightIdx(-1)}
            onMouseDown={(e) => {
              e.preventDefault()
              seleccionar(null)
            }}
          >
            <span className="text-slate-500">— Ninguno —</span>
          </li>
          {vehiculosFiltrados.length === 0 ? (
            <li className="px-3 py-2 text-sm text-slate-500">Sin resultados</li>
          ) : (
            vehiculosFiltrados.map((v, i) => (
              <li
                key={v.id}
                className={`px-3 py-2 text-sm cursor-pointer ${
                  i === highlightIdx ? 'bg-primary-50 text-primary-800' : 'hover:bg-slate-50'
                }`}
                onMouseEnter={() => setHighlightIdx(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  seleccionar(v)
                }}
              >
                {textoVehiculo(v)}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
