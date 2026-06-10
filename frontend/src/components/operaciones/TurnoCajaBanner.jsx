import { Link } from 'react-router-dom'

/**
 * Banner de turno de caja desde A0 (data.caja).
 * Fase 1: informativo — acciones de pago en Fase 2+.
 */
export default function TurnoCajaBanner({ caja }) {
  const turnoAbierto = caja?.turno_abierto === true

  if (turnoAbierto) {
    return (
      <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        <p className="font-medium">Turno de caja abierto</p>
        {caja?.id_turno != null && (
          <p className="text-emerald-800/80 mt-0.5">Turno #{caja.id_turno}</p>
        )}
      </div>
    )
  }

  return (
    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
      <p className="font-medium">No hay turno de caja abierto</p>
      <p className="mt-1 text-amber-900/90">
        Para registrar pagos desde mostrador necesitas abrir turno en el módulo de caja.
      </p>
      <Link
        to="/caja"
        className="mt-2 inline-flex min-h-[36px] items-center text-sm font-medium text-amber-950 underline underline-offset-2 hover:text-amber-900 touch-manipulation"
      >
        Abrir turno en Caja →
      </Link>
    </div>
  )
}
