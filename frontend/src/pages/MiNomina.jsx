import { useState, useEffect } from 'react'
import api from '../services/api'

const PERIODOS = { SEMANAL: 'Semanal', QUINCENAL: 'Quincenal', MENSUAL: 'Mensual' }

export default function MiNomina() {
  const [resumen, setResumen] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get('/prestamos-empleados/me/mi-resumen')
      .then((r) => setResumen(r.data))
      .catch(() => setResumen(null))
      .finally(() => setLoading(false))
  }, [])

  const formatearMoneda = (n) => n != null ? `$${Number(n).toLocaleString('es-MX', { minimumFractionDigits: 2 })}` : '-'
  const formatearFecha = (d) => {
  if (!d) return '-'
  const s = String(d).trim().slice(0, 10)
  const dt = /^\d{4}-\d{2}-\d{2}$/.test(s) ? new Date(s + 'T12:00:00') : new Date(d)
  return dt.toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' })
}

  if (loading) {
    return <p className="p-8 text-slate-500 text-center">Cargando...</p>
  }

  return (
    <div className="min-h-0 flex flex-col max-w-2xl mx-auto">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Mi nómina</h1>

      <div className="space-y-6">
        {/* Periodo y cálculo base */}
        {resumen?.periodo_inicio && (
          <div className="bg-white rounded-lg shadow border border-slate-200 p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-800 mb-3">
              Periodo {resumen.periodo_inicio && resumen.periodo_fin
                ? `${resumen.periodo_inicio} – ${resumen.periodo_fin}`
                : 'actual'}
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
                <details className="mt-2">
                  <summary className="cursor-pointer text-primary-600 hover:text-primary-700">Ver detalle asistencia</summary>
                  <ul className="mt-2 pl-4 space-y-1 text-slate-600">
                    {resumen.detalle_asistencia.map((a, i) => (
                      <li key={i}>{a.fecha}: {a.tipo} {a.dias_equiv}d {a.aplica_bono ? '✓ bono' : ''}</li>
                    ))}
                  </ul>
                </details>
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
                      <p className="text-sm text-slate-600">Descuento por periodo: <span className="font-medium text-slate-800">{formatearMoneda(p.descuento_por_periodo)}</span></p>
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
    </div>
  )
}
