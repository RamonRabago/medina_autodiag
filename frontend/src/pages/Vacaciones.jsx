import { useState, useEffect } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { parseFechaLocal, fechaAStr, hoyStr } from '../utils/fechas'

const TIPOS_MOV = [
  { value: 'TOMA', label: 'Toma de vacaciones', desc: 'Reduce el saldo' },
  { value: 'ACREDITACION', label: 'Acreditación anual', desc: 'Aumenta el saldo' },
  { value: 'AJUSTE', label: 'Ajuste manual', desc: 'Corrección (+ o -)' },
]

export default function Vacaciones() {
  const { user } = useAuth()
  const [usuarios, setUsuarios] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalMov, setModalMov] = useState(false)
  const [tipoMov, setTipoMov] = useState(null)
  const [usuarioSel, setUsuarioSel] = useState(null)
  const [form, setForm] = useState({
    dias: '',
    fecha_inicio: '',
    fecha_fin: '',
    periodo: '',
    observaciones: '',
  })
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [filtroUsuario, setFiltroUsuario] = useState('')

  const puedeEditar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  const cargar = () => {
    setLoading(true)
    Promise.all([
      api.get('/usuarios/'),
      api.get('/vacaciones/movimientos'),
    ])
      .then(([rUsers, rMov]) => {
        setError('')
        setUsuarios(Array.isArray(rUsers?.data) ? rUsers.data.filter((u) => u.activo !== false) : [])
        setMovimientos(Array.isArray(rMov?.data) ? rMov.data : [])
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Error al cargar datos')
        setUsuarios([])
        setMovimientos([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [])

  useEffect(() => {
    if (filtroUsuario && !usuarios.some((u) => String(u.id_usuario) === filtroUsuario)) {
      setFiltroUsuario('')
    }
  }, [filtroUsuario, usuarios])

  const abrirModal = (tipo, usuario) => {
    setTipoMov(tipo)
    setUsuarioSel(usuario)
    const hoy = hoyStr()
    setForm({
      dias: '',
      fecha_inicio: hoy,
      fecha_fin: hoy,
      periodo: tipo === 'ACREDITACION' ? new Date().getFullYear().toString() : '',
      observaciones: '',
    })
    setError('')
    setModalMov(true)
  }

  const generarFechasRango = (inicio, fin) => {
    const fechas = []
    const d = parseFechaLocal(inicio)
    const f = parseFechaLocal(fin)
    if (isNaN(d.getTime()) || isNaN(f.getTime()) || d > f) return []
    const actual = new Date(d)
    while (actual <= f) {
      fechas.push(fechaAStr(actual))
      actual.setDate(actual.getDate() + 1)
    }
    return fechas
  }

  const guardarMovimiento = async () => {
    if (!usuarioSel) return

    if (tipoMov === 'TOMA') {
      if (!form.fecha_inicio || !form.fecha_fin) {
        setError('Selecciona fecha inicio y fin')
        return
      }
      const fechas = generarFechasRango(form.fecha_inicio, form.fecha_fin)
      if (fechas.length === 0) {
        setError('La fecha fin debe ser mayor o igual a la fecha inicio')
        return
      }
      const saldo = usuarioSel.dias_vacaciones_saldo ?? 0
      if (fechas.length > saldo) {
        setError(`Saldo insuficiente: tiene ${saldo}, solicita ${fechas.length} días`)
        return
      }
      setEnviando(true)
      setError('')
      try {
        await api.post('/vacaciones/tomar-agendado', {
          id_usuario: usuarioSel.id_usuario,
          fechas,
          observaciones: form.observaciones?.trim() || null,
        })
        setModalMov(false)
        setTipoMov(null)
        setUsuarioSel(null)
        cargar()
      } catch (err) {
        const d = err.response?.data?.detail
        setError(typeof d === 'string' ? d : 'Error al guardar')
      } finally {
        setEnviando(false)
      }
      return
    }

    const dias = parseFloat(form.dias)
    if (isNaN(dias)) {
      setError('Días es obligatorio')
      return
    }
    if (tipoMov === 'ACREDITACION' && dias <= 0) {
      setError('Días debe ser mayor a 0')
      return
    }
    if (tipoMov === 'AJUSTE' && dias === 0) {
      setError('Días no puede ser 0 en ajuste')
      return
    }
    setEnviando(true)
    setError('')
    try {
      await api.post('/vacaciones/movimientos', {
        id_usuario: usuarioSel.id_usuario,
        fecha: hoyStr(),
        tipo: tipoMov,
        dias: tipoMov === 'AJUSTE' ? dias : Math.abs(dias),
        periodo: form.periodo?.trim() || null,
        observaciones: form.observaciones?.trim() || null,
      })
      setModalMov(false)
      setTipoMov(null)
      setUsuarioSel(null)
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const movimientosFiltrados = filtroUsuario
    ? movimientos.filter((m) => m.id_usuario === parseInt(filtroUsuario))
    : movimientos

  if (!puedeEditar && user?.rol !== 'TECNICO' && user?.rol !== 'EMPLEADO') {
    return (
      <div className="p-4 sm:p-6">
        <p className="text-slate-600">No tienes permiso para ver vacaciones.</p>
      </div>
    )
  }

  const tipoActual = TIPOS_MOV.find((t) => t.value === tipoMov)

  return (
    <div className="p-4 sm:p-6 min-h-0 flex flex-col">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">
        Vacaciones
      </h1>
      {error && !modalMov && (
        <p className="mb-4 text-sm text-red-600">{error}</p>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Saldos por empleado */}
        <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
          <div className="p-4 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-800">Saldo por empleado</h2>
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 uppercase">
                      Empleado
                    </th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-slate-500 uppercase">
                      Saldo
                    </th>
                    {puedeEditar && (
                      <th className="px-3 py-2 text-right text-xs font-medium text-slate-500 uppercase">
                        Acciones
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {usuarios.map((u) => (
                    <tr key={u.id_usuario} className="hover:bg-slate-50">
                      <td className="px-3 py-2 text-sm text-slate-800">{u.nombre}</td>
                      <td className="px-3 py-2 text-sm text-right font-medium text-slate-800">
                        {u.dias_vacaciones_saldo != null ? u.dias_vacaciones_saldo : 0} días
                      </td>
                      {puedeEditar && (
                        <td className="px-3 py-2 text-right">
                          <div className="flex gap-1 justify-end">
                            <button
                              type="button"
                              onClick={() => abrirModal('TOMA', u)}
                              className="px-2 py-1 text-xs bg-amber-100 text-amber-800 rounded hover:bg-amber-200"
                            >
                              Toma
                            </button>
                            <button
                              type="button"
                              onClick={() => abrirModal('ACREDITACION', u)}
                              className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200"
                            >
                              Acreditar
                            </button>
                            <button
                              type="button"
                              onClick={() => abrirModal('AJUSTE', u)}
                              className="px-2 py-1 text-xs bg-slate-100 text-slate-700 rounded hover:bg-slate-200"
                            >
                              Ajuste
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                  {usuarios.length === 0 && (
                    <tr>
                      <td colSpan={puedeEditar ? 3 : 2} className="px-3 py-8 text-center text-slate-500">
                        No hay empleados
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Historial de movimientos */}
        <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden flex flex-col min-h-0">
          <div className="p-4 border-b border-slate-200 flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-800">Movimientos</h2>
            <select
              value={filtroUsuario}
              onChange={(e) => setFiltroUsuario(e.target.value)}
              className="px-2 py-1 text-sm border border-slate-300 rounded"
            >
              <option value="">Todos</option>
              {usuarios.map((u) => (
                <option key={u.id_usuario} value={u.id_usuario}>
                  {u.nombre}
                </option>
              ))}
            </select>
          </div>
          {loading ? (
            <p className="p-8 text-slate-500 text-center">Cargando...</p>
          ) : (
            <div className="overflow-x-auto overflow-y-auto flex-1 min-h-0 max-h-[400px]">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Fecha</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Empleado</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Tipo</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-slate-500">Días</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Obs.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {movimientosFiltrados.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-slate-500">
                        Sin movimientos
                      </td>
                    </tr>
                  ) : (
                    movimientosFiltrados.map((m) => {
                      const u = usuarios.find((x) => x.id_usuario === m.id_usuario)
                      const signo = m.tipo === 'TOMA' ? '-' : '+'
                      return (
                        <tr key={m.id} className="hover:bg-slate-50">
                          <td className="px-3 py-2 text-slate-600">{m.fecha}</td>
                          <td className="px-3 py-2 text-slate-800">{u?.nombre ?? m.id_usuario}</td>
                          <td className="px-3 py-2">
                            <span
                              className={`px-2 py-0.5 rounded text-xs ${
                                m.tipo === 'TOMA'
                                  ? 'bg-amber-100 text-amber-800'
                                  : m.tipo === 'ACREDITACION'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {m.tipo}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right font-mono">
                            {signo}{m.dias}
                          </td>
                          <td className="px-3 py-2 text-slate-500 text-xs max-w-[120px] truncate">
                            {m.observaciones || m.periodo || '—'}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <Modal
        titulo={tipoActual ? `${tipoActual.label} – ${usuarioSel?.nombre}` : 'Movimiento'}
        abierto={modalMov}
        onCerrar={() => {
          setModalMov(false)
          setTipoMov(null)
          setUsuarioSel(null)
        }}
      >
        <div className="space-y-4">
          {tipoActual && (
            <p className="text-sm text-slate-600">{tipoActual.desc}</p>
          )}
          {usuarioSel && (
            <p className="text-sm font-medium">
              Saldo actual: {usuarioSel.dias_vacaciones_saldo ?? 0} días
            </p>
          )}
          {tipoMov === 'TOMA' ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Fecha inicio *</label>
                <input
                  type="date"
                  value={form.fecha_inicio}
                  onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Fecha fin *</label>
                <input
                  type="date"
                  value={form.fecha_fin}
                  onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-lg"
                />
              </div>
              {form.fecha_inicio && form.fecha_fin && (
                <p className="col-span-2 text-sm text-slate-600">
                  Total: {generarFechasRango(form.fecha_inicio, form.fecha_fin).length} días a descontar
                </p>
              )}
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Días {tipoMov === 'AJUSTE' ? '(positivo o negativo)' : '*'}
              </label>
              <input
                type="number"
                step="0.5"
                min={tipoMov === 'AJUSTE' ? undefined : 0}
                value={form.dias}
                onChange={(e) => setForm({ ...form, dias: e.target.value })}
                placeholder={tipoMov === 'AJUSTE' ? 'Ej: 2 o -1' : 'Ej: 5'}
                className="w-full px-4 py-3 border border-slate-300 rounded-lg"
              />
            </div>
          )}
          {(tipoMov === 'ACREDITACION' || tipoMov === 'AJUSTE') && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Período (opcional)</label>
              <input
                type="text"
                value={form.periodo}
                onChange={(e) => setForm({ ...form, periodo: e.target.value })}
                placeholder="Ej: 2025"
                className="w-full px-4 py-3 border border-slate-300 rounded-lg"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <textarea
              value={form.observaciones}
              onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
              rows={2}
              className="w-full px-4 py-3 border border-slate-300 rounded-lg"
              placeholder="Opcional"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setModalMov(false)
                setTipoMov(null)
                setUsuarioSel(null)
              }}
              className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={guardarMovimiento}
              disabled={enviando}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              {enviando ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
