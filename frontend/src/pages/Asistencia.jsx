import { useState, useEffect, useMemo } from 'react'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

const TIPOS_ASISTENCIA = [
  { value: 'TRABAJO', label: 'Trabajo' },
  { value: 'FESTIVO', label: 'Festivo' },
  { value: 'VACACION', label: 'Vacación' },
  { value: 'PERMISO_CON_GOCE', label: 'Permiso c/goce' },
  { value: 'PERMISO_SIN_GOCE', label: 'Permiso s/goce' },
  { value: 'INCAPACIDAD', label: 'Incapacidad' },
  { value: 'FALTA', label: 'Falta' },
]

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function getLunesSemana(d) {
  const dt = new Date(d)
  const day = dt.getDay()
  const diff = dt.getDate() - (day === 0 ? 7 : day) + 1
  return new Date(dt.getFullYear(), dt.getMonth(), diff)
}

function fechaAStr(d) {
  return d.toISOString().slice(0, 10)
}

function diasDeSemana(lunes) {
  const dias = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(lunes)
    d.setDate(lunes.getDate() + i)
    dias.push(d)
  }
  return dias
}

/** Genera array de fechas desde inicio hasta fin (máx 31 días). */
function diasEnRango(inicio, fin) {
  const dias = []
  const d = new Date(inicio)
  const f = new Date(fin)
  if (d > f) return dias
  const maxDias = 31
  let count = 0
  while (d <= f && count < maxDias) {
    dias.push(new Date(d))
    d.setDate(d.getDate() + 1)
    count++
  }
  return dias
}

/** Retorna día ISO: Lun=1..Dom=7 (según dias_semana_trabaja) */
function getDiaIso(d) {
  return d.getDay() === 0 ? 7 : d.getDay()
}

/** true si el empleado trabaja ese día según dias_semana_trabaja (1=lun..7=dom) */
function trabajaEseDia(usuario, d) {
  const str = usuario?.dias_semana_trabaja
  if (!str || !str.trim()) return true
  const dias = str.split(',').map((x) => parseInt(x.trim(), 10)).filter((n) => !isNaN(n))
  if (dias.length === 0) return true
  const diaIso = getDiaIso(d)
  return dias.includes(diaIso)
}

