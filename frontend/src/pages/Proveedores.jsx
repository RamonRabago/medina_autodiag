import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { showError } from '../utils/toast'

export default function Proveedores() {
  const { user } = useAuth()
  const [proveedores, setProveedores] = useState([])
  const [loading, setLoading] = useState(true)
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const limit = 20

  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({ nombre: '', contacto: '', telefono: '', email: '', direccion: '', rfc: '', activo: true })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalDesactivar, setModalDesactivar] = useState(false)
  const [proveedorADesactivar, setProveedorADesactivar] = useState(null)
  const [enviandoDesactivar, setEnviandoDesactivar] = useState(false)
  const [mostrarInactivos, setMostrarInactivos] = useState(false)

  const puedeEditar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'
  const puedeDesactivar = user?.rol === 'ADMIN'

  const cargar = () => {
    setLoading(true)
    const params = { skip: (pagina - 1) * limit, limit }
    if (buscar.trim()) params.buscar = buscar.trim()
    if (mostrarInactivos) params.activo = false
    else params.activo = true
    api.get('/proveedores/', { params }).then((res) => {
      const d = res.data
      setProveedores(d?.proveedores ?? [])
      setTotal(d?.total ?? 0)
      setTotalPaginas(d?.total_paginas ?? 1)
    }).catch(() => setProveedores([])).finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [pagina, buscar, mostrarInactivos])

  const abrirNuevo = () => {
    setEditando(null)
    setForm({ nombre: '', contacto: '', telefono: '', email: '', direccion: '', rfc: '', activo: true })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = (p) => {
    setEditando(p)
    setForm({
      nombre: p.nombre || '',
      contacto: p.contacto || '',
      telefono: p.telefono || '',
      email: p.email || '',
      direccion: p.direccion || '',
      rfc: p.rfc || '',
      activo: p.activo !== false,
    })
    setError('')
    setModalAbierto(true)
  }

  const guardar = async (e) => {
    e?.preventDefault?.()
    setError('')
    if (!form.nombre?.trim()) { setError('El nombre es obligatorio'); return }
    setEnviando(true)
    try {
      const payload = {
        nombre: form.nombre.trim(),
        contacto: form.contacto?.trim() || null,
        telefono: form.telefono?.trim() || null,
        email: form.email?.trim() || null,
        direccion: form.direccion?.trim() || null,
        rfc: form.rfc?.trim()?.toUpperCase() || null,
        activo: form.activo,
      }
      if (editando) {
        await api.put(`/proveedores/${editando.id_proveedor}`, payload)
      } else {
        await api.post('/proveedores/', payload)
      }
      setModalAbierto(false)
      cargar()
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg.map((m) => m?.msg ?? m).join(', ') : (typeof msg === 'string' ? msg : 'Error al guardar'))
    } finally {
      setEnviando(false)
    }
  }

  const abrirModalDesactivar = (p) => {
    setProveedorADesactivar(p)
    setModalDesactivar(true)
  }

  const confirmarDesactivar = async () => {
    if (!proveedorADesactivar) return
    setEnviandoDesactivar(true)
    try {
      await api.delete(`/proveedores/${proveedorADesactivar.id_proveedor}`)
      setModalDesactivar(false)
      setProveedorADesactivar(null)
      cargar()
    } catch (err) {
      showError(err, 'Error al desactivar')
    } finally {
      setEnviandoDesactivar(false)
    }
  }

  const reactivar = async (p) => {
    try {
      await api.post(`/proveedores/${p.id_proveedor}/reactivar`)
      cargar()
    } catch (err) {
      showError(err, 'Error al reactivar')
    }
  }

  if (loading && proveedores.length === 0) return <p className="text-slate-500 p-8">Cargando...</p>

  return (
    <div className="min-h-0 flex flex-col">
      <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Proveedores</h1>
        {puedeEditar && (
          <button type="button" onClick={abrirNuevo} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation">
            + Nuevo proveedor
          </button>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4 flex flex-wrap gap-3 items-center border border-slate-200">
        <input
          type="text"
          placeholder="Buscar por nombre, teléfono o email..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
          className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg flex-1 min-w-0 touch-manipulation"
        />
        <label className="flex items-center gap-2 text-sm text-slate-600 min-h-[44px] cursor-pointer touch-manipulation">
          <input
            type="checkbox"
            checked={mostrarInactivos}
            onChange={(e) => { setMostrarInactivos(e.target.checked); setPagina(1) }}
            className="rounded border-slate-300 w-5 h-5"
          />
          Mostrar inactivos
        </label>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 flex-1 min-h-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Contacto</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Teléfono</th>
                <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
                <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
                {puedeEditar && (
                  <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {proveedores.length === 0 ? (
                <tr><td colSpan={puedeEditar ? 7 : 6} className="px-4 py-8 text-center text-slate-500">No hay proveedores</td></tr>
              ) : (
                proveedores.map((p) => (
                  <tr key={p.id_proveedor} className="hover:bg-slate-50">
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{p.id_proveedor}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm font-medium text-slate-800">{p.nombre}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{p.contacto || '-'}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{p.telefono || '-'}</td>
                    <td className="px-2 sm:px-4 py-3 text-sm text-slate-600">{p.email || '-'}</td>
                    <td className="px-2 sm:px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${p.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                        {p.activo !== false ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    {puedeEditar && (
                      <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex justify-end gap-2 flex-wrap">
                          <button type="button" onClick={() => abrirEditar(p)} className="min-h-[36px] px-2 py-1.5 text-sm text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded font-medium touch-manipulation">Editar</button>
                          {p.activo !== false ? (
                            puedeDesactivar && <button type="button" onClick={() => abrirModalDesactivar(p)} className="min-h-[36px] px-2 py-1.5 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation">Desactivar</button>
                          ) : (
                            puedeDesactivar && <button type="button" onClick={() => reactivar(p)} className="min-h-[36px] px-2 py-1.5 text-sm text-green-600 hover:text-green-700 active:bg-green-50 rounded touch-manipulation">Reactivar</button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPaginas > 1 && (
        <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <p className="text-sm text-slate-600 order-2 sm:order-1">{(pagina - 1) * limit + 1} - {Math.min(pagina * limit, total)} de {total}</p>
          <div className="flex gap-2 order-1 sm:order-2">
            <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 touch-manipulation">Anterior</button>
            <span className="min-h-[44px] px-4 py-2 flex items-center justify-center text-sm text-slate-700 bg-white rounded-lg border border-slate-200">Pág. {pagina} de {totalPaginas}</span>
            <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 touch-manipulation">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={editando ? 'Editar proveedor' : 'Nuevo proveedor'} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }}>
        <form onSubmit={guardar} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
            <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: AutoPartes México SA" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" required minLength={3} />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contacto</label>
            <input type="text" value={form.contacto} onChange={(e) => setForm({ ...form, contacto: e.target.value })} placeholder="Nombre de la persona de contacto" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono</label>
            <input type="text" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} placeholder="10 dígitos" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="ventas@proveedor.com" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Dirección</label>
            <input type="text" value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} placeholder="Dirección del proveedor" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">RFC</label>
            <input type="text" value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value.toUpperCase() })} placeholder="12 o 13 caracteres" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono touch-manipulation" maxLength={13} />
          </div>
          <label className="flex items-center gap-2 cursor-pointer min-h-[44px] touch-manipulation">
            <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="rounded border-slate-300 w-5 h-5" />
            <span className="text-sm text-slate-700">Proveedor activo</span>
          </label>
          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">
              {enviando ? 'Guardando...' : editando ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Desactivar proveedor" abierto={modalDesactivar} onCerrar={() => { setModalDesactivar(false); setProveedorADesactivar(null) }}>
        {proveedorADesactivar && (
          <div className="space-y-4">
            <p className="text-slate-600">¿Desactivar al proveedor <strong>{proveedorADesactivar.nombre}</strong>? No se eliminará, solo se marcará como inactivo.</p>
            <div className="flex flex-wrap justify-end gap-2">
              <button type="button" onClick={() => { setModalDesactivar(false); setProveedorADesactivar(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
              <button type="button" onClick={confirmarDesactivar} disabled={enviandoDesactivar} className="min-h-[44px] px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 active:bg-red-800 disabled:opacity-50 touch-manipulation">
                {enviandoDesactivar ? 'Desactivando...' : 'Desactivar'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
