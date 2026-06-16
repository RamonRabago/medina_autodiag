const SEVERIDAD_CLASS = {
  alta: 'border-red-200 bg-red-50 text-red-900',
  media: 'border-amber-200 bg-amber-50 text-amber-950',
  baja: 'border-slate-200 bg-slate-50 text-slate-800',
}

/**
 * Lista alertas_operativas[] de A0 por severidad (solo contadores/mensajes).
 */
export default function AlertasOperativasBanner({ alertas = [] }) {
  if (!alertas.length) return null

  return (
    <div className="space-y-2">
      {alertas.map((alerta) => (
        <div
          key={alerta.codigo}
          className={`rounded-xl border px-4 py-3 text-sm ${
            SEVERIDAD_CLASS[alerta.severidad] ?? SEVERIDAD_CLASS.media
          }`}
        >
          <p className="font-medium">{alerta.mensaje}</p>
        </div>
      ))}
    </div>
  )
}
