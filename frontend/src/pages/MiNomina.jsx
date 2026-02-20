import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../services/api'
import { showError, showWarning } from '../utils/toast'
import { formatearFechaSolo, fechaAStr } from '../utils/fechas'
import Tooltip from '../components/Tooltip'
import { useAuth } from '../context/AuthContext'
import Modal from '../components/Modal'

const PERIODOS = { SEMANAL: 'Semanal', QUINCENAL: 'Quincenal', MENSUAL: 'Mensual', PERSONALIZADO: 'Personalizado' }

const OPCIONES_OFFSET = [
  { value: 0, label: 'Periodo actual' },
  { value: -1, label: 'Periodo anterior' },
  { value: -2, label: 'Hace 2 periodos' },
  { value: -3, label: 'Hace 3 periodos' },
]

const LEYENDA_TIPOS = [
  { tipo: 'TRABAJO', desc: 'Día laboral normal (horas o turno completo)' },
  { tipo: 'FESTIVO', desc: 'Día festivo trabajado' },
  { tipo: 'VACACION', desc: 'Vacaciones (descuenta del saldo)' },
  { tipo: 'PERMISO_CON_GOCE', desc: 'Permiso pagado' },
  { tipo: 'INCAPACIDAD', desc: 'Enfermedad/accidente (según admin)' },
]

function SkeletonNomina() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-pulse">
      <div className="h-40 bg-slate-200 rounded-xl" />
      <div className="h-40 bg-slate-200 rounded-xl" />
      <div className="h-48 bg-slate-200 rounded-xl lg:col-span-2" />
      <div className="h-48 bg-slate-200 rounded-xl lg:col-span-2" />
    </div>
  )
}

