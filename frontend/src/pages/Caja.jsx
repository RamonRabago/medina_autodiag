import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'

export default function Caja() {
  const [turno, setTurno] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modalAbrir, setModalAbrir] = useState(false)
  const [modalCerrar, setModalCerrar] = useState(false)
  const [montoApertura, setMontoApertura] = useState('')
  const [montoCierre, setMontoCierre] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  const cargar = () => {
    api.get('/caja/turno-actual').then((res) => setTurno(res.data)).catch(() => setTurno(null))
  }

  useEffect(() => {
    cargar()
    setLoading(false)
  }, [])

  const abrirTurno = async (e) => {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      await api.post('/caja/abrir', { monto_apertura: parseFloat(montoApertura) || 0 })
      cargar()
      setModalAbrir(false)
      setMontoApertura('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al abrir turno')
    } finally {
      setGuardando(false)
    }
  }

  const cerrarTurno = async (e) => {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      await api.post('/caja/cerrar', { monto_cierre: parseFloat(montoCierre) || 0 })
      cargar()
      setModalCerrar(false)
      setMontoCierre('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al cerrar turno')
    } finally {
      setGuardando(false)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Caja</h1>
      <div className="bg-white rounded-lg shadow p-6 max-w-md">
        <h3 className="font-semibold text-slate-700 mb-2">Turno actual</h3>
        {turno && turno.estado === 'ABIERTO' ? (
          <div>
            <p className="text-green-600 font-medium">Turno abierto</p>
            <p className="text-sm text-slate-500 mt-1">Apertura: {turno.fecha_apertura ? new Date(turno.fecha_apertura).toLocaleString() : '-'}</p>
            <p className="text-sm text-slate-500">Monto apertura: ${(Number(turno.monto_apertura) || 0).toFixed(2)}</p>
            <button onClick={() => { setModalCerrar(true); setError('') }} className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Cerrar turno</button>
          </div>
        ) : (
          <div>
            <p className="text-slate-600">No hay turno abierto</p>
            <button onClick={() => { setModalAbrir(true); setError('') }} className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">Abrir turno</button>
          </div>
        )}
      </div>

      <Modal titulo="Abrir turno" abierto={modalAbrir} onCerrar={() => setModalAbrir(false)}>
        <form onSubmit={abrirTurno} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto de apertura</label>
            <input type="number" step={0.01} min={0} value={montoApertura} onChange={(e) => setMontoApertura(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="0.00" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalAbrir(false)} className="px-4 py-2 border rounded-lg">Cancelar</button>
            <button type="submit" disabled={guardando} className="px-4 py-2 bg-primary-600 text-white rounded-lg disabled:opacity-50">{guardando ? 'Abriendo...' : 'Abrir'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Cerrar turno" abierto={modalCerrar} onCerrar={() => setModalCerrar(false)}>
        <form onSubmit={cerrarTurno} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Monto en caja al cierre</label>
            <input type="number" step={0.01} min={0} value={montoCierre} onChange={(e) => setMontoCierre(e.target.value)} className="w-full px-4 py-2 border rounded-lg" placeholder="0.00" />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCerrar(false)} className="px-4 py-2 border rounded-lg">Cancelar</button>
            <button type="submit" disabled={guardando} className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">{guardando ? 'Cerrando...' : 'Cerrar'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
