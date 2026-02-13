import { useState, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function UsuarioForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const esEdicion = Boolean(id)
  const [cargando, setCargando] = useState(esEdicion)
  const [form, setForm] = useState({
    nombre: '', email: '', password: '', rol: 'TECNICO', activo: true,
    salario_base: '', periodo_pago: 'MENSUAL', bono_puntualidad: '',
    horas_por_dia: '', dias_por_semana: '', dias_vacaciones_saldo: '',
    horario_inicio: '', horario_fin: '', dias_semana_trabaja: ''
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const esAdmin = user?.rol === 'ADMIN'

  useEffect(() => {
    if (!esAdmin) {
      navigate('/configuracion')
      return
    }
    if (!esEdicion) {
      setCargando(false)
      return
    }
    api.get(`/usuarios/`)
      .then((r) => {
        const list = Array.isArray(r.data) ? r.data : []
        const u = list.find((x) => String(x.id_usuario) === id)
        if (u) {
          setForm({
            nombre: u.nombre || '', email: u.email || '', password: '',
            rol: u.rol || 'TECNICO', activo: u.activo !== false,
            salario_base: u.salario_base != null ? u.salario_base : '',
            periodo_pago: u.periodo_pago || 'MENSUAL',
            bono_puntualidad: u.bono_puntualidad != null ? u.bono_puntualidad : '',
            horas_por_dia: u.horas_por_dia != null ? u.horas_por_dia : '',
            dias_por_semana: u.dias_por_semana != null ? u.dias_por_semana : '',
            dias_vacaciones_saldo: u.dias_vacaciones_saldo != null ? u.dias_vacaciones_saldo : '',
            horario_inicio: u.horario_inicio || '', horario_fin: u.horario_fin || '',
            dias_semana_trabaja: u.dias_semana_trabaja || ''
          })
        }
      })
      .catch(() => setError('No se pudo cargar el usuario'))
      .finally(() => setCargando(false))
  }, [id, esEdicion, esAdmin, navigate])

  const guardar = async (e) => {
    e?.preventDefault()
    setError('')
    if (!form.nombre?.trim()) { setError('El nombre es obligatorio'); return }
    if (!form.email?.trim()) { setError('El email es obligatorio'); return }
    if (!esEdicion && !form.password?.trim()) { setError('La contraseña es obligatoria para nuevo usuario'); return }
    if (esEdicion && form.password?.trim() && form.password.length < 4) { setError('La contraseña debe tener al menos 4 caracteres'); return }

    setEnviando(true)
    try {
      if (esEdicion) {
        const payload = { nombre: form.nombre.trim(), email: form.email.trim(), rol: form.rol, activo: form.activo }
        if (form.password?.trim()) payload.password = form.password
        payload.salario_base = (form.salario_base !== '' && form.salario_base != null) ? parseFloat(form.salario_base) || null : null
        payload.periodo_pago = form.periodo_pago || null
        payload.bono_puntualidad = (form.bono_puntualidad !== '' && form.bono_puntualidad != null) ? parseFloat(form.bono_puntualidad) || null : null
        payload.horas_por_dia = (form.horas_por_dia !== '' && form.horas_por_dia != null) ? parseFloat(form.horas_por_dia) || null : null
        payload.dias_por_semana = (form.dias_por_semana !== '' && form.dias_por_semana != null) ? parseInt(form.dias_por_semana, 10) || null : null
        payload.dias_vacaciones_saldo = (form.dias_vacaciones_saldo !== '' && form.dias_vacaciones_saldo != null) ? parseFloat(form.dias_vacaciones_saldo) || null : null
        payload.horario_inicio = form.horario_inicio?.trim() || null
        payload.horario_fin = form.horario_fin?.trim() || null
        payload.dias_semana_trabaja = form.dias_semana_trabaja?.trim() || null
        await api.put(`/usuarios/${id}`, payload)
      } else {
        const payload = { nombre: form.nombre.trim(), email: form.email.trim(), password: form.password, rol: form.rol, activo: form.activo }
        payload.salario_base = (form.salario_base !== '' && form.salario_base != null) ? parseFloat(form.salario_base) || null : null
        payload.periodo_pago = form.periodo_pago || null
        payload.bono_puntualidad = (form.bono_puntualidad !== '' && form.bono_puntualidad != null) ? parseFloat(form.bono_puntualidad) || null : null
        payload.horas_por_dia = (form.horas_por_dia !== '' && form.horas_por_dia != null) ? parseFloat(form.horas_por_dia) || null : null
        payload.dias_por_semana = (form.dias_por_semana !== '' && form.dias_por_semana != null) ? parseInt(form.dias_por_semana, 10) || null : null
        payload.dias_vacaciones_saldo = (form.dias_vacaciones_saldo !== '' && form.dias_vacaciones_saldo != null) ? parseFloat(form.dias_vacaciones_saldo) || null : null
        payload.horario_inicio = form.horario_inicio?.trim() || null
        payload.horario_fin = form.horario_fin?.trim() || null
        payload.dias_semana_trabaja = form.dias_semana_trabaja?.trim() || null
        await api.post('/usuarios/', payload)
      }
      navigate('/configuracion?tab=usuarios')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  if (!esAdmin) return null
  if (cargando) return <p className="p-8 text-slate-500">Cargando...</p>

  return (
    <div className="min-h-0 flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4 sm:mb-6">
        <Link
          to="/configuracion?tab=usuarios"
          className="inline-flex items-center gap-1 px-3 py-2 min-h-[44px] border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 font-medium text-sm bg-white touch-manipulation w-fit"
        >
          ← Volver a usuarios
        </Link>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">
          {esEdicion ? 'Editar usuario' : 'Nuevo usuario'}
        </h1>
      </div>

      <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden flex-1 min-h-0">
        <form onSubmit={guardar} className="p-4 sm:p-6 max-w-3xl">
          {error && <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

          {/* Datos básicos */}
          <section className="mb-6 sm:mb-8">
            <h2 className="text-base font-semibold text-slate-800 mb-4 pb-2 border-b border-slate-200">Datos del usuario</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">Nombre *</label>
                <input type="text" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej: Juan Pérez" className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email *</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="usuario@taller.com" className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">{esEdicion ? 'Nueva contraseña (vacío = no cambiar)' : 'Contraseña *'}</label>
                <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={esEdicion ? 'Opcional' : 'Mín. 4 caracteres'} className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" minLength={esEdicion ? 0 : 4} />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Rol</label>
                <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })} className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation">
                  <option value="ADMIN">Administrador</option>
                  <option value="CAJA">Caja</option>
                  <option value="TECNICO">Técnico</option>
                  <option value="EMPLEADO">Empleado</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="flex items-center gap-2 cursor-pointer min-h-[44px] touch-manipulation py-2">
                  <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="rounded border-slate-300 w-5 h-5 flex-shrink-0" />
                  <span className="text-sm text-slate-700">Usuario activo</span>
                </label>
              </div>
            </div>
          </section>

          {/* Nómina */}
          <section className="mb-6 sm:mb-8">
            <h2 className="text-base font-semibold text-slate-800 mb-4 pb-2 border-b border-slate-200">Nómina</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Salario base</label>
                <input type="number" step="0.01" min="0" value={form.salario_base} onChange={(e) => setForm({ ...form, salario_base: e.target.value })} placeholder="0.00" className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Bono puntualidad</label>
                <input type="number" step="0.01" min="0" value={form.bono_puntualidad} onChange={(e) => setForm({ ...form, bono_puntualidad: e.target.value })} placeholder="0.00" className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Periodo de pago</label>
                <select value={form.periodo_pago} onChange={(e) => setForm({ ...form, periodo_pago: e.target.value })} className="w-full px-4 py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation">
                  <option value="MENSUAL">Mensual</option>
                  <option value="QUINCENAL">Quincenal</option>
                  <option value="SEMANAL">Semanal</option>
                </select>
              </div>
            </div>
          </section>

          {/* Checador / Asistencia */}
          <section className="mb-6 sm:mb-8">
            <h2 className="text-base font-semibold text-slate-800 mb-4 pb-2 border-b border-slate-200">Checador / Asistencia</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Horas/día</label>
                  <input type="number" step="0.5" min="0" max="24" value={form.horas_por_dia} onChange={(e) => setForm({ ...form, horas_por_dia: e.target.value })} placeholder="8" className="w-full px-3 py-2.5 sm:py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Días/sem.</label>
                  <input type="number" min="1" max="7" value={form.dias_por_semana} onChange={(e) => setForm({ ...form, dias_por_semana: e.target.value })} placeholder="5" className="w-full px-3 py-2.5 sm:py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Vacaciones</label>
                  <input type="number" step="0.5" min="0" value={form.dias_vacaciones_saldo} onChange={(e) => setForm({ ...form, dias_vacaciones_saldo: e.target.value })} placeholder="0" className="w-full px-3 py-2.5 sm:py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Entrada</label>
                  <input type="time" value={form.horario_inicio || ''} onChange={(e) => setForm({ ...form, horario_inicio: e.target.value })} className="w-full px-3 py-2.5 sm:py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Salida</label>
                  <input type="time" value={form.horario_fin || ''} onChange={(e) => setForm({ ...form, horario_fin: e.target.value })} className="w-full px-3 py-2.5 sm:py-3 min-h-[44px] sm:min-h-[40px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base touch-manipulation" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Días que trabaja</label>
                <div className="flex flex-wrap gap-2 sm:gap-3">
                  {[
                    { n: 1, label: 'Lun' },
                    { n: 2, label: 'Mar' },
                    { n: 3, label: 'Mié' },
                    { n: 4, label: 'Jue' },
                    { n: 5, label: 'Vie' },
                    { n: 6, label: 'Sáb' },
                    { n: 7, label: 'Dom' }
                  ].map(({ n, label }) => {
                    const vals = (form.dias_semana_trabaja || '').split(',').map((x) => x.trim()).filter(Boolean)
                    const checked = vals.includes(String(n))
                    return (
                      <label key={n} className={`flex items-center justify-center min-w-[44px] min-h-[44px] px-3 py-2 rounded-lg border cursor-pointer touch-manipulation transition-colors ${checked ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-slate-300 bg-white hover:bg-slate-50 text-slate-600'}`}>
                        <input type="checkbox" checked={checked} onChange={(e) => {
                          const next = e.target.checked ? [...vals.filter((v) => v !== String(n)), String(n)].sort((a, b) => Number(a) - Number(b)) : vals.filter((v) => v !== String(n))
                          setForm({ ...form, dias_semana_trabaja: next.join(',') })
                        }} className="sr-only" />
                        <span className="text-sm font-medium">{label}</span>
                      </label>
                    )
                  })}
                </div>
              </div>
            </div>
          </section>

          <div className="flex flex-col-reverse sm:flex-row gap-2 pt-4 border-t border-slate-200">
            <Link to="/configuracion?tab=usuarios" className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 inline-flex items-center justify-center touch-manipulation">
              Cancelar
            </Link>
            <button type="submit" disabled={enviando} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 touch-manipulation">
              {enviando ? 'Guardando...' : esEdicion ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
