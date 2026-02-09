import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Citas() {
  const { user } = useAuth()
  const [citas, setCitas] = useState([])
  const [loading, setLoading] = useState(true)
  const [clientes, setClientes] = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [modalAbierto, setModalAbierto] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({
    id_cliente: '',
    id_vehiculo: '',
    fecha: '',
    hora: '',
    tipo: 'REVISION',
    motivo: '',
    notas: '',
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [filtros, setFiltros] = useState({
    id_cliente: '',
    estado: '',
    fecha_desde: '',
    fecha_hasta: '',
  })
  const [pagina, setPagina] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [modalDetalle, setModalDetalle] = useState(false)
  const [citaDetalle, setCitaDetalle] = useState(null)
  const [modalCancelar, setModalCancelar] = useState(false)
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const limit = 20

  const [tipos, setTipos] = useState([
    { valor: 'REVISION', nombre: 'Revisión' },
    { valor: 'MANTENIMIENTO', nombre: 'Mantenimiento' },
    { valor: 'REPARACION', nombre: 'Reparación' },
    { valor: 'DIAGNOSTICO', nombre: 'Diagnóstico' },
    { valor: 'OTRO', nombre: 'Otro' },
  ])
  const [estados, setEstados] = useState([
    { valor: 'CONFIRMADA', nombre: 'Confirmada' },
    { valor: 'SI_ASISTIO', nombre: 'Sí asistió' },
    { valor: 'NO_ASISTIO', nombre: 'No asistió' },
    { valor: 'CANCELADA', nombre: 'Cancelada' },
  ])

  useEffect(() => {
    Promise.allSettled([
      api.get('/citas/catalogos/tipos'),
      api.get('/citas/catalogos/estados'),
    ]).then(([rTipos, rEstados]) => {
      if (rTipos.status === 'fulfilled' && rTipos.value?.data?.tipos?.length) {
        setTipos(rTipos.value.data.tipos.map((t) => ({ valor: t.valor, nombre: t.nombre || t.valor })))
      }
      if (rEstados.status === 'fulfilled' && rEstados.value?.data?.estados?.length) {
        setEstados(rEstados.value.data.estados.map((e) => ({ valor: e.valor, nombre: e.nombre || e.valor })))
      }
    })
  }, [])

  const cargar = () => {
    const params = { skip: (pagina - 1) * limit, limit }
    if (filtros.id_cliente) params.id_cliente = parseInt(filtros.id_cliente)
    if (filtros.estado) params.estado = filtros.estado
    if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
    if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
    api
      .get('/citas/', { params })
      .then((res) => {
        const d = res.data
        setCitas(d.citas || [])
        setTotal(d.total ?? 0)
        setTotalPaginas(d.total_paginas ?? 1)
      })
      .catch(() => setCitas([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    cargar()
  }, [pagina, filtros.id_cliente, filtros.estado, filtros.fecha_desde, filtros.fecha_hasta])

  useEffect(() => {
    api.get('/clientes/', { params: { limit: 500 } }).then((r) => {
      const d = r.data
      setClientes(d?.clientes ?? [])
    }).catch(() => setClientes([]))
  }, [])

  useEffect(() => {
    if (form.id_cliente && modalAbierto) {
      api.get(`/vehiculos/cliente/${form.id_cliente}`).then((r) => {
        setVehiculos(Array.isArray(r.data) ? r.data : [])
      }).catch(() => setVehiculos([]))
    } else {
      setVehiculos([])
    }
  }, [form.id_cliente, modalAbierto])

  const abrirNuevo = () => {
    setEditando(null)
    const hoy = new Date()
    const fecha = hoy.toISOString().slice(0, 10)
    const hora = `${String(hoy.getHours()).padStart(2, '0')}:${String(hoy.getMinutes()).padStart(2, '0')}`
    setForm({
      id_cliente: '',
      id_vehiculo: '',
      fecha,
      hora,
      tipo: 'REVISION',
      motivo: '',
      notas: '',
    })
    setError('')
    setModalAbierto(true)
  }

  const abrirEditar = async (c) => {
    setEditando(c)
    setError('')
    setModalAbierto(true)
    const parsearFechaHora = (fh) => {
      if (!fh) return { fecha: '', hora: '' }
      const d = new Date(fh)
      return {
        fecha: d.toISOString().slice(0, 10),
        hora: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
      }
    }
    try {
      const res = await api.get(`/citas/${c.id_cita}`)
      const d = res.data
      const { fecha, hora } = parsearFechaHora(d.fecha_hora)
      setForm({
        id_cliente: d.id_cliente,
        id_vehiculo: d.id_vehiculo || '',
        fecha,
        hora,
        tipo: d.tipo || 'REVISION',
        motivo: d.motivo || '',
        notas: d.notas || '',
      })
    } catch {
      const { fecha, hora } = parsearFechaHora(c.fecha_hora)
      setForm({
        id_cliente: c.id_cliente,
        id_vehiculo: c.id_vehiculo || '',
        fecha,
        hora,
        tipo: c.tipo || 'REVISION',
        motivo: c.motivo || '',
        notas: '',
      })
    }
  }

  const abrirDetalle = async (idCita) => {
    try {
      const res = await api.get(`/citas/${idCita}`)
      setCitaDetalle(res.data)
      setModalDetalle(true)
    } catch {
      setCitaDetalle(null)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.id_cliente || !form.fecha || !form.hora) {
      setError('Cliente, fecha y hora son obligatorios')
      return
    }
    const fecha_hora = `${form.fecha}T${form.hora}:00`
    const ahora = new Date()
    const fechaCita = new Date(form.fecha + 'T' + form.hora + ':00')
    if (fechaCita <= ahora) {
      setError('La fecha y hora deben ser posteriores al momento actual')
      return
    }
    setEnviando(true)
    try {
      if (editando) {
        await api.put(`/citas/${editando.id_cita}`, {
          id_vehiculo: form.id_vehiculo ? parseInt(form.id_vehiculo) : null,
          fecha_hora,
          tipo: form.tipo,
          motivo: form.motivo?.trim() || null,
          notas: form.notas?.trim() || null,
        })
      } else {
        await api.post('/citas/', {
          id_cliente: parseInt(form.id_cliente),
          id_vehiculo: form.id_vehiculo ? parseInt(form.id_vehiculo) : null,
          fecha_hora,
          tipo: form.tipo,
          motivo: form.motivo?.trim() || null,
          notas: form.notas?.trim() || null,
        })
      }
      cargar()
      setModalAbierto(false)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg.map((m) => m?.msg ?? m).join(', ') : (typeof msg === 'string' ? msg : 'Error al guardar'))
    } finally {
      setEnviando(false)
    }
  }

  const cambiarEstado = async (idCita, nuevoEstado, motivoCancelacionParam) => {
    try {
      const payload = { estado: nuevoEstado }
      if (nuevoEstado === 'CANCELADA' && motivoCancelacionParam?.trim()) {
        payload.motivo_cancelacion = motivoCancelacionParam.trim()
      }
      await api.put(`/citas/${idCita}`, payload)
      cargar()
      if (citaDetalle?.id_cita === idCita) {
        const res = await api.get(`/citas/${idCita}`)
        setCitaDetalle(res.data)
      }
      setModalCancelar(false)
      setMotivoCancelacion('')
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al cambiar estado')
    }
  }

  const abrirModalCancelar = () => {
    setMotivoCancelacion('')
    setModalCancelar(true)
  }

  const confirmarCancelar = () => {
    if (!motivoCancelacion?.trim()) {
      alert('Indica el motivo de la cancelación')
      return
    }
    cambiarEstado(citaDetalle?.id_cita, 'CANCELADA', motivoCancelacion)
  }

  const eliminar = async (idCita) => {
    if (!confirm('¿Eliminar esta cita?')) return
    try {
      await api.delete(`/citas/${idCita}`)
      cargar()
      setModalDetalle(false)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar')
    }
  }

  const getEstadoBadge = (estado) => {
    const colors = {
      CONFIRMADA: 'bg-blue-100 text-blue-800',
      SI_ASISTIO: 'bg-green-100 text-green-800',
      NO_ASISTIO: 'bg-red-100 text-red-800',
      CANCELADA: 'bg-slate-200 text-slate-700',
    }
    return colors[estado] || 'bg-slate-100 text-slate-700'
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Citas</h1>
        <button onClick={abrirNuevo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">
          Nueva cita
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Cliente</label>
            <select
              value={filtros.id_cliente}
              onChange={(e) => { setFiltros((f) => ({ ...f, id_cliente: e.target.value })); setPagina(1) }}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]"
            >
              <option value="">Todos</option>
              {clientes.map((c) => (
                <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Estado</label>
            <select
              value={filtros.estado}
              onChange={(e) => { setFiltros((f) => ({ ...f, estado: e.target.value })); setPagina(1) }}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            >
              <option value="">Todos</option>
              {estados.map((e) => (
                <option key={e.valor} value={e.valor}>{e.nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Desde</label>
            <input
              type="date"
              value={filtros.fecha_desde}
              onChange={(e) => { setFiltros((f) => ({ ...f, fecha_desde: e.target.value })); setPagina(1) }}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Hasta</label>
            <input
              type="date"
              value={filtros.fecha_hasta}
              onChange={(e) => { setFiltros((f) => ({ ...f, fecha_hasta: e.target.value })); setPagina(1) }}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Cliente</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Vehículo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Tipo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Estado</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Motivo</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {citas.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  No hay citas. Usa los filtros o crea una nueva cita.
                </td>
              </tr>
            ) : (
              citas.map((c) => (
                <tr key={c.id_cita} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-700">
                    {c.fecha_hora ? new Date(c.fecha_hora).toLocaleString('es-MX') : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-800">{c.cliente_nombre || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{c.vehiculo_info || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600">{c.tipo || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getEstadoBadge(c.estado)}`}>
                      {c.estado || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 max-w-[200px]" title={c.estado === 'CANCELADA' && c.motivo_cancelacion ? c.motivo_cancelacion : undefined}>
                    {c.estado === 'CANCELADA' && c.motivo_cancelacion ? (
                      <span className="truncate block" title={c.motivo_cancelacion}>Cancelada: {c.motivo_cancelacion}</span>
                    ) : (
                      (c.motivo || '-')
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                        <button onClick={() => abrirDetalle(c.id_cita)} className="text-sm text-primary-600 hover:text-primary-700 mr-2">Ver</button>
                        <button onClick={() => abrirEditar(c)} className="text-sm text-slate-600 hover:text-slate-800 mr-2">Editar</button>
                        <button onClick={() => eliminar(c.id_cita)} className="text-sm text-red-600 hover:text-red-700">Eliminar</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPaginas > 1 && (
        <div className="mt-4 flex justify-between items-center">
          <p className="text-sm text-slate-600">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, total)} de {total}</p>
          <div className="flex gap-2">
            <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Anterior</button>
            <span className="px-3 py-1 text-sm text-slate-700">Página {pagina} de {totalPaginas}</span>
            <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Siguiente</button>
          </div>
        </div>
      )}

      <Modal titulo={editando ? 'Editar cita' : 'Nueva cita'} abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cliente <span className="text-red-500">*</span></label>
            <select
              value={form.id_cliente}
              onChange={(e) => setForm((f) => ({ ...f, id_cliente: e.target.value, id_vehiculo: '' }))}
              required
              disabled={!!editando}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            >
              <option value="">— Seleccionar —</option>
              {clientes.map((c) => (
                <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>
              ))}
            </select>
          </div>
          {form.id_cliente && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Vehículo (opcional)</label>
              <select
                value={form.id_vehiculo}
                onChange={(e) => setForm((f) => ({ ...f, id_vehiculo: e.target.value }))}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg"
              >
                <option value="">— Sin vehículo —</option>
                {vehiculos.map((v) => (
                  <option key={v.id_vehiculo} value={v.id_vehiculo}>{v.marca} {v.modelo} {v.anio}</option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fecha <span className="text-red-500">*</span></label>
              <input
                type="date"
                value={form.fecha}
                onChange={(e) => setForm((f) => ({ ...f, fecha: e.target.value }))}
                required
                min={(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; })()}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Hora <span className="text-red-500">*</span></label>
              <input
                type="time"
                list="horas-sugeridas"
                value={form.hora}
                onChange={(e) => setForm((f) => ({ ...f, hora: e.target.value }))}
                required
                step="60"
                min={form.fecha === (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; })() ? (() => { const d = new Date(); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; })() : undefined}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg"
              />
              <datalist id="horas-sugeridas">
                {[8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18].flatMap((h) => [
                  `${String(h).padStart(2, '0')}:00`,
                  `${String(h).padStart(2, '0')}:30`,
                ]).map((t) => (
                  <option key={t} value={t} />
                ))}
              </datalist>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
            <select value={form.tipo} onChange={(e) => setForm((f) => ({ ...f, tipo: e.target.value }))} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              {tipos.map((t) => (
                <option key={t.valor} value={t.valor}>{t.nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motivo</label>
            <input
              type="text"
              value={form.motivo}
              onChange={(e) => setForm((f) => ({ ...f, motivo: e.target.value }))}
              placeholder="Ej: Revisión de frenos, cambio de aceite..."
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notas</label>
            <textarea
              value={form.notas}
              onChange={(e) => setForm((f) => ({ ...f, notas: e.target.value }))}
              rows={2}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Detalle de cita" abierto={modalDetalle} onCerrar={() => { setModalDetalle(false); setCitaDetalle(null) }}>
        {citaDetalle ? (
          <div className="space-y-4">
            <p><strong>Cliente:</strong> {citaDetalle.cliente_nombre || '-'}</p>
            <p><strong>Vehículo:</strong> {citaDetalle.vehiculo_info || '-'}</p>
            <p><strong>Fecha:</strong> {citaDetalle.fecha_hora ? new Date(citaDetalle.fecha_hora).toLocaleString('es-MX') : '-'}</p>
            <p><strong>Tipo:</strong> {citaDetalle.tipo || '-'}</p>
            <p><strong>Estado:</strong> <span className={`px-2 py-1 rounded text-sm font-medium ${getEstadoBadge(citaDetalle.estado)}`}>{citaDetalle.estado || '-'}</span></p>
            <p><strong>Motivo:</strong> {citaDetalle.motivo || '-'}</p>
            {citaDetalle.estado === 'CANCELADA' && citaDetalle.motivo_cancelacion && (
              <p><strong>Motivo cancelación:</strong> <span className="text-slate-700">{citaDetalle.motivo_cancelacion}</span></p>
            )}
            {citaDetalle.notas && <p><strong>Notas:</strong> {citaDetalle.notas}</p>}
            {citaDetalle.orden_vinculada && <p><strong>Orden vinculada:</strong> {citaDetalle.orden_vinculada.numero_orden} ({citaDetalle.orden_vinculada.estado})</p>}
            <div className="flex flex-wrap gap-2 pt-4 border-t">
              {citaDetalle.estado === 'CONFIRMADA' && (
                <>
                  <button onClick={() => cambiarEstado(citaDetalle.id_cita, 'SI_ASISTIO')} className="px-3 py-1 bg-green-600 text-white rounded text-sm">Sí asistió</button>
                  <button onClick={() => cambiarEstado(citaDetalle.id_cita, 'NO_ASISTIO')} className="px-3 py-1 bg-amber-600 text-white rounded text-sm">No asistió</button>
                  <button onClick={abrirModalCancelar} className="px-3 py-1 bg-slate-500 text-white rounded text-sm">Cancelar cita</button>
                </>
              )}
              <button onClick={() => { setModalDetalle(false); abrirEditar(citaDetalle) }} className="px-3 py-1 border border-slate-300 rounded text-sm">Editar</button>
              <button onClick={() => eliminar(citaDetalle.id_cita)} className="px-3 py-1 bg-red-600 text-white rounded text-sm">Eliminar</button>
            </div>
          </div>
        ) : (
          <p className="text-slate-500">Cargando...</p>
        )}
      </Modal>

      <Modal titulo="Cancelar cita" abierto={modalCancelar} onCerrar={() => { setModalCancelar(false); setMotivoCancelacion('') }}>
        <p className="text-slate-600 mb-3">El cliente avisó que no podrá asistir. Indica el motivo de la cancelación:</p>
        <textarea
          value={motivoCancelacion}
          onChange={(e) => setMotivoCancelacion(e.target.value)}
          placeholder="Ej: reprogramó para otra fecha, emergencia familiar..."
          rows={3}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
        />
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={() => { setModalCancelar(false); setMotivoCancelacion('') }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700">No cancelar</button>
          <button onClick={confirmarCancelar} disabled={!motivoCancelacion?.trim()} className="px-4 py-2 bg-slate-500 text-white rounded-lg disabled:opacity-50">Confirmar cancelación</button>
        </div>
      </Modal>
    </div>
  )
}
