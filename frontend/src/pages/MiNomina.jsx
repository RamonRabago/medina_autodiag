import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../services/api'
import { showError } from '../utils/toast'

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
    <div className="space-y-6 animate-pulse">
      <div className="h-8 bg-slate-200 rounded w-48" />
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-3">
        <div className="h-5 bg-slate-200 rounded w-32" />
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-4 bg-slate-200 rounded w-3/4" />
        <div className="h-4 bg-slate-200 rounded w-1/2" />
      </div>
      <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-3">
        <div className="h-5 bg-slate-200 rounded w-40" />
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-4 bg-slate-200 rounded w-2/3" />
      </div>
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
  const formatearFecha = (d) => {
    if (!d) return '-'
    const s = String(d).trim().slice(0, 10)
    const dt = /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(s + 'T12:00:00') : new Date(d)
    return dt.toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' })
  }

  const imprimirRecibo = () => {
    const ventana = window.open('', '_blank', 'width=800,height=900')
    if (!ventana) {
      showError('Permite ventanas emergentes para imprimir.')
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
      <div className="min-h-0 flex flex-col max-w-2xl mx-auto">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Mi nómina</h1>
        <SkeletonNomina />
      </div>
    )
  }

  if (error && !resumen) {
    return (
      <div className="min-h-0 flex flex-col max-w-2xl mx-auto">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Mi nómina</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
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

  return (
    <div className="min-h-0 flex flex-col max-w-2xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 sm:mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Mi nómina</h1>
          {resumen?.nombre && (
            <p className="text-sm text-slate-600 mt-1">Hola, {resumen.nombre}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={offsetPeriodos}
            onChange={handleCambioPeriodo}
            className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white"
          >
            {OPCIONES_OFFSET.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => cargar(offsetPeriodos)}
            disabled={loading}
            className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
            title="Actualizar datos"
          >
            {loading ? 'Actualizando...' : 'Actualizar'}
          </button>
          {!sinDatos && (
            <button
              type="button"
              onClick={imprimirRecibo}
              className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              title="Imprimir recibo"
            >
              Imprimir recibo
            </button>
          )}
        </div>
      </div>

      {sinDatos ? (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
          <p className="text-amber-800">
            Tu perfil de nómina aún no está configurado o no hay datos para este periodo.
            <br />
            <span className="text-sm">Contacta a Recursos Humanos para configurar tu información.</span>
          </p>
        </div>
      ) : (
      <div className="space-y-6">
        {/* Contenido imprimible (oculto en pantalla, visible al imprimir) */}
        <div ref={printableRef} className="hidden print:block" aria-hidden>
          <h1>Recibo de nómina</h1>
          <p className="periodo">
            {resumen?.nombre} • {resumen?.periodo_inicio && resumen?.periodo_fin
              ? `${resumen.periodo_inicio} – ${resumen.periodo_fin}`
              : 'Periodo'}
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

        {/* Periodo y cálculo base */}
        {resumen?.periodo_inicio && (
          <div className="bg-white rounded-lg shadow border border-slate-200 p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-3">
              Periodo {resumen.periodo_inicio && resumen.periodo_fin
                ? `${resumen.periodo_inicio} – ${resumen.periodo_fin}`
                : 'actual'}
              {resumen.tipo_periodo && (
                <span className="text-sm font-normal text-slate-500 ml-2">
                  ({PERIODOS[resumen.tipo_periodo] || resumen.tipo_periodo})
                </span>
              )}
            </h2>
            <div className="space-y-2 text-sm">
              {resumen.dias_pagados != null && (
                <p className="text-slate-600">
                  Días pagados: <strong>{resumen.dias_pagados}</strong>
                  {resumen.dias_esperados != null && ` de ${resumen.dias_esperados} esperados`}
                </p>
              )}
              {resumen.salario_base != null && resumen.salario_base > 0 && (
                <p className="text-slate-600">
                  Salario base: {formatearMoneda(resumen.salario_base)} → Proporcional: {formatearMoneda(resumen.salario_proporcional)}
                </p>
              )}
              {resumen.bono_puntualidad != null && resumen.bono_puntualidad > 0 && (
                <p className="text-slate-600">Bono puntualidad: {formatearMoneda(resumen.bono_puntualidad)}</p>
              )}
              {resumen.detalle_asistencia?.length > 0 && (
                <>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-primary-600 hover:text-primary-700">
                      Ver detalle asistencia
                    </summary>
                    <ul className="mt-2 pl-4 space-y-1 text-slate-600">
                      {resumen.detalle_asistencia.map((a, i) => (
                        <li key={i}>{a.fecha}: {a.tipo} {a.dias_equiv}d {a.aplica_bono ? '✓ bono' : ''}</li>
                      ))}
                    </ul>
                  </details>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-slate-500 hover:text-slate-600 text-xs">
                      ¿Qué significan los tipos?
                    </summary>
                    <ul className="mt-2 pl-4 space-y-1 text-xs text-slate-500">
                      {LEYENDA_TIPOS.map((l) => (
                        <li key={l.tipo}><strong>{l.tipo}:</strong> {l.desc}</li>
                      ))}
                    </ul>
                  </details>
                </>
              )}
            </div>
          </div>
        )}

        {/* Totales */}
        {resumen?.periodo_inicio && (resumen?.total_bruto_estimado != null || resumen?.total_neto_estimado != null) && (
          <div className="bg-primary-50 rounded-lg border border-primary-200 p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-3">Estimado del periodo</h2>
            <div className="space-y-2">
              {resumen.total_bruto_estimado != null && (
                <p className="text-slate-700">Bruto: {formatearMoneda(resumen.total_bruto_estimado)}</p>
              )}
              {resumen.total_descuento_este_periodo > 0 && (
                <p className="text-slate-600">Menos descuentos: {formatearMoneda(resumen.total_descuento_este_periodo)}</p>
              )}
              {resumen.total_neto_estimado != null && (
                <p className="text-lg font-bold text-slate-800">Neto: {formatearMoneda(resumen.total_neto_estimado)}</p>
              )}
            </div>
          </div>
        )}

        {/* Descuentos por préstamos */}
        <div className="bg-white rounded-lg shadow border border-slate-200 p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-3">Descuentos por préstamos</h2>
          {resumen?.prestamos_activos?.length > 0 ? (
            <div className="space-y-4">
              {resumen.prestamos_activos.map((p) => (
                <div key={p.id} className="border border-slate-200 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-slate-800">Préstamo #{p.id}</p>
                      <p className="text-sm text-slate-600">Inicio: {formatearFecha(p.fecha_inicio)} • {PERIODOS[p.periodo_descuento] || p.periodo_descuento}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-slate-600">Descuento este periodo: <span className="font-medium text-slate-800">{formatearMoneda(p.descuento_por_periodo)}</span></p>
                      <p className="text-sm">Saldo pendiente: <span className="font-semibold text-slate-800">{formatearMoneda(p.saldo_pendiente)}</span></p>
                    </div>
                  </div>
                </div>
              ))}
              <div className="pt-3 border-t border-slate-200">
                <p className="text-sm text-slate-600">Total que se te descontará este periodo:</p>
                <p className="text-xl font-bold text-slate-800">{formatearMoneda(resumen.total_descuento_este_periodo)}</p>
              </div>
            </div>
          ) : (
            <p className="text-slate-500">No tienes préstamos activos ni descuentos.</p>
          )}
        </div>

        {/* Comisiones (Etapa 3 - placeholder) */}
        <div className="bg-white rounded-lg shadow border border-slate-200 p-4 sm:p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-3">Comisiones del periodo</h2>
          {resumen?.comisiones_periodo != null ? (
            <p className="text-slate-700">{formatearMoneda(resumen.comisiones_periodo)}</p>
          ) : (
            <p className="text-slate-500 italic">Próximamente. Las comisiones se mostrarán aquí cuando estén disponibles.</p>
          )}
        </div>
      </div>
      )}
    </div>
  )
}
