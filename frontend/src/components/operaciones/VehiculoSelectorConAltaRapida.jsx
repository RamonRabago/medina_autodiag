import { useState, useEffect } from 'react'
import api from '../../services/api'
import ModalVehiculoRapido from '../ModalVehiculoRapido'
import { showError } from '../../utils/toast'

function textoVehiculo(v) {
  const partes = [v.marca, v.modelo, v.anio].filter(Boolean)
  const base = partes.join(' ')
  if (v.color) return `${base} (${v.color})`
  return base || `Vehículo #${v.id_vehiculo}`
}

/**
 * Selector de vehículo del cliente con alta rápida integrada.
 * Reutilizable en recepción rápida, OT nueva, citas, etc.
 */
export default function VehiculoSelectorConAltaRapida({
  idCliente,
  value,
  onChange,
  nombreCliente = 'Cliente',
  senalClienteNuevo = false,
  onSenalClienteNuevoConsumida,
  disabled = false,
  required = true,
  className = '',
}) {
  const [vehiculos, setVehiculos] = useState([])
  const [cargando, setCargando] = useState(false)
  const [modalAbierto, setModalAbierto] = useState(false)

  useEffect(() => {
    if (!idCliente) {
      setVehiculos([])
      return
    }
    setCargando(true)
    api
      .get(`/vehiculos/cliente/${idCliente}`)
      .then((r) => setVehiculos(Array.isArray(r.data) ? r.data : []))
      .catch((err) => {
        showError(err, 'Error al cargar vehículos')
        setVehiculos([])
      })
      .finally(() => setCargando(false))
  }, [idCliente])

  useEffect(() => {
    if (!required || !idCliente || !senalClienteNuevo || cargando) return
    if (vehiculos.length === 0) {
      setModalAbierto(true)
    }
    onSenalClienteNuevoConsumida?.()
  }, [required, idCliente, senalClienteNuevo, vehiculos, cargando, onSenalClienteNuevoConsumida])

  const handleVehiculoCreado = (nuevo) => {
    setVehiculos((prev) => [...prev, nuevo])
    onChange?.(String(nuevo.id_vehiculo), nuevo)
  }

  const abrirModal = () => setModalAbierto(true)

  if (!idCliente) {
    return (
      <p className="text-sm text-slate-500 px-4 py-3 border border-slate-200 rounded-lg bg-slate-50">
        Selecciona un cliente primero.
      </p>
    )
  }

  if (cargando) {
    return (
      <p className="text-sm text-slate-500 px-4 py-3 border border-slate-200 rounded-lg">
        Cargando vehículos...
      </p>
    )
  }

  return (
    <>
      <div className={className}>
        {vehiculos.length === 0 ? (
          <div className="p-4 border border-amber-200 bg-amber-50 rounded-lg">
            <p className="text-sm text-amber-800 mb-2">
              {required
                ? 'Este cliente no tiene vehículos registrados. Agrega uno para continuar.'
                : 'Este cliente no tiene vehículos. Puedes agregar uno o continuar sin vehículo.'}
            </p>
            <button
              type="button"
              onClick={abrirModal}
              disabled={disabled}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50"
            >
              ➕ Agregar vehículo
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <select
              value={value || ''}
              onChange={(e) => {
                const id = e.target.value
                const v = id ? vehiculos.find((x) => String(x.id_vehiculo) === id) : null
                onChange?.(id, v || null)
              }}
              required={required}
              disabled={disabled}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 disabled:bg-slate-50"
            >
              <option value="">{required ? 'Seleccionar vehículo...' : '— Sin vehículo —'}</option>
              {vehiculos.map((v) => (
                <option key={v.id_vehiculo} value={v.id_vehiculo}>
                  {textoVehiculo(v)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={abrirModal}
              disabled={disabled}
              className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm disabled:opacity-50"
              title="Agregar otro vehículo"
            >
              +
            </button>
          </div>
        )}
      </div>

      <ModalVehiculoRapido
        abierto={modalAbierto}
        onCerrar={() => setModalAbierto(false)}
        idCliente={idCliente}
        nombreCliente={nombreCliente}
        onVehiculoCreado={handleVehiculoCreado}
      />
    </>
  )
}
