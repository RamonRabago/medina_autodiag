import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../services/api'
import ModalClienteRapido, { ROLES_CREAR } from './ModalClienteRapido'
import { parseTextoBusquedaCliente, textoCliente } from '../utils/clienteBusqueda'
import { showError } from '../utils/toast'

/**
 * Autocomplete de clientes con alta rápida contextual en el dropdown.
 * UX V2: una sola acción de creación — «Crear nuevo cliente "texto"» al buscar.
 * Reutilizable en OT, citas, ventas, cotizaciones, recepción rápida, etc.
 */
export default function ClienteAutocompleteConAltaRapida({
  value,
  onChange,
  onClienteCreado,
  selectedCliente: selectedClienteProp,
  puedeCrear,
  userRol,
  placeholder = 'Escribe para buscar (nombre o teléfono)...',
  className = '',
}) {
  const puedeCrearCliente = puedeCrear ?? ROLES_CREAR.includes(userRol)

  const [busqueda, setBusqueda] = useState('')
  const [abierto, setAbierto] = useState(false)
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  const [selectedCliente, setSelectedCliente] = useState(selectedClienteProp || null)
  const [modalCliente, setModalCliente] = useState(false)
  const [valoresInicialesModal, setValoresInicialesModal] = useState({ nombre: '', telefono: '', email: '', direccion: '' })
  const containerRef = useRef(null)
  const debounceRef = useRef(null)

  useEffect(() => {
    if (selectedClienteProp) {
      setSelectedCliente(selectedClienteProp)
    }
  }, [selectedClienteProp])

  useEffect(() => {
    if (!value) {
      setSelectedCliente(null)
      return
    }
    if (selectedCliente && String(selectedCliente.id_cliente) === String(value)) return

    api
      .get(`/clientes/${value}`)
      .then((r) => setSelectedCliente(r.data))
      .catch(() => {
        /* Si no puede leer detalle (ej. CAJA), mantener selección parcial */
      })
  }, [value])

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setAbierto(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const buscarClientes = useCallback(async (term) => {
    const q = (term || '').trim()
    if (!q) {
      setResultados([])
      return
    }
    setBuscando(true)
    try {
      const res = await api.get('/clientes/', { params: { buscar: q, limit: 20, skip: 0 } })
      const lista = res.data?.clientes ?? (Array.isArray(res.data) ? res.data : [])
      setResultados(lista)
    } catch (err) {
      showError(err, 'Error al buscar clientes')
      setResultados([])
    } finally {
      setBuscando(false)
    }
  }, [])

  useEffect(() => {
    if (!abierto || value) return
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => buscarClientes(busqueda), 280)
    return () => clearTimeout(debounceRef.current)
  }, [busqueda, abierto, value, buscarClientes])

  const seleccionarCliente = (cliente) => {
    setSelectedCliente(cliente)
    onChange?.(String(cliente.id_cliente), cliente)
    setBusqueda('')
    setAbierto(false)
  }

  const limpiar = () => {
    setSelectedCliente(null)
    setBusqueda('')
    onChange?.('', null)
  }

  const abrirModalCrear = (textoBusqueda) => {
    const parsed = parseTextoBusquedaCliente(textoBusqueda || busqueda)
    setValoresInicialesModal(parsed)
    setModalCliente(true)
    setAbierto(false)
  }

  const handleClienteCreado = (cliente) => {
    seleccionarCliente(cliente)
    onClienteCreado?.(cliente)
  }

  const handleSeleccionarExistente = (cliente) => {
    seleccionarCliente(cliente)
  }

  const textoInput = value && selectedCliente ? selectedCliente.nombre : busqueda
  const terminoBusqueda = (busqueda || '').trim()
  const mostrarCrear =
    puedeCrearCliente &&
    abierto &&
    !value &&
    terminoBusqueda.length >= 2 &&
    !buscando &&
    resultados.length === 0

  return (
    <>
      <div ref={containerRef} className={`relative ${className}`}>
        <div className="flex gap-1">
          <input
            type="text"
            value={textoInput}
            onChange={(e) => {
              const v = e.target.value
              if (value) limpiar()
              setBusqueda(v)
              setAbierto(true)
            }}
            onFocus={() => {
              if (!value) setAbierto(true)
            }}
            placeholder={placeholder}
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            autoComplete="off"
          />
          {value && (
            <button
              type="button"
              onClick={limpiar}
              className="px-3 py-2 border border-slate-300 rounded-lg text-slate-500 hover:bg-slate-50"
              title="Limpiar"
            >
              ✕
            </button>
          )}
        </div>

        {abierto && !value && (
          <div className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
            {buscando && (
              <div className="px-4 py-3 text-sm text-slate-500">Buscando...</div>
            )}
            {!buscando && resultados.map((c) => (
              <button
                key={c.id_cliente}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => seleccionarCliente(c)}
                className="w-full px-4 py-2 text-left hover:bg-slate-50 text-sm text-slate-700 border-b border-slate-50 last:border-0"
              >
                {textoCliente(c)}
              </button>
            ))}
            {mostrarCrear && (
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => abrirModalCrear(terminoBusqueda)}
                className="w-full px-4 py-3 text-left text-sm font-medium text-primary-700 hover:bg-primary-50 border-t border-slate-100"
              >
                ➕ Crear nuevo cliente &quot;{terminoBusqueda}&quot;
              </button>
            )}
            {!buscando && terminoBusqueda.length >= 2 && resultados.length > 0 && puedeCrearCliente && (
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => abrirModalCrear(terminoBusqueda)}
                className="w-full px-4 py-2.5 text-left text-sm text-primary-600 hover:bg-primary-50 border-t border-slate-100"
              >
                ➕ Crear nuevo cliente &quot;{terminoBusqueda}&quot;
              </button>
            )}
            {!buscando && terminoBusqueda.length > 0 && terminoBusqueda.length < 2 && (
              <div className="px-4 py-3 text-sm text-slate-500">Escribe al menos 2 caracteres para buscar.</div>
            )}
            {!buscando && !terminoBusqueda && (
              <div className="px-4 py-3 text-sm text-slate-500">Escribe nombre o teléfono del cliente.</div>
            )}
            {!puedeCrearCliente && mostrarCrear && (
              <div className="px-4 py-2 text-xs text-slate-500 border-t border-slate-100">
                Tu rol no permite crear clientes. Busca un cliente existente.
              </div>
            )}
          </div>
        )}
      </div>

      <ModalClienteRapido
        abierto={modalCliente}
        onCerrar={() => setModalCliente(false)}
        valoresIniciales={valoresInicialesModal}
        onClienteCreado={handleClienteCreado}
        onSeleccionarExistente={handleSeleccionarExistente}
        puedeCrear={puedeCrearCliente}
        zIndex={60}
      />
    </>
  )
}
