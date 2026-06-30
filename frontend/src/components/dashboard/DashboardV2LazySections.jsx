import { useState } from 'react'
import DisclosurePanel, { DisclosureChevron } from '../ui/DisclosurePanel'
import DashboardOperativoSection from './DashboardOperativoSection'
import { formatoMoneda } from './dashboardV2Styles'
import { useApiQuery } from '../../hooks/useApi'
import { useOperacionesResumen } from '../../hooks/useOperacionesResumen'
import api from '../../services/api'

/**
 * Acordeones lazy: Operación (A0), Finanzas, Inventario.
 * UX-1A intacto dentro de DashboardOperativoSection.
 */
export default function DashboardV2LazySections({ esAdmin, periodoInicial = 'mes' }) {
  const [operacionOpen, setOperacionOpen] = useState(false)
  const [finanzasOpen, setFinanzasOpen] = useState(false)
  const [inventarioOpen, setInventarioOpen] = useState(false)
  const [periodoFinanzas, setPeriodoFinanzas] = useState(periodoInicial)

  const {
    data: operacionesResumen,
    isLoading: operacionesLoading,
    isError: operacionesError,
  } = useOperacionesResumen(1, { incluirItems: false, enabled: esAdmin && operacionOpen })

  const {
    data: finanzasData,
    isLoading: finanzasLoading,
    isError: finanzasError,
  } = useApiQuery(
    ['dashboard', 'v2', 'finanzas', periodoFinanzas],
    () =>
      api
        .get('/dashboard', { params: { secciones: 'finanzas', periodo: periodoFinanzas } })
        .then((r) => r.data?.finanzas),
    { enabled: esAdmin && finanzasOpen, staleTime: 45 * 1000 }
  )

  const {
    data: inventarioData,
    isLoading: inventarioLoading,
    isError: inventarioError,
  } = useApiQuery(
    ['dashboard', 'v2', 'inventario'],
    () =>
      api.get('/dashboard', { params: { secciones: 'inventario' } }).then((r) => r.data?.inventario),
    { enabled: esAdmin && inventarioOpen, staleTime: 45 * 1000 }
  )

  if (!esAdmin) {
    return null
  }

  return (
    <section className="mt-2 sm:mt-4 space-y-3" aria-labelledby="dashboard-lazy-titulo">
      <h2 id="dashboard-lazy-titulo" className="text-base font-semibold text-slate-800 mb-1">
        Más detalle
      </h2>

      <DisclosurePanel
        id="dashboard-lazy-operacion"
        expanded={operacionOpen}
        onToggle={() => setOperacionOpen((v) => !v)}
        trigger={
          <>
            <span className="text-sm font-semibold text-slate-800">Operación</span>
            <span className="text-xs text-slate-500 hidden sm:inline">Resumen A0 ligero</span>
            <DisclosureChevron expanded={operacionOpen} />
          </>
        }
      >
        <div className="p-4 sm:p-5">
          <DashboardOperativoSection
            data={operacionesResumen}
            isLoading={operacionesLoading}
            isError={operacionesError}
          />
        </div>
      </DisclosurePanel>

      <DisclosurePanel
        id="dashboard-lazy-finanzas"
        expanded={finanzasOpen}
        onToggle={() => setFinanzasOpen((v) => !v)}
        trigger={
          <>
            <span className="text-sm font-semibold text-slate-800">Finanzas</span>
            <span className="text-xs text-slate-500 hidden sm:inline">Ventas, gastos, utilidad</span>
            <DisclosureChevron expanded={finanzasOpen} />
          </>
        }
      >
        <div className="p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
            <p className="text-sm text-slate-600">Periodo</p>
            <select
              value={periodoFinanzas}
              onChange={(e) => setPeriodoFinanzas(e.target.value)}
              className="text-sm border border-slate-200 rounded px-3 py-2 min-h-[44px] sm:min-h-0 text-slate-600 bg-white focus:ring-1 focus:ring-primary-500"
            >
              <option value="mes">Este mes</option>
              <option value="mes_pasado">Mes pasado</option>
              <option value="ano">Este año</option>
              <option value="acumulado">Acumulado</option>
            </select>
          </div>
          {finanzasLoading && (
            <p className="text-sm text-slate-500">Cargando finanzas...</p>
          )}
          {finanzasError && (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
              No se pudieron cargar los datos financieros.
            </p>
          )}
          {finanzasData && !finanzasLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <FinanzaCard label="Ventas del periodo" value={formatoMoneda(finanzasData.total_ventas_periodo)} />
              <FinanzaCard label="Cobrado" value={formatoMoneda(finanzasData.total_facturado)} valueClass="text-emerald-700" />
              <FinanzaCard label="Gastos" value={formatoMoneda(finanzasData.total_gastos)} valueClass="text-red-600" />
              <FinanzaCard
                label="Utilidad neta"
                value={formatoMoneda(finanzasData.utilidad_neta)}
                valueClass={(Number(finanzasData.utilidad_neta) || 0) >= 0 ? 'text-emerald-700' : 'text-red-600'}
              />
              <FinanzaCard
                label="Cuentas por pagar"
                value={formatoMoneda(finanzasData.cuentas_por_pagar?.total_saldo_pendiente)}
                hint={`${finanzasData.cuentas_por_pagar?.total_cuentas ?? 0} cuenta(s)`}
              />
              <FinanzaCard label="Devoluciones del mes" value={finanzasData.devoluciones_mes ?? 0} />
            </div>
          )}
        </div>
      </DisclosurePanel>

      <DisclosurePanel
        id="dashboard-lazy-inventario"
        expanded={inventarioOpen}
        onToggle={() => setInventarioOpen((v) => !v)}
        trigger={
          <>
            <span className="text-sm font-semibold text-slate-800">Inventario</span>
            <span className="text-xs text-slate-500 hidden sm:inline">Stock y alertas</span>
            <DisclosureChevron expanded={inventarioOpen} />
          </>
        }
      >
        <div className="p-4 sm:p-5">
          {inventarioLoading && (
            <p className="text-sm text-slate-500">Cargando inventario...</p>
          )}
          {inventarioError && (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
              No se pudieron cargar los datos de inventario.
            </p>
          )}
          {inventarioData && !inventarioLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <FinanzaCard
                label="Valor inventario"
                value={formatoMoneda(
                  inventarioData.valor_inventario?.valor_compra ?? inventarioData.valor_inventario
                )}
              />
              <FinanzaCard label="Productos activos" value={inventarioData.productos_activos ?? 0} />
              <FinanzaCard
                label="Stock bajo / Sin stock"
                value={`${inventarioData.stock_bajo ?? 0} / ${inventarioData.sin_stock ?? 0}`}
                valueClass="text-amber-600"
              />
              <FinanzaCard
                label="Alertas activas"
                value={inventarioData.total_alertas ?? 0}
                valueClass={(inventarioData.total_alertas ?? 0) > 0 ? 'text-amber-600' : undefined}
              />
              {inventarioData.ordenes_compra_alertas && (
                <FinanzaCard
                  label="OC sin recibir"
                  value={inventarioData.ordenes_compra_alertas.ordenes_sin_recibir ?? 0}
                  hint={
                    (inventarioData.ordenes_compra_alertas.ordenes_vencidas ?? 0) > 0
                      ? `${inventarioData.ordenes_compra_alertas.ordenes_vencidas} vencidas`
                      : undefined
                  }
                />
              )}
            </div>
          )}
        </div>
      </DisclosurePanel>
    </section>
  )
}

function FinanzaCard({ label, value, hint, valueClass = 'text-slate-800' }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3">
      <p className="text-xs text-slate-500 font-medium">{label}</p>
      <p className={`text-lg font-semibold mt-0.5 ${valueClass}`}>{value}</p>
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}