export default function Asistencia() {
  const { user } = useAuth()
  const hoy = new Date()
  const lunesInicial = getLunesSemana(hoy)
  const domingoInicial = new Date(lunesInicial)
  domingoInicial.setDate(lunesInicial.getDate() + 6)
  const [fechaInicio, setFechaInicio] = useState(fechaAStr(lunesInicial))
  const [fechaFin, setFechaFin] = useState(fechaAStr(domingoInicial))
  const [usuarios, setUsuarios] = useState([])
  const [asistencia, setAsistencia] = useState([])
  const [festivos, setFestivos] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalDetalle, setModalDetalle] = useState(false)
  const [celdaEditando, setCeldaEditando] = useState(null)
  const [formDetalle, setFormDetalle] = useState({
    tipo: 'TRABAJO',
    horas_trabajadas: '',
    turno_completo: true,
    aplica_bono_puntualidad: true,
    observaciones: '',
  })
  const [enviando, setEnviando] = useState(false)
  const [prellenando, setPrellenando] = useState(false)
  const [exportando, setExportando] = useState(false)
  const [error, setError] = useState('')
  const [incluirRegistroManual, setIncluirRegistroManual] = useState(false)

  const puedeEditar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'
  const [desdeRango, hastaRango] = fechaInicio <= fechaFin ? [fechaInicio, fechaFin] : [fechaFin, fechaInicio]
  const dias = diasEnRango(desdeRango, hastaRango)
  const usuariosVisibles = usuarios.filter((u) => incluirRegistroManual || u.checa_entrada_salida !== false)

  const cargar = () => {
    setLoading(true)
    const params = { fecha_inicio: desdeRango, fecha_fin: hastaRango }
    const anios = []
    const y1 = new Date(fechaInicio).getFullYear()
    const y2 = new Date(fechaFin).getFullYear()
    for (let y = y1; y <= y2; y++) anios.push(y)
    Promise.all([
      api.get('/usuarios/').catch(() => ({ data: [] })),
      api.get('/asistencia/', { params }).catch(() => ({ data: [] })),
      ...anios.map((a) => api.get('/festivos/', { params: { anio: a } }).catch(() => ({ data: [] }))),
    ])
      .then(([rUsers, rAsistencia, ...rFestivos]) => {
        const list = Array.isArray(rUsers.data) ? rUsers.data : []
        setUsuarios(list.filter((u) => u.activo !== false))
        setAsistencia(Array.isArray(rAsistencia.data) ? rAsistencia.data : [])
        const festivosList = (rFestivos || []).flatMap((r) => Array.isArray(r.data) ? r.data : [])
        setFestivos(festivosList)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [fechaInicio, fechaFin])

  const esFestivo = (fechaStr) => festivos.some((f) => f.fecha === fechaStr)

  const exportarExcel = async () => {
    setExportando(true)
    try {
      const desde = dias.length > 0 ? fechaAStr(dias[0]) : fechaInicio
      const hasta = dias.length > 0 ? fechaAStr(dias[dias.length - 1]) : fechaFin
      const params = { fecha_desde: desde, fecha_hasta: hasta }
      const res = await api.get('/exportaciones/asistencia', { params, responseType: 'blob' })
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `asistencia_${desde}_${hasta}.xlsx`
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fn)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    } finally {
      setExportando(false)
    }
  }

  const prellenarFestivos = async () => {
    setPrellenando(true)
    setError('')
    try {
      const res = await api.post('/asistencia/prellenar-festivos', null, {
        params: { fecha_inicio: fechaInicio, fecha_fin: fechaFin },
      })
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : 'Error al prellenar')
    } finally {
      setPrellenando(false)
    }
  }

  const getAsistenciaCelda = (idUsuario, fechaStr) =>
    asistencia.find((a) => a.id_usuario === idUsuario && a.fecha === fechaStr)

  const rangoIni = dias.length > 0 ? fechaAStr(dias[0]) : desdeRango
  const rangoFin = dias.length > 0 ? fechaAStr(dias[dias.length - 1]) : hastaRango

  const resumenSemana = useMemo(() => {
    const porEmpleado = {}
    const horasPorDiaDefault = 8
    for (const u of usuariosVisibles) {
      porEmpleado[u.id_usuario] = {
        nombre: u.nombre,
        trabajo: 0,
        falta: 0,
        vacacion: 0,
        permisoConGoce: 0,
        permisoSinGoce: 0,
        incapacidad: 0,
        festivo: 0,
        horas: 0,
      }
    }
    const idsVisibles = new Set(usuariosVisibles.map((x) => x.id_usuario))
    for (const r of asistencia) {
      if (r.fecha < rangoIni || r.fecha > rangoFin || !idsVisibles.has(r.id_usuario)) continue
      const u = usuarios.find((x) => x.id_usuario === r.id_usuario)
      if (!u) continue
      if (!porEmpleado[r.id_usuario]) porEmpleado[r.id_usuario] = { nombre: u.nombre, trabajo: 0, falta: 0, vacacion: 0, permisoConGoce: 0, permisoSinGoce: 0, incapacidad: 0, festivo: 0, horas: 0 }
      const tipo = typeof r.tipo === 'string' ? r.tipo : r.tipo?.value || ''
      const horasPorDia = u?.horas_por_dia != null ? Number(u.horas_por_dia) : horasPorDiaDefault
      if (tipo === 'TRABAJO') {
        const hrs = r.turno_completo ? horasPorDia : (Number(r.horas_trabajadas) || 0)
        porEmpleado[r.id_usuario].trabajo += r.turno_completo ? 1 : (hrs / horasPorDia) || 0
        porEmpleado[r.id_usuario].horas += hrs
      } else if (tipo === 'FALTA') porEmpleado[r.id_usuario].falta += 1
      else if (tipo === 'VACACION') porEmpleado[r.id_usuario].vacacion += 1
      else if (tipo === 'PERMISO_CON_GOCE') porEmpleado[r.id_usuario].permisoConGoce += 1
      else if (tipo === 'PERMISO_SIN_GOCE') porEmpleado[r.id_usuario].permisoSinGoce += 1
      else if (tipo === 'INCAPACIDAD') porEmpleado[r.id_usuario].incapacidad += 1
      else if (tipo === 'FESTIVO') porEmpleado[r.id_usuario].festivo += 1
    }
    let totalHoras = 0
    const filas = usuariosVisibles.map((u) => {
      const d = porEmpleado[u.id_usuario] || { nombre: u.nombre, trabajo: 0, falta: 0, vacacion: 0, permisoConGoce: 0, permisoSinGoce: 0, incapacidad: 0, festivo: 0, horas: 0 }
      totalHoras += d.horas
      return d
    })
    return { filas, totalHoras }
  }, [asistencia, usuariosVisibles, usuarios, rangoIni, rangoFin])

  const cambiarTipo = async (idUsuario, fechaStr, tipo) => {
    if (!puedeEditar) return
    const existente = getAsistenciaCelda(idUsuario, fechaStr)
    setEnviando(true)
    setError('')
    try {
      if (existente) {
        await api.put(`/asistencia/${existente.id}`, { tipo })
      } else {
        await api.post('/asistencia/', {
          id_usuario: idUsuario,
          fecha: fechaStr,
          tipo,
          turno_completo: true,
          aplica_bono_puntualidad: true,
        })
      }
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const abrirDetalle = (u, fechaStr) => {
    const a = getAsistenciaCelda(u.id_usuario, fechaStr)
    const turnoCompleto = a?.turno_completo !== false
    const horasPorDia = u?.horas_por_dia != null ? Number(u.horas_por_dia) : 8
    setCeldaEditando({ usuario: u, fecha: fechaStr, registro: a })
    setFormDetalle({
      tipo: a?.tipo ?? 'TRABAJO',
      horas_trabajadas: turnoCompleto ? horasPorDia : (a?.horas_trabajadas ?? ''),
      turno_completo: turnoCompleto,
      aplica_bono_puntualidad: a?.aplica_bono_puntualidad !== false,
      observaciones: a?.observaciones ?? '',
    })
    setError('')
    setModalDetalle(true)
  }

  const guardarDetalle = async () => {
    if (!celdaEditando) return
    const { usuario, fecha, registro } = celdaEditando
    const payload = {
      tipo: formDetalle.tipo,
      horas_trabajadas: formDetalle.horas_trabajadas ? parseFloat(formDetalle.horas_trabajadas) : 0,
      turno_completo: formDetalle.turno_completo,
      aplica_bono_puntualidad: formDetalle.aplica_bono_puntualidad,
      observaciones: formDetalle.observaciones?.trim() || null,
    }
    setEnviando(true)
    setError('')
    try {
      if (registro) {
        await api.put(`/asistencia/${registro.id}`, payload)
      } else {
        await api.post('/asistencia/', {
          id_usuario: usuario.id_usuario,
          fecha,
          ...payload,
        })
      }
      setModalDetalle(false)
      setCeldaEditando(null)
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : 'Error al guardar')
    } finally {
      setEnviando(false)
    }
  }

  const eliminarRegistro = async () => {
    if (!celdaEditando?.registro) return
    setEnviando(true)
    setError('')
    try {
      await api.delete(`/asistencia/${celdaEditando.registro.id}`)
      setModalDetalle(false)
      setCeldaEditando(null)
      cargar()
    } catch (err) {
      const d = err.response?.data?.detail
      setError(typeof d === 'string' ? d : 'Error al eliminar')
    } finally {
      setEnviando(false)
    }
  }

  if (!puedeEditar && user?.rol !== 'TECNICO' && user?.rol !== 'EMPLEADO') {
    return (
      <div className="p-4 sm:p-6">
        <p className="text-slate-600">No tienes permiso para ver asistencia.</p>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 min-h-0 flex flex-col">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Asistencia</h1>

      <div className="bg-white rounded-lg shadow border border-slate-200 flex flex-col min-h-0">
        <div className="p-4 border-b border-slate-200 flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Desde</label>
            <input
              type="date"
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
              className="px-3 py-2 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Hasta</label>
            <input
              type="date"
              value={fechaFin}
              onChange={(e) => setFechaFin(e.target.value)}
              className="px-3 py-2 min-h-[48px] border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 text-base sm:text-sm"
            />
          </div>
          <div className="flex gap-2 self-end">
            <button
              type="button"
              onClick={() => {
                const lun = getLunesSemana(hoy)
                const dom = new Date(lun)
                dom.setDate(lun.getDate() + 6)
                setFechaInicio(fechaAStr(lun))
                setFechaFin(fechaAStr(dom))
              }}
              className="px-3 py-2 text-xs bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200"
            >
              1 sem
            </button>
            <button
              type="button"
              onClick={() => {
                const lun = getLunesSemana(hoy)
                const dom = new Date(lun)
                dom.setDate(lun.getDate() + 13)
                setFechaInicio(fechaAStr(lun))
                setFechaFin(fechaAStr(dom))
              }}
              className="px-3 py-2 text-xs bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200"
            >
              2 sem
            </button>
          </div>
          <p className="text-sm text-slate-500 self-end pb-2">
            {dias.length > 0 ? `${fechaAStr(dias[0])} – ${fechaAStr(dias[dias.length - 1])}` : ''} {dias.length > 0 && `(${dias.length} días)`}
          </p>
          {puedeEditar && dias.some((d) => esFestivo(fechaAStr(d))) && (
            <button
              type="button"
              onClick={prellenarFestivos}
              disabled={prellenando}
              className="px-4 py-2 text-sm bg-amber-100 text-amber-800 rounded-lg hover:bg-amber-200 disabled:opacity-50 self-end"
            >
              {prellenando ? 'Prellenando...' : 'Prellenar festivos'}
            </button>
          )}
          <button
            type="button"
            onClick={exportarExcel}
            disabled={exportando}
            className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 self-end"
          >
            📥 {exportando ? 'Exportando...' : 'Exportar'}
          </button>
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer self-end pb-2">
            <input
              type="checkbox"
              checked={incluirRegistroManual}
              onChange={(e) => setIncluirRegistroManual(e.target.checked)}
              className="rounded border-slate-300"
            />
            Incluir registro manual
          </label>
          {enviando && <span className="text-sm text-amber-600">Guardando...</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>

        {loading ? (
          <p className="p-8 text-slate-500 text-center">Cargando...</p>
        ) : (
          <div className="overflow-x-auto flex-1 min-h-0">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-2 sm:px-3 py-3 text-left font-medium text-slate-600 whitespace-nowrap w-36">
                    Empleado
                  </th>
                  {dias.map((d) => (
                    <th
                      key={fechaAStr(d)}
                      className="px-1 sm:px-2 py-3 text-center font-medium text-slate-600 whitespace-nowrap min-w-[100px]"
                    >
                      <div>{DIAS_SEMANA[d.getDay() === 0 ? 6 : d.getDay() - 1]}</div>
                      <div className="text-xs text-slate-400">{d.getDate()}</div>
                      {esFestivo(fechaAStr(d)) && (
                        <span className="text-xs text-amber-600 font-normal">F</span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {usuarios.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                      No hay empleados. Configura usuarios en Configuración.
                    </td>
                  </tr>
                ) : usuariosVisibles.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                      No hay empleados que checan entrada/salida. Marca &quot;Incluir registro manual&quot; para ver todos.
                    </td>
                  </tr>
                ) : (
                  usuariosVisibles.map((u) => (
                    <tr key={u.id_usuario} className="hover:bg-slate-50">
                      <td className="px-2 sm:px-3 py-2 font-medium text-slate-800 whitespace-nowrap">
                        {u.nombre}
                      </td>
                      {dias.map((d) => {
                        const fechaStr = fechaAStr(d)
                        const reg = getAsistenciaCelda(u.id_usuario, fechaStr)
                        const laborable = trabajaEseDia(u, d)
                        const mostrarNoTrabaja = !laborable && !reg
                        return (
                          <td
                            key={fechaStr}
                            className={`px-1 sm:px-2 py-2 align-top ${mostrarNoTrabaja ? 'bg-slate-50' : ''}`}
                          >
                            <div className="flex flex-col gap-1">
                              {mostrarNoTrabaja ? (
                                <span className="text-xs text-slate-400 italic">No trabaja</span>
                              ) : (
                                <>
                                  <select
                                    value={reg?.tipo || ''}
                                    onChange={(e) => {
                                      const v = e.target.value
                                      if (v) cambiarTipo(u.id_usuario, fechaStr, v)
                                    }}
                                    disabled={!puedeEditar}
                                    className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-primary-500 disabled:bg-slate-100"
                                  >
                                    <option value="">—</option>
                                    {TIPOS_ASISTENCIA.map((t) => (
                                      <option key={t.value} value={t.value}>
                                        {t.label}
                                      </option>
                                    ))}
                                  </select>
                                  {(reg ? (
                                    <button
                                      type="button"
                                      onClick={() => abrirDetalle(u, fechaStr)}
                                      disabled={!puedeEditar}
                                      className="text-xs text-primary-600 hover:text-primary-700 disabled:opacity-50"
                                    >
                                      Detalle
                                    </button>
                                  ) : puedeEditar ? (
                                    <button
                                      type="button"
                                      onClick={() => abrirDetalle(u, fechaStr)}
                                      className="text-xs text-slate-500 hover:text-primary-600"
                                    >
                                      + Agregar
                                    </button>
                                  ) : null)}
                                </>
                              )}
                            </div>
                          </td>
                        )
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {!loading && usuariosVisibles.length > 0 && (
          <div className="border-t border-slate-200 p-4 bg-slate-50">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Resumen del período</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 uppercase">
                    <th className="px-2 py-1.5 font-medium">Empleado</th>
                    <th className="px-2 py-1.5 font-medium text-center">Trabajo</th>
                    <th className="px-2 py-1.5 font-medium text-center">Faltas</th>
                    <th className="px-2 py-1.5 font-medium text-center">Vacac.</th>
                    <th className="px-2 py-1.5 font-medium text-center">Perm.c/goce</th>
                    <th className="px-2 py-1.5 font-medium text-center">Perm.s/goce</th>
                    <th className="px-2 py-1.5 font-medium text-center">Incap.</th>
                    <th className="px-2 py-1.5 font-medium text-center">Festivo</th>
                    <th className="px-2 py-1.5 font-medium text-right">Horas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {resumenSemana.filas.map((f, i) => (
                    <tr key={usuariosVisibles[i]?.id_usuario || i} className="text-slate-700">
                      <td className="px-2 py-1.5 font-medium">{f.nombre}</td>
                      <td className="px-2 py-1.5 text-center">{f.trabajo > 0 ? f.trabajo.toFixed(1) : '—'}</td>
                      <td className="px-2 py-1.5 text-center">{f.falta > 0 ? f.falta : '—'}</td>
                      <td className="px-2 py-1.5 text-center">{f.vacacion > 0 ? f.vacacion : '—'}</td>
                      <td className="px-2 py-1.5 text-center">{f.permisoConGoce > 0 ? f.permisoConGoce : '—'}</td>
                      <td className="px-2 py-1.5 text-center">{f.permisoSinGoce > 0 ? f.permisoSinGoce : '—'}</td>
                      <td className="px-2 py-1.5 text-center">{f.incapacidad > 0 ? f.incapacidad : '—'}</td>
                      <td className="px-2 py-1.5 text-center">{f.festivo > 0 ? f.festivo : '—'}</td>
                      <td className="px-2 py-1.5 text-right font-mono">{f.horas > 0 ? f.horas.toFixed(1) : '—'}</td>
                    </tr>
                  ))}
                  <tr className="bg-slate-100 font-semibold text-slate-800">
                    <td className="px-2 py-2">Total</td>
                    <td colSpan={7} className="px-2 py-2" />
                    <td className="px-2 py-2 text-right font-mono">{resumenSemana.totalHoras.toFixed(1)} h</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <Modal
        titulo={
          celdaEditando
            ? `${celdaEditando.usuario?.nombre} – ${celdaEditando.fecha}`
            : 'Detalle de asistencia'
        }
        abierto={modalDetalle}
        onCerrar={() => {
          setModalDetalle(false)
          setCeldaEditando(null)
        }}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
            <select
              value={formDetalle.tipo}
              onChange={(e) => setFormDetalle({ ...formDetalle, tipo: e.target.value })}
              className="w-full px-4 py-3 border border-slate-300 rounded-lg"
            >
              {TIPOS_ASISTENCIA.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Horas trabajadas</label>
            <input
              type="number"
              step="0.5"
              min={0}
              max={24}
              value={formDetalle.horas_trabajadas}
              onChange={(e) => {
                const val = e.target.value
                const num = parseFloat(val)
                const esParcial = val !== '' && !isNaN(num) && num > 0
                setFormDetalle((prev) => ({
                  ...prev,
                  horas_trabajadas: val,
                  turno_completo: esParcial ? false : prev.turno_completo,
                }))
              }}
              className="w-full px-4 py-3 border border-slate-300 rounded-lg"
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formDetalle.turno_completo}
              onChange={(e) => {
                const checked = e.target.checked
                setFormDetalle((prev) => ({
                  ...prev,
                  turno_completo: checked,
                  horas_trabajadas: checked ? '' : prev.horas_trabajadas,
                }))
              }}
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">Turno completo</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formDetalle.aplica_bono_puntualidad}
              onChange={(e) =>
                setFormDetalle({ ...formDetalle, aplica_bono_puntualidad: e.target.checked })
              }
              className="rounded border-slate-300"
            />
            <span className="text-sm text-slate-700">Aplica bono puntualidad</span>
          </label>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
            <textarea
              value={formDetalle.observaciones}
              onChange={(e) => setFormDetalle({ ...formDetalle, observaciones: e.target.value })}
              rows={3}
              className="w-full px-4 py-3 border border-slate-300 rounded-lg"
              placeholder="Notas opcionales"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-between gap-2 pt-2">
            <div>
              {celdaEditando?.registro && (
                <button
                  type="button"
                  onClick={eliminarRegistro}
                  disabled={enviando}
                  className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50"
                >
                  Eliminar
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setModalDetalle(false)
                  setCeldaEditando(null)
                }}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={guardarDetalle}
                disabled={enviando}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {enviando ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
