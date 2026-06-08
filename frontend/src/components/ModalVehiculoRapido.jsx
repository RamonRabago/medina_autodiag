import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from './Modal'
import { aEntero } from '../utils/numeros'
import { showError } from '../utils/toast'

/**
 * Modal reutilizable para alta rápida de vehículo asociado a un cliente.
 */
export default function ModalVehiculoRapido({
  abierto,
  onCerrar,
  idCliente,
  nombreCliente = 'Cliente',
  onVehiculoCreado,
  zIndex = 60,
}) {
  const [form, setForm] = useState({
    marca: '',
    modelo: '',
    anio: new Date().getFullYear(),
    color: '',
    numero_serie: '',
    motor: '',
  })
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (abierto) {
      setForm({
        marca: '',
        modelo: '',
        anio: new Date().getFullYear(),
        color: '',
        numero_serie: '',
        motor: '',
      })
    }
  }, [abierto])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!idCliente) return
    setEnviando(true)
    try {
      const res = await api.post('/vehiculos/', {
        id_cliente: aEntero(idCliente),
        marca: form.marca.trim(),
        modelo: form.modelo.trim(),
        anio: aEntero(form.anio),
        color: form.color?.trim() || null,
        numero_serie: form.numero_serie?.trim() || null,
        motor: form.motor?.trim() || null,
      })
      onVehiculoCreado?.(res.data)
      onCerrar?.()
    } catch (err) {
      showError(err, 'Error al agregar vehículo')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Modal titulo={`Agregar vehículo — ${nombreCliente}`} abierto={abierto} onCerrar={onCerrar} zIndex={zIndex}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label>
            <input
              type="text"
              value={form.marca}
              onChange={(e) => setForm({ ...form, marca: e.target.value })}
              required
              placeholder="Ej: Nissan"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label>
            <input
              type="text"
              value={form.modelo}
              onChange={(e) => setForm({ ...form, modelo: e.target.value })}
              required
              placeholder="Ej: Versa"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Año *</label>
            <input
              type="number"
              min={1900}
              max={2030}
              value={form.anio}
              onChange={(e) => setForm({ ...form, anio: e.target.value })}
              required
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Color (opcional)</label>
            <input
              type="text"
              value={form.color}
              onChange={(e) => setForm({ ...form, color: e.target.value })}
              placeholder="Ej: Blanco"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motor (opcional)</label>
            <input
              type="text"
              value={form.motor}
              onChange={(e) => setForm({ ...form, motor: e.target.value })}
              placeholder="Ej: 1.8"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">VIN / Núm. serie (opcional)</label>
            <input
              type="text"
              value={form.numero_serie}
              onChange={(e) => setForm({ ...form, numero_serie: e.target.value })}
              placeholder="Ej: 1HGBH41JXMN109186"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onCerrar} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
            Cancelar
          </button>
          <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
            {enviando ? 'Guardando...' : 'Agregar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
