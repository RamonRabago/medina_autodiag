import CitaOperativaCard from './CitaOperativaCard'

export default function BandejaCitaSection({
  titulo,
  total = 0,
  items = [],
  vacio = 'No hay citas en esta bandeja',
  onAccionExito,
  AccionesRenderer,
}) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-slate-800 mb-1">
        {titulo}
        <span className="ml-2 text-sm font-normal text-slate-500">({total})</span>
      </h2>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500 py-6 text-center rounded-xl bg-slate-50 border border-dashed border-slate-200">
          {vacio}
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <CitaOperativaCard
              key={item.id}
              item={item}
              AccionesRenderer={AccionesRenderer}
              onAccionExito={onAccionExito}
            />
          ))}
        </div>
      )}
    </section>
  )
}
