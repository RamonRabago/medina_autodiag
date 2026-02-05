import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

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
      alert(err.response?.data?.detail || 'Error al desactivar')
    } finally {
      setEnviandoDesactivar(false)
    }
  }

  const reactivar = async (p) => {
    try {
      await api.post(`/proveedores/${p.id_proveedor}/reactivar`)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al reactivar')
    }
  }

  if (loading && proveedores.length === 0) return <p className="text-slate-500 p-8">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Proveedores</h1>
        {puedeEditar && (
          <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">
            + Nuevo proveedor
          </button>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Buscar por nombre, teléfono o email..."
          value={buscar}
          onChange={(e) => { setBuscar(e.target.value); setPagina(1) }}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm flex-1 min-w-[200px]"
        />
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={mostrarInactivos}
            onChange={(e) => { setMostrarInactivos(e.target.checked); setPagina(1) }}
            className="rounded border-slate-300"
          />
          Mostrar inactivos
        </label>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nombre</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Contacto</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Teléfono</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Estado</th>
              {puedeEditar && (
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {proveedores.length === 0 ? (
              <tr><td colSpan={puedeEditar ? 7 : 6} className="px-4 py-8 text-center text-slate-500">No hay proveedores</td></tr>
            ) : (
              proveedores.map((p) => (
                <tr key={p.id_proveedor} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-600">{p.id_proveedor}</td>
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">{p.nombre}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.contacto || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.telefono || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{p.email || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${p.activo !== false ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                      {p.activo !== false ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  {puedeEditar && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <button onClick={() => abrirEditar(p)} className="text-sm text-primary-600 hover:text-primary-700 font-medium">Editar</button>
                        {p.activo !== false ? (
                          puedeDesactivar && <button onClick={() => abrirModalDesactivar(p)} className="text-sm text-red-600 hover:text-red-700">Desactivar</button>
                        ) : (
                          puedeDesactivar && <button onClick={() => reactivar(p)} className="text-sm text-green-600 hover:text-green-700">Reactivar</button>
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

      {totalPaginas > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-slate-600">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, total)} de {total}</p>
          <div className="flex gap-2">
            <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Anterior</button>
            <span className="px-3 py-1 text-sm text-slate-700">Página {pagina} de {totalPaginas}</span>
            <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={editando ? 'Editar proveedor' : 'Nuevo proveedor'} abierto={modalAbierto} onCerrar={() => { setModalAbierto(false); setEditando(null) }}>
        <form onSubmit={guardar} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
            <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: AutoPartes México SA" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" required minLength={3} />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contacto</label>
            <input type="text" value={form.contacto} onChange={(e) => setForm({ ...form, contacto: e.target.value })} placeholder="Nombre de la persona de contacto" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Teléfono</label>
            <input type="text" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} placeholder="10 dígitos" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="ventas@proveedor.com" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Dirección</label>
            <input type="text" value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} placeholder="Dirección del proveedor" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">RFC</label>
            <input type="text" value={form.rfc} onChange={(e) => setForm({ ...form, rfc: e.target.value.toUpperCase() })} placeholder="12 o 13 caracteres" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono" maxLength={13} />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="rounded border-slate-300" />
            <span className="text-sm text-slate-700">Proveedor activo</span>
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalAbierto(false); setEditando(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
              {enviando ? 'Guardando...' : editando ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Desactivar proveedor" abierto={modalDesactivar} onCerrar={() => { setModalDesactivar(false); setProveedorADesactivar(null) }}>
        {proveedorADesactivar && (
          <div className="space-y-4">
            <p className="text-slate-600">
              ¿Desactivar al proveedor <strong>{proveedorADesactivar.nombre}</strong>? No se eliminará, solo se marcará como inactivo.
            </p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setModalDesactivar(false); setProveedorADesactivar(null) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">Cancelar</button>
              <button type="button" onClick={confirmarDesactivar} disabled={enviandoDesactivar} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50">
                {enviandoDesactivar ? 'Desactivando...' : 'Desactivar'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
