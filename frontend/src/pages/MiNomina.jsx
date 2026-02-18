import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../services/api'
import { showError, showWarning } from '../utils/toast'
import { formatearFechaSolo } from '../utils/fechas'
import Tooltip from '../components/Tooltip'

const PERIODOS = { SEMANAL: 'Semanal', QUINCENAL: 'Quincenal', MENSUAL: 'Mensual' }

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
  const [resumen, setResumen] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [offsetPeriodos, setOffsetPeriodos] = useState(0)
  const printableRef = useRef(null)

  const cargar = useCallback((offset = 0) => {
    setLoading(true)
    setError(null)
    api.get('/prestamos-empleados/me/mi-resumen', { params: { offset_periodos: offset } })
      .then((r) => { setResumen(r.data); setError(null) })
      .catch((err) => { showError(err, 'Error al cargar nómina'); setResumen(null); setError(true) })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { cargar(offsetPeriodos) }, [cargar, offsetPeriodos])

  const handleCambioPeriodo = (e) => {
    const v = parseInt(e.target.value, 10)
    setOffsetPeriodos(v)
  }

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

  if (loading && !resumen) {
    return (
      <div className="min-h-0 flex flex-col w-full max-w-6xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Mi nómina</h1>
          <p className="text-slate-500 mt-1">Consultando tu información de pago…</p>
        </div>
        <SkeletonNomina />
      </div>
    )
  }

  if (error && !resumen) {
    return (
      <div className="min-h-0 flex flex-col w-full max-w-6xl">
        <h1 className="text-2xl font-bold text-slate-800 mb-6">Mi nómina</h1>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 mb-4">No se pudo cargar tu nómina. Revisa tu conexión e intenta de nuevo.</p>
          <button
            type="button"
            onClick={() => cargar(offsetPeriodos)}
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
      {/* Header: título, saludo, controles */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Mi nómina</h1>
          {resumen?.nombre && (
            <p className="text-slate-600 mt-0.5">Hola, {resumen.nombre}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
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
          <Tooltip text="Actualiza los datos desde el servidor">
            <button
              type="button"
              onClick={() => cargar(offsetPeriodos)}
              disabled={loading}
              className="px-4 py-2.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 font-medium"
            >
              {loading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </Tooltip>
          {!sinDatos && (
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

      {sinDatos ? (
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
            <Tooltip text="Comisiones por ventas o servicios (cuando estén disponibles)">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Comisiones del periodo</h2>
            </Tooltip>
            {resumen?.comisiones_periodo != null ? (
              <p className="text-xl font-bold text-slate-800">{formatearMoneda(resumen.comisiones_periodo)}</p>
            ) : (
              <p className="text-slate-500 italic">Próximamente. Las comisiones se mostrarán aquí cuando estén disponibles.</p>
            )}
          </div>
        </div>
      </>
      )}
    </div>
  )
}
