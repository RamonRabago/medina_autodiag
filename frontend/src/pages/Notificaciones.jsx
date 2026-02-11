import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

const TIPO_LABEL = {
  DIFERENCIA_CIERRE: 'Diferencia en cierre',
  TURNO_LARGO: 'Turno largo sin cerrar',
  STOCK_BAJO: 'Stock bajo',
  STOCK_CRITICO: 'Stock crítico',
  SIN_STOCK: 'Sin stock',
  SIN_MOVIMIENTO: 'Sin movimiento',
  SOBRE_STOCK: 'Sobre stock',
}

const NIVEL_CLASS = {
  CRITICO: 'bg-red-50 border-red-200 text-red-800',
  WARNING: 'bg-amber-50 border-amber-200 text-amber-800',
  INFO: 'bg-slate-50 border-slate-200 text-slate-700',
}

function formatearFecha(s) {
  if (!s) return '-'
  try {
    return new Date(s).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return String(s)
  }
}

export default function Notificaciones() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [alertasCaja, setAlertasCaja] = useState([])
  const [alertasInventario, setAlertasInventario] = useState([])
  const [resumenInventario, setResumenInventario] = useState(null)
  const [ordenesCompra, setOrdenesCompra] = useState(null)
  const [resolviendo, setResolviendo] = useState(null)

  const cargar = async () => {
    setLoading(true)
    setError('')
    const requests = []

    if (user?.rol === 'ADMIN') {
      requests.push({ key: 'caja', promise: api.get('/admin/alertas', { params: { resueltas: false } }) })
    }
    requests.push({ key: 'inventario', promise: api.get('/inventario/alertas', { params: { activas_solo: true, limit: 50 } }) })
    requests.push({ key: 'inventarioResumen', promise: api.get('/inventario/alertas/resumen') })
    if (user?.rol === 'ADMIN' || user?.rol === 'CAJA') {
      requests.push({ key: 'ordenesCompra', promise: api.get('/ordenes-compra/alertas', { params: { limit: 15 } }) })
    }

    const results = await Promise.allSettled(requests.map((r) => r.promise))

    results.forEach((result, i) => {
      const { key } = requests[i]
      if (result.status === 'fulfilled') {
        const data = result.value.data
        if (key === 'caja') setAlertasCaja(Array.isArray(data) ? data : [])
        if (key === 'inventario') setAlertasInventario(Array.isArray(data) ? data : [])
        if (key === 'inventarioResumen') setResumenInventario(data)
        if (key === 'ordenesCompra') setOrdenesCompra(data)
      } else {
        if (key === 'caja' && result.reason?.response?.status === 403) setAlertasCaja([])
        else if (key === 'ordenesCompra' && result.reason?.response?.status === 403) setOrdenesCompra(null)
      }
    })

    setLoading(false)
  }

  useEffect(() => {
    cargar()
  }, [user?.rol])

  const resolverAlertaCaja = async (idAlerta) => {
    setResolviendo(idAlerta)
    try {
      await api.post(`/admin/${idAlerta}/resolver`)
      setAlertasCaja((prev) => prev.filter((a) => a.id_alerta !== idAlerta))
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al resolver')
    } finally {
      setResolviendo(null)
    }
  }

  const resolverAlertaInventario = async (idAlerta) => {
    setResolviendo(idAlerta)
    try {
      await api.post(`/inventario/alertas/${idAlerta}/resolver`)
      setAlertasInventario((prev) => prev.filter((a) => a.id_alerta !== idAlerta))
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al resolver')
    } finally {
      setResolviendo(null)
    }
  }

  const totalAlertas =
    alertasCaja.filter((a) => !a.resuelta).length +
    (alertasInventario?.length || 0) +
    (ordenesCompra?.ordenes_sin_recibir > 0 ? 1 : 0)

  if (loading && totalAlertas === 0) {
    return (
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-6">Notificaciones</h1>
        <p className="text-slate-500">Cargando alertas...</p>
      </div>
    )
  }

  return (
    <div className="min-h-0 flex flex-col">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-2">Notificaciones</h1>
      <p className="text-sm text-slate-500 mb-6">Alertas y notificaciones del sistema</p>

      {error && <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}

      {/* Alertas de Caja (solo ADMIN) */}
      {user?.rol === 'ADMIN' && (
        <section className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              🖥️ Caja
              {alertasCaja.length > 0 && (
                <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">{alertasCaja.length}</span>
              )}
            </h2>
            {alertasCaja.length > 0 && (
              <Link to="/caja" className="min-h-[44px] inline-flex items-center text-sm text-primary-600 hover:text-primary-700 active:text-primary-800 touch-manipulation">
                Ir a Caja →
              </Link>
            )}
          </div>
          <div className="bg-white rounded-lg shadow divide-y divide-slate-100 border border-slate-200">
            {alertasCaja.length === 0 ? (
              <p className="p-4 text-slate-500 text-sm">No hay alertas pendientes de caja</p>
            ) : (
              alertasCaja.map((a) => (
                <div key={a.id_alerta} className={`p-4 border-l-4 ${NIVEL_CLASS[a.nivel] || NIVEL_CLASS.INFO}`}>
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <span className="text-xs font-medium uppercase text-slate-500">{TIPO_LABEL[a.tipo] || a.tipo}</span>
                      <p className="text-slate-800 font-medium mt-0.5">{a.mensaje}</p>
                      <p className="text-xs text-slate-500 mt-1">{formatearFecha(a.fecha_creacion)}</p>
                    </div>
                    <button type="button" onClick={() => resolverAlertaCaja(a.id_alerta)} disabled={resolviendo === a.id_alerta} className="min-h-[44px] px-4 py-2 text-sm bg-white border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 shrink-0 touch-manipulation self-start sm:self-center">
                      {resolviendo === a.id_alerta ? '...' : 'Marcar resuelta'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {/* Alertas de Inventario */}
      <section className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
          <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            📦 Inventario
            {resumenInventario?.total_alertas > 0 && (
              <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">{resumenInventario.total_alertas}</span>
            )}
          </h2>
          {alertasInventario.length > 0 && (
            <Link to="/inventario" className="min-h-[44px] inline-flex items-center text-sm text-primary-600 hover:text-primary-700 active:text-primary-800 touch-manipulation">
              Ir a Inventario →
            </Link>
          )}
        </div>
        <div className="bg-white rounded-lg shadow divide-y divide-slate-100 border border-slate-200">
          {alertasInventario.length === 0 ? (
            <p className="p-4 text-slate-500 text-sm">No hay alertas de stock activas</p>
          ) : (
            alertasInventario.map((a) => (
              <div key={a.id_alerta} className={`p-4 border-l-4 ${a.tipo_alerta === 'SIN_STOCK' || a.tipo_alerta === 'STOCK_CRITICO' ? 'bg-red-50 border-red-300' : a.tipo_alerta === 'STOCK_BAJO' ? 'bg-amber-50 border-amber-300' : 'bg-slate-50 border-slate-200'}`}>
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-medium uppercase text-slate-500">{TIPO_LABEL[a.tipo_alerta] || a.tipo_alerta}</span>
                    <p className="text-slate-800 font-medium mt-0.5">{a.mensaje}</p>
                    {a.repuesto && (
                      <Link to={`/inventario/kardex/${a.id_repuesto}`} className="text-sm text-primary-600 hover:text-primary-700 active:text-primary-800 mt-1 inline-block min-h-[36px] py-1 touch-manipulation">
                        {a.repuesto.codigo} – {a.repuesto.nombre}
                      </Link>
                    )}
                    <p className="text-xs text-slate-500 mt-1">{formatearFecha(a.fecha_creacion)}</p>
                  </div>
                  {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (
                    <button type="button" onClick={() => resolverAlertaInventario(a.id_alerta)} disabled={resolviendo === a.id_alerta} className="min-h-[44px] px-4 py-2 text-sm bg-white border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 disabled:opacity-50 shrink-0 touch-manipulation self-start sm:self-center">
                      {resolviendo === a.id_alerta ? '...' : 'Marcar resuelta'}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Ordenes de compra pendientes */}
      {(user?.rol === 'ADMIN' || user?.rol === 'CAJA') && (
        <section className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
            <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              🛒 Ordenes de compra
              {ordenesCompra?.ordenes_sin_recibir > 0 && (
                <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">{ordenesCompra.ordenes_sin_recibir} pendientes</span>
              )}
            </h2>
            {ordenesCompra?.ordenes_sin_recibir > 0 && (
              <Link to="/ordenes-compra" className="min-h-[44px] inline-flex items-center text-sm text-primary-600 hover:text-primary-700 active:text-primary-800 touch-manipulation">
                Ir a Ordenes de compra →
              </Link>
            )}
          </div>
          <div className="bg-white rounded-lg shadow divide-y divide-slate-100 border border-slate-200">
            {!ordenesCompra ? (
              <p className="p-4 text-slate-500 text-sm">No se pudo cargar</p>
            ) : !ordenesCompra.items?.length ? (
              <p className="p-4 text-slate-500 text-sm">No hay ordenes pendientes de recibir</p>
            ) : (
              ordenesCompra.items.map((oc) => (
                <div key={oc.id_orden_compra} className={`p-4 border-l-4 ${oc.vencida ? 'bg-red-50 border-red-300' : 'bg-slate-50 border-slate-200'}`}>
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <span className="text-xs font-medium uppercase text-slate-500">{oc.vencida ? 'Vencida' : 'Pendiente'}</span>
                      <p className="text-slate-800 font-medium mt-0.5">Orden #{oc.numero} – {oc.nombre_proveedor}</p>
                      <p className="text-sm text-slate-600">Entrega estimada: {oc.fecha_estimada_entrega || 'Sin fecha'}{oc.vencida && ' (vencida)'}</p>
                    </div>
                    <Link to={`/ordenes-compra/editar/${oc.id_orden_compra}`} className="min-h-[44px] inline-flex items-center px-4 py-2 text-sm bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200 active:bg-primary-300 shrink-0 touch-manipulation self-start sm:self-center">
                      Ver orden
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      {totalAlertas === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-8 sm:p-12 text-center text-slate-500 border border-slate-200">
          <p className="text-lg">No hay alertas pendientes</p>
          <p className="text-sm mt-2">El sistema mostrará aquí las notificaciones cuando existan.</p>
        </div>
      )}
    </div>
  )
}
