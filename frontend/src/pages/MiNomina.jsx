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
  const formatearFecha = (d) => d ? new Date(d).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' }) : '-'

  if (loading) {
    return <p className="p-8 text-slate-500 text-center">Cargando...</p>
  }

  return (
    <div className="min-h-0 flex flex-col max-w-2xl mx-auto">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4 sm:mb-6">Mi nómina</h1>

      <div className="space-y-6">
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
