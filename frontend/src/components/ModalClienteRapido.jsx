import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from './Modal'
import { normalizeDetail, showSuccess } from '../utils/toast'

const ROLES_CREAR = ['ADMIN', 'EMPLEADO', 'TECNICO']

/**
 * Modal de alta rápida de cliente (nombre + teléfono obligatorios).
 */
export default function ModalClienteRapido({
  abierto,
  onCerrar,
  valoresIniciales = { nombre: '', telefono: '', email: '', direccion: '' },
  onClienteCreado,
  onSeleccionarExistente,
  puedeCrear = true,
}) {
  const [form, setForm] = useState({ nombre: '', telefono: '', email: '', direccion: '' })
  const [error, setError] = useState('')
  const [clienteDuplicado, setClienteDuplicado] = useState(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (abierto) {
      setForm({
        nombre: valoresIniciales.nombre || '',
        telefono: valoresIniciales.telefono || '',
        email: valoresIniciales.email || '',
        direccion: valoresIniciales.direccion || '',
      })
      setError('')
      setClienteDuplicado(null)
    }
  }, [abierto, valoresIniciales])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setClienteDuplicado(null)

    const nombre = (form.nombre || '').trim()
    const telefono = (form.telefono || '').trim()
    if (!nombre) {
      setError('El nombre es obligatorio.')
      return
    }
    if (nombre.length < 3) {
      setError('El nombre debe tener al menos 3 caracteres.')
      return
    }
    if (!telefono) {
      setError('El teléfono es obligatorio.')
      return
    }
    if (!puedeCrear) {
      setError('No tienes permisos para crear clientes.')
      return
    }

    setEnviando(true)
    try {
      const res = await api.post('/clientes/', {
        nombre,
        telefono,
        email: (form.email || '').trim() || null,
        direccion: (form.direccion || '').trim() || null,
      })
      showSuccess('Cliente creado correctamente')
      onClienteCreado?.(res.data)
      onCerrar?.()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (detail?.codigo === 'TELEFONO_DUPLICADO' && detail?.cliente_existente) {
        setError(detail.mensaje || 'Ya existe un cliente registrado con este teléfono.')
        setClienteDuplicado(detail.cliente_existente)
        return
      }
      setError(normalizeDetail(detail) || 'Error al crear cliente')
    } finally {
      setEnviando(false)
    }
  }

  const seleccionarExistente = () => {
    if (clienteDuplicado) {
      onSeleccionarExistente?.(clienteDuplicado)
      onCerrar?.()
    }
  }

  return (
    <Modal titulo="Nuevo cliente" abierto={abierto} onCerrar={onCerrar}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm whitespace-pre-line">{error}</div>
        )}
        {clienteDuplicado && (
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm">
            <p className="text-amber-900 mb-2">
              Cliente existente: <strong>{clienteDuplicado.nombre}</strong>
              {clienteDuplicado.telefono ? ` (${clienteDuplicado.telefono})` : ''}
            </p>
            <button
              type="button"
              onClick={seleccionarExistente}
              className="px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium"
            >
              Seleccionar este cliente
            </button>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Nombre completo *</label>
          <input
            type="text"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            required
            minLength={3}
            placeholder="Ej: Pedro Martínez"
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            autoFocus
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono *</label>
          <input
            type="tel"
            value={form.telefono}
            onChange={(e) => setForm({ ...form, telefono: e.target.value })}
            required
            placeholder="Ej: 644 123 4567"
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Correo electrónico (opcional)</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="Ej: cliente@email.com"
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Dirección (opcional)</label>
          <input
            type="text"
            value={form.direccion}
            onChange={(e) => setForm({ ...form, direccion: e.target.value })}
            placeholder="Ej: Av. Principal 123"
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onCerrar} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
            Cancelar
          </button>
          <button
            type="submit"
            disabled={enviando || !puedeCrear}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {enviando ? 'Guardando...' : 'Crear cliente'}
          </button>
        </div>
        {!puedeCrear && (
          <p className="text-xs text-slate-500">Tu rol no permite crear clientes. Contacta a un administrador.</p>
        )}
      </form>
    </Modal>
  )
}

export { ROLES_CREAR }