export default function MiNomina() {
  const { user } = useAuth()
  const esAdmin = (typeof user?.rol === 'string' ? user.rol : user?.rol?.value) === 'ADMIN'
  const [vista, setVista] = useState(esAdmin ? 'equipo' : 'mi') // admin por defecto ve equipo
  const [resumen, setResumen] = useState(null)
  const [resumenEquipo, setResumenEquipo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [offsetPeriodos, setOffsetPeriodos] = useState(0)
  const hoy = new Date()
  const getLunes = (d) => {
    const dt = new Date(d)
    const day = dt.getDay()
    const diff = dt.getDate() - (day === 0 ? 6 : day - 1)
    return new Date(dt.getFullYear(), dt.getMonth(), diff)
  }
  const getDomingo = (lun) => {
    const d = new Date(lun)
    d.setDate(d.getDate() + 6)
    return d
  }
  const lunesActual = getLunes(hoy)
  const [fechaInicio, setFechaInicio] = useState(fechaAStr(lunesActual))
  const [fechaFin, setFechaFin] = useState(fechaAStr(getDomingo(lunesActual)))
  const [usarRango, setUsarRango] = useState(false)
  const printableRef = useRef(null)
  const [modalDetalle, setModalDetalle] = useState(null) // { empleado, detalle } o null
  const [loadingDetalle, setLoadingDetalle] = useState(false)

  const paramsParaCarga = useCallback(() => {
    if (usarRango && typeof fechaInicio === 'string' && fechaInicio.trim() && typeof fechaFin === 'string' && fechaFin.trim()) {
      const ini = fechaInicio.trim()
      const fin = fechaFin.trim()
      const [i, f] = ini <= fin ? [ini, fin] : [fin, ini]
      return { fecha_inicio: i, fecha_fin: f }
    }
    return { offset_periodos: offsetPeriodos }
  }, [usarRango, fechaInicio, fechaFin, offsetPeriodos])

  const cargar = useCallback(() => {
    setLoading(true)
    setError(null)
    api.get('/prestamos-empleados/me/mi-resumen', { params: paramsParaCarga() })
      .then((r) => { setResumen(r.data); setError(null) })
      .catch((err) => { showError(err, 'Error al cargar nómina'); setResumen(null); setError(true) })
      .finally(() => setLoading(false))
  }, [paramsParaCarga])

  const cargarEquipo = useCallback(() => {
    setLoading(true)
    setError(null)
    api.get('/prestamos-empleados/admin/resumen-nominas', { params: paramsParaCarga() })
      .then((r) => { setResumenEquipo(r.data); setError(null) })
      .catch((err) => { showError(err, 'Error al cargar nóminas'); setResumenEquipo(null); setError(true) })
      .finally(() => setLoading(false))
  }, [paramsParaCarga])

  useEffect(() => {
    if (vista === 'equipo' && esAdmin) cargarEquipo()
    else cargar()
  }, [vista, esAdmin, cargar, cargarEquipo])

  const handleCambioPeriodo = (e) => {
    const v = parseInt(e.target.value, 10)
    setOffsetPeriodos(v)
  }

  const verDetalleEmpleado = useCallback((empleado) => {
    setModalDetalle({ empleado, detalle: null })
    setLoadingDetalle(true)
    // Usar el mismo periodo que la tabla: si hay resumenEquipo con periodo, usar ese; si no, params actuales
    const params = (resumenEquipo?.periodo_inicio && resumenEquipo?.periodo_fin && resumenEquipo?.tipo_periodo === 'PERSONALIZADO')
      ? { fecha_inicio: resumenEquipo.periodo_inicio, fecha_fin: resumenEquipo.periodo_fin }
      : paramsParaCarga()
    api.get(`/prestamos-empleados/admin/resumen-nomina/${empleado.id_usuario}`, { params })
      .then((r) => setModalDetalle({ empleado, detalle: r.data }))
      .catch((err) => { showError(err, 'Error al cargar detalle'); setModalDetalle(null) })
      .finally(() => setLoadingDetalle(false))
  }, [paramsParaCarga, resumenEquipo])

  const mostrarVistaEquipo = esAdmin && vista === 'equipo'

  const formatearMoneda = (n) => n != null ? `$${Number(n).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '-'

  const imprimirRecibo = () => {
    const ventana = window.open('', '_blank', 'width=800,height=900')
    if (!ventana) {
      showWarning('Permite ventanas emergentes para imprimir.')
      return
    }
    const contenido = printableRef.current
    if (!contenido) return
    ventana.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <title>Recibo de nómina - ${resumen?.nombre || 'Empleado'}</title>
          <style>
            body { font-family: system-ui, sans-serif; padding: 24px; color: #1e293b; }
            h1 { font-size: 1.5rem; margin-bottom: 8px; }
            .periodo { color: #64748b; margin-bottom: 24px; }
            table { width: 100%; border-collapse: collapse; margin: 16px 0; }
            td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
            td:first-child { color: #64748b; width: 45%; }
            .total { font-weight: 700; font-size: 1.1rem; }
          </style>
        </head>
        <body>
          ${contenido.innerHTML}
        </body>
      </html>
    `)
    ventana.document.close()
    ventana.focus()
    setTimeout(() => { ventana.print(); ventana.close() }, 250)
  }

  const datosParaVista = mostrarVistaEquipo ? resumenEquipo : resumen
  const reintentar = () => (mostrarVistaEquipo ? cargarEquipo() : cargar())

  if (loading && !datosParaVista) {
    return (
      <div className="min-h-0 flex flex-col w-full max-w-6xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">{mostrarVistaEquipo ? 'Nóminas del equipo' : 'Mi nómina'}</h1>
          <p className="text-slate-500 mt-1">Consultando información de pago…</p>
        </div>
        <SkeletonNomina />
      </div>
    )
  }

  if (error && !datosParaVista) {
    return (
      <div className="min-h-0 flex flex-col w-full max-w-6xl">
        <h1 className="text-2xl font-bold text-slate-800 mb-6">{mostrarVistaEquipo ? 'Nóminas del equipo' : 'Mi nómina'}</h1>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 mb-4">No se pudo cargar la información. Revisa tu conexión e intenta de nuevo.</p>
          <button
            type="button"
            onClick={reintentar}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  const sinDatos = !resumen?.periodo_inicio && !resumen?.prestamos_activos?.length
  const tieneDias = resumen?.dias_pagados != null
  const tieneEstimado = resumen?.periodo_inicio && (resumen?.total_bruto_estimado != null || resumen?.total_neto_estimado != null)

  return (
    <div className="min-h-0 flex flex-col w-full max-w-6xl">
      {/* Header: título, pestañas (admin), controles */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            {mostrarVistaEquipo ? 'Nóminas del equipo' : 'Mi nómina'}
          </h1>
          {mostrarVistaEquipo ? (
            <p className="text-slate-600 mt-0.5">
              Cuánto pagar a cada empleado en el periodo
            </p>
          ) : (
            resumen?.nombre && <p className="text-slate-600 mt-0.5">Hola, {resumen.nombre}</p>
          )}
        </div>
        {esAdmin && (
          <div className="flex gap-2 border-b border-slate-200 pb-2 sm:pb-0 sm:border-0">
            <button
              type="button"
              onClick={() => setVista('equipo')}
              className={`px-3 py-2 text-sm font-medium rounded-lg ${vista === 'equipo' ? 'bg-primary-100 text-primary-700' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              Nóminas del equipo
            </button>
            <button
              type="button"
              onClick={() => setVista('mi')}
              className={`px-3 py-2 text-sm font-medium rounded-lg ${vista === 'mi' ? 'bg-primary-100 text-primary-700' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              Mi nómina
            </button>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={usarRango}
              onChange={(e) => setUsarRango(e.target.checked)}
              className="rounded border-slate-300"
            />
            <span className="text-slate-600">Rango de fechas</span>
          </label>
          {usarRango ? (
            <>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Desde</label>
                <input
                  type="date"
                  value={fechaInicio}
                  onChange={(e) => setFechaInicio(e.target.value)}
                  className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 min-w-[140px]"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Hasta</label>
                <input
                  type="date"
                  value={fechaFin}
                  onChange={(e) => setFechaFin(e.target.value)}
                  className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 min-w-[140px]"
                />
              </div>
            </>
          ) : (
            <Tooltip text="Selecciona el periodo de pago que deseas consultar">
              <select
                value={offsetPeriodos}
                onChange={handleCambioPeriodo}
                className="px-4 py-2.5 text-sm border border-slate-300 rounded-lg bg-white hover:border-slate-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 min-w-[180px]"
              >
                {OPCIONES_OFFSET.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </Tooltip>
          )}
          <Tooltip text="Actualiza los datos desde el servidor">
            <button
              type="button"
              onClick={() => (mostrarVistaEquipo ? cargarEquipo() : cargar())}
              disabled={loading}
              className="px-4 py-2.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 font-medium"
            >
              {loading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </Tooltip>
          {!sinDatos && !mostrarVistaEquipo && (
            <Tooltip text="Genera e imprime el recibo de nómina para este periodo">
              <button
                type="button"
                onClick={imprimirRecibo}
                className="px-4 py-2.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
              >
                Imprimir recibo
              </button>
            </Tooltip>
          )}
        </div>
      </div>

      {mostrarVistaEquipo && resumenEquipo ? (
        /* Vista admin: tabla de nóminas por empleado */
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Periodo</p>
              <p className="text-sm font-medium text-slate-800 mt-1">
                {resumenEquipo.periodo_inicio} – {resumenEquipo.periodo_fin}
                <span className="text-slate-500 font-normal ml-1">
                  ({PERIODOS[resumenEquipo.tipo_periodo] || resumenEquipo.tipo_periodo})
                </span>
              </p>
            </div>
            <div className="bg-primary-50 rounded-xl border border-primary-200 p-4 shadow-sm">
              <p className="text-xs text-primary-700 uppercase tracking-wide font-medium">Total bruto periodo</p>
              <p className="text-xl font-bold text-primary-800 mt-1">{formatearMoneda(resumenEquipo.total_bruto_general)}</p>
            </div>
            <div className="bg-emerald-50 rounded-xl border border-emerald-200 p-4 shadow-sm">
              <p className="text-xs text-emerald-700 uppercase tracking-wide font-medium">Total neto a pagar</p>
              <p className="text-xl font-bold text-emerald-800 mt-1">{formatearMoneda(resumenEquipo.total_neto_general)}</p>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-2 sm:px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Empleado</th>
                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase w-16" aria-label="Ver detalle" />
                    <th className="px-2 sm:px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Días</th>
                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Salario prop.</th>
                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Bono</th>
                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Comis.</th>
                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Desct.</th>
                    <th className="px-2 sm:px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Neto</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {resumenEquipo.empleados?.map((e) => (
                    <tr key={e.id_usuario} className="hover:bg-slate-50">
                      <td className="px-2 sm:px-4 py-3 font-medium text-slate-800">{e.nombre}</td>
                      <td className="px-2 sm:px-4 py-3 text-center">
                        <button
                          type="button"
                          onClick={() => verDetalleEmpleado(e)}
                          className="min-h-[36px] px-3 py-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium rounded touch-manipulation active:bg-primary-50"
                        >
                          Ver detalle
                        </button>
                      </td>
                      <td className="px-2 sm:px-4 py-3 text-center text-slate-600">
                        {e.dias_pagados != null ? `${e.dias_pagados} / ${e.dias_esperados ?? '-'}` : '—'}
                      </td>
                      <td className="px-2 sm:px-4 py-3 text-right text-slate-700">{formatearMoneda(e.salario_proporcional)}</td>
                      <td className="px-2 sm:px-4 py-3 text-right text-slate-700">{formatearMoneda(e.bono_puntualidad)}</td>
                      <td className="px-2 sm:px-4 py-3 text-right text-slate-700">{formatearMoneda(e.comisiones_periodo)}</td>
                      <td className="px-2 sm:px-4 py-3 text-right text-amber-600">
                        {e.total_descuento_este_periodo > 0 ? `-${formatearMoneda(e.total_descuento_este_periodo)}` : '—'}
                      </td>
                      <td className="px-2 sm:px-4 py-3 text-right font-semibold text-slate-800">{formatearMoneda(e.total_neto_estimado)}</td>
                    </tr>
                  ))}
                  {(!resumenEquipo.empleados || resumenEquipo.empleados.length === 0) && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-slate-500">No hay empleados activos con datos de nómina para este periodo.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {resumenEquipo.empleados?.length > 0 && (
              <div className="px-4 py-3 bg-slate-100 border-t border-slate-200 flex justify-end gap-6 text-sm font-semibold">
                <span className="text-slate-700">Total bruto: {formatearMoneda(resumenEquipo.total_bruto_general)}</span>
                <span className="text-emerald-700">Total neto: {formatearMoneda(resumenEquipo.total_neto_general)}</span>
              </div>
            )}
          </div>
        </div>
      ) : sinDatos ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
          <p className="text-amber-800">
            Tu perfil de nómina aún no está configurado o no hay datos para este periodo.
            <br />
            <span className="text-sm">Contacta a Recursos Humanos para configurar tu información.</span>
          </p>
        </div>
      ) : (
      <>
        {/* Barra resumen: métricas clave cuando hay datos */}
        {tieneDias || tieneEstimado ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
            {tieneDias && (
              <Tooltip text="Días laborales ya registrados en el sistema vs. días esperados en el periodo">
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Días pagados</p>
                  <p className="text-xl font-bold text-slate-800 mt-1">
                    {resumen.dias_pagados}
                    {resumen.dias_esperados != null && <span className="text-slate-500 font-normal text-base"> / {resumen.dias_esperados}</span>}
                  </p>
                </div>
              </Tooltip>
            )}
            {resumen?.total_bruto_estimado != null && (
              <Tooltip text="Total antes de descuentos (salario proporcional + bonos)">
                <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Bruto</p>
                  <p className="text-xl font-bold text-slate-800 mt-1">{formatearMoneda(resumen.total_bruto_estimado)}</p>
                </div>
              </Tooltip>
            )}
            {resumen?.total_descuento_este_periodo > 0 && (
              <Tooltip text="Total que se descuenta este periodo (préstamos, etc.)">
                <div className="bg-white rounded-xl border border-amber-100 p-4 shadow-sm">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Descuentos</p>
                  <p className="text-xl font-bold text-amber-700 mt-1">-{formatearMoneda(resumen.total_descuento_este_periodo)}</p>
                </div>
              </Tooltip>
            )}
            {resumen?.total_neto_estimado != null && (
              <Tooltip text="Lo que recibirás después de descuentos (estimado)">
                <div className="bg-primary-50 rounded-xl border border-primary-200 p-4 shadow-sm">
                  <p className="text-xs text-primary-700 uppercase tracking-wide font-medium">Neto estimado</p>
                  <p className="text-xl font-bold text-primary-800 mt-1">{formatearMoneda(resumen.total_neto_estimado)}</p>
                </div>
              </Tooltip>
            )}
          </div>
        ) : null}

        {/* Contenido imprimible (oculto) */}
        <div ref={printableRef} className="hidden print:block" aria-hidden>
          <h1>Recibo de nómina</h1>
          <p className="periodo">
            {resumen?.nombre} • {resumen?.periodo_inicio && resumen?.periodo_fin ? `${resumen.periodo_inicio} – ${resumen.periodo_fin}` : 'Periodo'}
          </p>
          <table>
            {resumen?.dias_pagados != null && (
              <tr><td>Días pagados</td><td>{resumen.dias_pagados}{resumen.dias_esperados != null ? ` de ${resumen.dias_esperados}` : ''}</td></tr>
            )}
            {resumen?.salario_base != null && resumen.salario_base > 0 && (
              <tr><td>Salario proporcional</td><td>{formatearMoneda(resumen.salario_proporcional)}</td></tr>
            )}
            {resumen?.bono_puntualidad != null && resumen.bono_puntualidad > 0 && (
              <tr><td>Bono puntualidad</td><td>{formatearMoneda(resumen.bono_puntualidad)}</td></tr>
            )}
            {resumen?.comisiones_periodo != null && resumen.comisiones_periodo > 0 && (
              <tr><td>Comisiones</td><td>{formatearMoneda(resumen.comisiones_periodo)}</td></tr>
            )}
            {resumen?.total_descuento_este_periodo > 0 && (
              <tr><td>Descuentos</td><td>-{formatearMoneda(resumen.total_descuento_este_periodo)}</td></tr>
            )}
            {resumen?.total_neto_estimado != null && (
              <tr><td className="total">Neto estimado</td><td className="total">{formatearMoneda(resumen.total_neto_estimado)}</td></tr>
            )}
          </table>
        </div>

        {/* Grid de tarjetas: 2 columnas en pantallas grandes */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Periodo y asistencia */}
          {resumen?.periodo_inicio && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6">
              <div className="flex items-start justify-between gap-2 mb-4">
                <h2 className="text-lg font-semibold text-slate-800">
                  Periodo {resumen.periodo_inicio && resumen.periodo_fin ? `${resumen.periodo_inicio} – ${resumen.periodo_fin}` : 'actual'}
                  {(typeof resumen.tipo_periodo === 'string' ? resumen.tipo_periodo : resumen.tipo_periodo?.value) && (
                    <span className="text-slate-500 font-normal ml-1">
                      ({PERIODOS[typeof resumen.tipo_periodo === 'string' ? resumen.tipo_periodo : resumen.tipo_periodo?.value] || resumen.tipo_periodo})
                    </span>
                  )}
                </h2>
              </div>
              <div className="space-y-3 text-sm">
                {resumen.salario_base != null && resumen.salario_base > 0 && (
                  <div className="flex justify-between text-slate-600">
                    <Tooltip text="Salario base configurado para tu puesto">
                      <span>Salario base</span>
                    </Tooltip>
                    <span>{formatearMoneda(resumen.salario_base)} → {formatearMoneda(resumen.salario_proporcional)}</span>
                  </div>
                )}
                {resumen.bono_puntualidad != null && resumen.bono_puntualidad > 0 && (
                  <div className="flex justify-between text-slate-600">
                    <Tooltip text="Bono por asistencia puntual en el periodo">
                      <span>Bono puntualidad</span>
                    </Tooltip>
                    <span className="font-medium text-green-700">{formatearMoneda(resumen.bono_puntualidad)}</span>
                  </div>
                )}
                {resumen.detalle_asistencia?.length > 0 && (
                  <details className="mt-3 border-t border-slate-100 pt-3">
                    <summary className="cursor-pointer text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1">
                      Ver detalle asistencia
                      <Tooltip text="Desglose día a día de tu registro (trabajo, bonos, vacaciones, etc.)">
                        <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-200 text-slate-500 text-xs hover:bg-slate-300">?</span>
                      </Tooltip>
                    </summary>
                    <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {resumen.detalle_asistencia.map((a, i) => (
                        <div key={i} className="flex items-center justify-between text-slate-600 bg-slate-50 rounded-lg px-3 py-2 text-xs">
                          <span>{a.fecha}</span>
                          <span className="font-medium">
                            {a.tipo} {a.dias_equiv}d {a.aplica_bono && <span className="text-green-600">✓ bono</span>}
                          </span>
                        </div>
                      ))}
                    </div>
                    <details className="mt-3">
                      <summary className="cursor-pointer text-slate-500 hover:text-slate-600 text-xs flex items-center gap-1">
                        ¿Qué significan los tipos?
                        <Tooltip text="Leyenda de los códigos de asistencia (TRABAJO, VACACION, etc.)">
                          <span className="inline-flex w-3.5 h-3.5 rounded-full bg-slate-200 text-[10px] items-center justify-center">?</span>
                        </Tooltip>
                      </summary>
                      <ul className="mt-2 pl-4 space-y-1 text-xs text-slate-500">
                        {LEYENDA_TIPOS.map((l) => (
                          <li key={l.tipo}><strong>{l.tipo}:</strong> {l.desc}</li>
                        ))}
                      </ul>
                    </details>
                  </details>
                )}
              </div>
            </div>
          )}

          {/* Estimado del periodo */}
          {tieneEstimado && (
            <div className="bg-primary-50/50 rounded-xl border border-primary-200 p-5 sm:p-6">
              <Tooltip text="Resumen de percepciones y deducciones para este periodo">
                <h2 className="text-lg font-semibold text-slate-800 mb-4">Estimado del periodo</h2>
              </Tooltip>
              <div className="space-y-3">
                {resumen.total_bruto_estimado != null && (
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Bruto</span>
                    <span className="font-medium">{formatearMoneda(resumen.total_bruto_estimado)}</span>
                  </div>
                )}
                {resumen.total_descuento_este_periodo > 0 && (
                  <div className="flex justify-between items-center text-amber-700">
                    <span>Menos descuentos</span>
                    <span className="font-medium">-{formatearMoneda(resumen.total_descuento_este_periodo)}</span>
                  </div>
                )}
                {resumen.total_neto_estimado != null && (
                  <div className="flex justify-between items-center pt-3 border-t border-primary-200">
                    <span className="font-semibold text-slate-800">Neto</span>
                    <span className="text-xl font-bold text-primary-800">{formatearMoneda(resumen.total_neto_estimado)}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Descuentos y Comisiones: segunda fila */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6">
            <Tooltip text="Préstamos que tienes activos y el monto que se descuenta cada periodo">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Descuentos por préstamos</h2>
            </Tooltip>
            {resumen?.prestamos_activos?.length > 0 ? (
              <div className="space-y-4">
                {resumen.prestamos_activos.map((p) => (
                  <div key={p.id} className="border border-slate-200 rounded-lg p-4">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                      <div>
                        <p className="font-medium text-slate-800">Préstamo #{p.id}</p>
                        <p className="text-sm text-slate-600">Inicio: {formatearFechaSolo(p.fecha_inicio)} • {PERIODOS[typeof p.periodo_descuento === 'string' ? p.periodo_descuento : p.periodo_descuento?.value] || p.periodo_descuento}</p>
                      </div>
                      <div className="text-left sm:text-right">
                        <p className="text-sm text-slate-600">
                          Descuento: <span className="font-medium text-slate-800">{formatearMoneda(p.descuento_por_periodo)}</span>
                        </p>
                        <p className="text-sm">
                          Saldo: <span className="font-semibold text-slate-800">{formatearMoneda(p.saldo_pendiente)}</span>
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                <div className="pt-3 border-t border-slate-200">
                  <p className="text-sm text-slate-600">Total descuento este periodo:</p>
                  <p className="text-xl font-bold text-slate-800">{formatearMoneda(resumen.total_descuento_este_periodo)}</p>
                </div>
              </div>
            ) : (
              <p className="text-slate-500">No tienes préstamos activos ni descuentos.</p>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 sm:p-6">
            <Tooltip text="Comisiones devengadas por ventas del periodo (mano de obra, partes, servicios, productos)">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Comisiones del periodo</h2>
            </Tooltip>
            {resumen?.comisiones_periodo != null ? (
              <p className="text-xl font-bold text-slate-800">{formatearMoneda(resumen.comisiones_periodo)}</p>
            ) : (
              <p className="text-slate-500 italic">No hay datos de periodo o comisiones para este periodo.</p>
            )}
          </div>
        </div>
      </>
      )}

      {/* Modal detalle empleado (vista admin) */}
      <Modal
        titulo={modalDetalle ? `Detalle nómina – ${modalDetalle.empleado?.nombre}` : 'Detalle'}
        abierto={!!modalDetalle}
        onCerrar={() => setModalDetalle(null)}
        size="xl"
      >
        {modalDetalle && (
          loadingDetalle ? (
            <div className="py-12 text-center text-slate-500">Cargando detalle…</div>
          ) : modalDetalle.detalle ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-slate-500 text-xs">Periodo</p>
                  <p className="font-medium">{modalDetalle.detalle.periodo_inicio} – {modalDetalle.detalle.periodo_fin}</p>
                  <p className="text-slate-500 text-xs">({PERIODOS[modalDetalle.detalle.tipo_periodo] || modalDetalle.detalle.tipo_periodo})</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-slate-500 text-xs">Días pagados</p>
                  <p className="font-medium">{modalDetalle.detalle.dias_pagados ?? '—'} / {modalDetalle.detalle.dias_esperados ?? '—'}</p>
                </div>
              </div>
              <div className="border-t border-slate-200 pt-4 space-y-2">
                <div className="flex justify-between text-sm"><span className="text-slate-600">Salario base → proporcional</span><span>{formatearMoneda(modalDetalle.detalle.salario_base)} → {formatearMoneda(modalDetalle.detalle.salario_proporcional)}</span></div>
                {modalDetalle.detalle.bono_puntualidad > 0 && (
                  <div className="flex justify-between text-sm"><span className="text-slate-600">Bono puntualidad</span><span className="text-green-700 font-medium">{formatearMoneda(modalDetalle.detalle.bono_puntualidad)}</span></div>
                )}
                {modalDetalle.detalle.comisiones_periodo > 0 && (
                  <div className="flex justify-between text-sm"><span className="text-slate-600">Comisiones</span><span>{formatearMoneda(modalDetalle.detalle.comisiones_periodo)}</span></div>
                )}
                {modalDetalle.detalle.total_descuento_este_periodo > 0 && (
                  <div className="flex justify-between text-sm text-amber-700"><span>Descuentos</span><span>-{formatearMoneda(modalDetalle.detalle.total_descuento_este_periodo)}</span></div>
                )}
                <div className="flex justify-between pt-3 border-t border-slate-200 font-semibold">
                  <span>Neto estimado</span>
                  <span className="text-primary-700">{formatearMoneda(modalDetalle.detalle.total_neto_estimado)}</span>
                </div>
              </div>
              {modalDetalle.detalle.detalle_asistencia?.length > 0 && (
                <details className="border border-slate-200 rounded-lg">
                  <summary className="cursor-pointer px-4 py-3 text-primary-600 hover:bg-slate-50 font-medium">Ver detalle asistencia</summary>
                  <div className="px-4 pb-3 grid grid-cols-2 gap-2">
                    {modalDetalle.detalle.detalle_asistencia.map((a, i) => (
                      <div key={i} className="text-xs bg-slate-50 rounded px-2 py-1.5">
                        {a.fecha} – {a.tipo} {a.dias_equiv}d {a.aplica_bono && <span className="text-green-600">✓ bono</span>}
                      </div>
                    ))}
                  </div>
                </details>
              )}
              {modalDetalle.detalle.prestamos_activos?.length > 0 && (
                <div className="border border-slate-200 rounded-lg p-4">
                  <h3 className="font-medium text-slate-800 mb-2">Préstamos activos</h3>
                  <div className="space-y-2">
                    {modalDetalle.detalle.prestamos_activos.map((p) => (
                      <div key={p.id} className="flex justify-between text-sm bg-slate-50 rounded px-3 py-2">
                        <span>Préstamo #{p.id}</span>
                        <span>Descuento: {formatearMoneda(p.descuento_por_periodo)} • Saldo: {formatearMoneda(p.saldo_pendiente)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-slate-500 py-4">No se pudo cargar el detalle.</p>
          )
        )}
      </Modal>
    </div>
  )
}
