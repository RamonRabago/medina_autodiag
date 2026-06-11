import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import PageHeader from '../../components/PageHeader'
import PageLoading from '../../components/PageLoading'
import BandejaOtSection from '../../components/operaciones/BandejaOtSection'
import BandejaVentaSection from '../../components/operaciones/BandejaVentaSection'
import AccionesCajaRenderer from '../../components/operaciones/AccionesCajaRenderer'
import FlujoCrearVentaOtModal from '../../components/operaciones/FlujoCrearVentaOtModal'
import FlujoRegistrarPagoModal from '../../components/operaciones/FlujoRegistrarPagoModal'
import FlujoEntregarVehiculoModal from '../../components/operaciones/FlujoEntregarVehiculoModal'
import TurnoCajaBanner from '../../components/operaciones/TurnoCajaBanner'
import { useAuth } from '../../context/AuthContext'
import { RESUMEN_QUERY_KEY, useOperacionesResumen } from '../../hooks/useOperacionesResumen'
import { puedeCajaOperativa } from '../../utils/rolesOperaciones'
import { showError } from '../../utils/toast'

/**
 * Caja Operativa P4.1 — Modo Mostrador.
 * Fase 3: crear venta desde OT vía modal + POST delegado.
 * Fase 4A: registrar pago vía modal + POST /api/pagos/.
 * Fase 4B: entregar vehículo vía modal + POST /api/ordenes-trabajo/{id}/entregar.
 */
export default function CajaOperativa() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, loading: authLoading } = useAuth()
  const { data, isLoading, isError, error, refetch, isFetching } = useOperacionesResumen(30)
  const [otCrearVentaItem, setOtCrearVentaItem] = useState(null)
  const [pagoContext, setPagoContext] = useState(null)
  const [otEntregarItem, setOtEntregarItem] = useState(null)

  useEffect(() => {
    if (!authLoading && user?.rol && !puedeCajaOperativa(user.rol)) {
      navigate('/', { replace: true })
    }
  }, [authLoading, user?.rol, navigate])

  useEffect(() => {
    if (isError && error) {
      showError(error, 'No se pudo cargar Caja Operativa')
    }
  }, [isError, error])

  const invalidarA0 = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: RESUMEN_QUERY_KEY })
    refetch()
  }, [queryClient, refetch])

  const abrirCrearVentaOt = useCallback((item) => {
    setOtCrearVentaItem(item)
  }, [])

  const cerrarCrearVentaOt = useCallback(() => {
    setOtCrearVentaItem(null)
  }, [])

  const handleCrearVentaExito = useCallback(() => {
    invalidarA0()
    setOtCrearVentaItem(null)
  }, [invalidarA0])

  const abrirRegistrarPago = useCallback((item, accion) => {
    setPagoContext({ item, accion })
  }, [])

  const cerrarRegistrarPago = useCallback(() => {
    setPagoContext(null)
  }, [])

  const handleRegistrarPagoExito = useCallback(() => {
    invalidarA0()
    setPagoContext(null)
  }, [invalidarA0])

  const abrirEntregarVehiculo = useCallback((item) => {
    setOtEntregarItem(item)
  }, [])

  const cerrarEntregarVehiculo = useCallback(() => {
    setOtEntregarItem(null)
  }, [])

  const handleEntregarVehiculoExito = useCallback(() => {
    invalidarA0()
    setOtEntregarItem(null)
  }, [invalidarA0])

  const renderAccionesCaja = useCallback(
    (props) => (
      <AccionesCajaRenderer
        {...props}
        onCrearVentaDesdeOt={abrirCrearVentaOt}
        onRegistrarPago={abrirRegistrarPago}
        onEntregarVehiculo={abrirEntregarVehiculo}
      />
    ),
    [abrirCrearVentaOt, abrirRegistrarPago, abrirEntregarVehiculo]
  )

  if (authLoading || (user?.rol && !puedeCajaOperativa(user.rol))) {
    return null
  }

  if (isLoading && !data) {
    return <PageLoading mensaje="Cargando Caja Operativa..." />
  }

  const bandejas = data?.bandejas || {}

  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader
        title="Caja Operativa"
        subtitle="Modo mostrador — cobro y entrega desde bandejas operativas"
      >
        <button
          type="button"
          onClick={() => invalidarA0()}
          disabled={isFetching}
          className="min-h-[44px] px-4 py-2 rounded-xl border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 touch-manipulation disabled:opacity-50"
        >
          {isFetching ? 'Actualizando...' : 'Actualizar'}
        </button>
      </PageHeader>

      <TurnoCajaBanner caja={data?.caja} />

      <BandejaOtSection
        titulo="Por cobrar (OT)"
        total={bandejas.ot_pendientes_cobro?.total ?? 0}
        items={bandejas.ot_pendientes_cobro?.items ?? []}
        vacio="No hay órdenes pendientes de cobro"
        AccionesRenderer={renderAccionesCaja}
      />

      <BandejaOtSection
        titulo="Listas para entrega"
        total={bandejas.ot_listas_entrega?.total ?? 0}
        items={bandejas.ot_listas_entrega?.items ?? []}
        vacio="No hay vehículos listos para entrega"
        AccionesRenderer={renderAccionesCaja}
      />

      <BandejaVentaSection
        titulo="Ventas con saldo (mostrador)"
        total={bandejas.ventas_saldo_pendiente?.total ?? 0}
        items={bandejas.ventas_saldo_pendiente?.items ?? []}
        vacio="No hay ventas de mostrador con saldo pendiente"
        AccionesRenderer={renderAccionesCaja}
      />

      <FlujoCrearVentaOtModal
        item={otCrearVentaItem}
        abierto={!!otCrearVentaItem}
        onCerrar={cerrarCrearVentaOt}
        onExito={handleCrearVentaExito}
        onErrorNegocio={invalidarA0}
      />

      <FlujoRegistrarPagoModal
        item={pagoContext?.item ?? null}
        accionRegistrarPago={pagoContext?.accion ?? null}
        abierto={!!pagoContext}
        onCerrar={cerrarRegistrarPago}
        onExito={handleRegistrarPagoExito}
        onErrorNegocio={invalidarA0}
      />

      <FlujoEntregarVehiculoModal
        item={otEntregarItem}
        abierto={!!otEntregarItem}
        onCerrar={cerrarEntregarVehiculo}
        onExito={handleEntregarVehiculoExito}
        onErrorNegocio={invalidarA0}
      />
    </div>
  )
}
