import { Link } from 'react-router-dom'
import AccionesCajaRenderer from './AccionesCajaRenderer'

function formatearMoneda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '—'
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(valor))
}

/**
 * Bandeja ventas con saldo pendiente (A0 ventas_saldo_pendiente).
 */
export default function BandejaVentaSection({
  titulo,
  total = 0,
  items = [],
  vacio = 'No hay ventas con saldo pendiente',
  soloLectura = false,
  AccionesRenderer = AccionesCajaRenderer,
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
            <article
              key={item.id}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="mb-2">
                <p className="font-semibold text-slate-900">Venta #{item.id}</p>
                <p className="text-sm text-slate-600">{item.cliente_nombre || '—'}</p>
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500 mb-3">
                <div>
                  <dt className="inline">Total: </dt>
                  <dd className="inline text-slate-700">{formatearMoneda(item.total)}</dd>
                </div>
                <div>
                  <dt className="inline">Saldo: </dt>
                  <dd className="inline font-medium text-amber-700">
                    {formatearMoneda(item.saldo_pendiente)}
                  </dd>
                </div>
                <div className="col-span-2">
                  <dt className="inline">Estado: </dt>
                  <dd className="inline text-slate-700">{item.estado || '—'}</dd>
                </div>
              </dl>
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
                {!soloLectura ? (
                  <AccionesRenderer acciones={item.acciones} item={item} ventaId={item.id} />
                ) : (
                  <span className="text-xs text-slate-400">Solo lectura</span>
                )}
                <Link
                  to={`/ventas`}
                  className="text-sm text-primary-600 hover:text-primary-700 min-h-[36px] inline-flex items-center touch-manipulation"
                >
                  Ir a ventas
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
