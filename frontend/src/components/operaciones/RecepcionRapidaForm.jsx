import { useState, useEffect } from 'react'
import api from '../../services/api'
import ClienteAutocompleteConAltaRapida from '../ClienteAutocompleteConAltaRapida'
import VehiculoSelectorConAltaRapida from './VehiculoSelectorConAltaRapida'
import { aEntero } from '../../utils/numeros'
import { normalizeDetail } from '../../utils/toast'

const PRIORIDADES = ['BAJA', 'NORMAL', 'ALTA', 'URGENTE']

const FORM_INICIAL = {
  cliente_id: '',
  vehiculo_id: '',
  motivo: '',
  prioridad: 'NORMAL',
  tecnico_id: '',
  kilometraje: '',
  requiere_autorizacion: false,
  cita_id: null,
}

/**
 * Formulario de recepción rápida — OT mínima en PENDIENTE.
 *
 * Props de precarga (P2 cita → OT):
 * initialValues={{ cliente_id, cliente, vehiculo_id, motivo, cita_id }}
 */
export default function RecepcionRapidaForm({
  initialValues = {},
  onExito,
  userRol,
}) {
  const [form, setForm] = useState({ ...FORM_INICIAL, ...initialValues })
  const [clienteSeleccionado, setClienteSeleccionado] = useState(initialValues.cliente || null)
  const [senalClienteNuevo, setSenalClienteNuevo] = useState(false)
  const [tecnicos, setTecnicos] = useState([])
  const [cargandoTecnicos, setCargandoTecnicos] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get('/usuarios/')
      .then((r) => {
        const users = Array.isArray(r.data) ? r.data : []
        setTecnicos(users.filter((u) => u.rol === 'TECNICO'))
      })
      .catch(() => setTecnicos([]))
      .finally(() => setCargandoTecnicos(false))
  }, [])

  useEffect(() => {
    if (initialValues.cliente_id) {
      setForm((prev) => ({
        ...prev,
        cliente_id: String(initialValues.cliente_id),
        vehiculo_id: initialValues.vehiculo_id ? String(initialValues.vehiculo_id) : prev.vehiculo_id,
        motivo: initialValues.motivo ?? prev.motivo,
        cita_id: initialValues.cita_id ?? prev.cita_id,
      }))
    }
    if (initialValues.cliente) {
      setClienteSeleccionado(initialValues.cliente)
    }
  }, [initialValues.cliente_id, initialValues.vehiculo_id, initialValues.motivo, initialValues.cita_id, initialValues.cliente])

  const handleClienteChange = (clienteId, cliente) => {
    setClienteSeleccionado(cliente || null)
    setForm((prev) => ({
      ...prev,
      cliente_id: clienteId || '',
      vehiculo_id: '',
    }))
  }

  const handleClienteCreado = () => {
    setSenalClienteNuevo(true)
  }

  const validar = () => {
    if (!form.cliente_id) return 'Selecciona un cliente.'
    if (!form.vehiculo_id) return 'Selecciona o agrega un vehículo.'
    const motivo = (form.motivo || '').trim()
    if (!motivo) return 'Describe el motivo de ingreso.'
    if (motivo.length < 10) return 'Describe el motivo en al menos 10 caracteres.'
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const msg = validar()
    if (msg) {
      setError(msg)
      return
    }

    setEnviando(true)
    try {
      const payload = {
        cliente_id: aEntero(form.cliente_id),
        vehiculo_id: aEntero(form.vehiculo_id),
        motivo: form.motivo.trim(),
        prioridad: form.prioridad,
        requiere_autorizacion: form.requiere_autorizacion,
      }
      if (form.tecnico_id) payload.tecnico_id = aEntero(form.tecnico_id)
      if (form.kilometraje !== '' && form.kilometraje != null) {
        payload.kilometraje = aEntero(form.kilometraje)
      }
      if (form.cita_id) payload.cita_id = aEntero(form.cita_id)

      const res = await api.post('/ordenes-trabajo/recepcion-rapida', payload)
      onExito?.(res.data)
    } catch (err) {
      const status = err.response?.status
      if (status === 403) {
        setError('Tu rol no puede crear recepciones rápidas.')
      } else {
        setError(normalizeDetail(err.response?.data?.detail) || 'Error al registrar la recepción.')
      }
    } finally {
      setEnviando(false)
    }
  }

  const motivoLen = (form.motivo || '').trim().length

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm border border-red-100">{error}</div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label>
          <ClienteAutocompleteConAltaRapida
            value={form.cliente_id}
            onChange={handleClienteChange}
            onClienteCreado={handleClienteCreado}
            selectedCliente={clienteSeleccionado}
            userRol={userRol}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Vehículo *</label>
          <VehiculoSelectorConAltaRapida
            idCliente={form.cliente_id}
            value={form.vehiculo_id}
            onChange={(vehiculoId) => setForm((prev) => ({ ...prev, vehiculo_id: vehiculoId }))}
            nombreCliente={clienteSeleccionado?.nombre || 'Cliente'}
            senalClienteNuevo={senalClienteNuevo}
            onSenalClienteNuevoConsumida={() => setSenalClienteNuevo(false)}
            disabled={enviando}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Motivo de ingreso *</label>
          <textarea
            value={form.motivo}
            onChange={(e) => setForm((prev) => ({ ...prev, motivo: e.target.value }))}
            rows={3}
            placeholder="Ej: Ruido en frenos al frenar, revisión de luces, cambio de aceite..."
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-y min-h-[88px]"
            required
            minLength={10}
            maxLength={2000}
          />
          <p className={`text-xs mt-1 ${motivoLen > 0 && motivoLen < 10 ? 'text-amber-600' : 'text-slate-500'}`}>
            {motivoLen}/10 caracteres mínimos
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label>
            <select
              value={form.prioridad}
              onChange={(e) => setForm((prev) => ({ ...prev, prioridad: e.target.value }))}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            >
              {PRIORIDADES.map((p) => (
                <option key={p} value={p}>
                  {p.charAt(0) + p.slice(1).toLowerCase()}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Técnico (opcional)</label>
            <select
              value={form.tecnico_id || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, tecnico_id: e.target.value }))}
              disabled={cargandoTecnicos}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 disabled:bg-slate-50"
            >
              <option value="">Sin asignar</option>
              {tecnicos.map((t) => (
                <option key={t.id_usuario ?? t.id} value={t.id_usuario ?? t.id}>
                  {t.nombre || t.email}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Kilometraje (opcional)</label>
            <input
              type="number"
              min={0}
              value={form.kilometraje}
              onChange={(e) => setForm((prev) => ({ ...prev, kilometraje: e.target.value }))}
              placeholder="Ej: 85000"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={form.requiere_autorizacion}
                onChange={(e) => setForm((prev) => ({ ...prev, requiere_autorizacion: e.target.checked }))}
                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              Requiere autorización del cliente
            </label>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 sm:justify-end">
        <button
          type="submit"
          disabled={enviando}
          className="min-h-[44px] px-6 py-2.5 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 shadow-sm"
        >
          {enviando ? 'Registrando...' : 'Registrar recepción'}
        </button>
      </div>
    </form>
  )
}
