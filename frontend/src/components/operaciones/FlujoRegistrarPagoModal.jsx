import { useEffect, useMemo, useState } from 'react'
import Modal from '../Modal'
import api from '../../services/api'
import { debeRefetchA0TrasError, ejecutarRegistrarPago } from '../../utils/accionesCajaApi'
import { showError, showSuccess } from '../../utils/toast'

const METODOS_PAGO = [
  { value: 'EFECTIVO', label: 'Efectivo' },
  { value: 'TARJETA', label: 'Tarjeta' },
  { value: 'TRANSFERENCIA', label: 'Transferencia' },
]

function formatearMoneda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '—'
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(valor))
}

/** Resuelve id_venta y saldo desde contexto A0 + ítem (O1 o V1). */
export function datosPagoDesdeA0(item, accionRegistrarPago) {
  const ctx = accionRegistrarPago?.contexto || {}
  const idVenta =
    ctx.id_venta ??
    item?.id_venta ??
    (item?.tipo_entidad === 'venta' ? item?.id : null)
  const saldo = ctx.saldo_pendiente ?? item?.saldo_pendiente
  return { idVenta, saldo }
}

function tituloModal(item) {
  if (item?.tipo_entidad === 'venta') {
    return `Registrar pago — Venta #${item.id}`
  }
  return `Registrar pago — ${item?.numero_orden || `OT #${item?.id}`}`
}

/**
 * Fase 4A — Registrar pago delegado a POST /api/pagos/.
 * Permisos y saldo vienen de acciones[] A0; sin lógica local de autorización.
 */
export default function FlujoRegistrarPagoModal({
  item,
  accionRegistrarPago,
  abierto,
  onCerrar,
  onExito,
  onErrorNegocio,
}) {
  const { idVenta, saldo } = useMemo(
    () => datosPagoDesdeA0(item, accionRegistrarPago),
    [item, accionRegistrarPago]
  )

  const [monto, setMonto] = useState('')
  const [metodo, setMetodo] = useState('EFECTIVO')
  const [referencia, setReferencia] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (abierto && saldo != null) {
      setMonto(String(Number(saldo)))
      setMetodo('EFECTIVO')
      setReferencia('')
      setEnviando(false)
    }
  }, [abierto, item?.id, idVenta, saldo])

  const cerrar = () => {
    if (enviando) return
    onCerrar?.()
  }

  const montoNum = Number(monto)
  const montoValido =
    monto !== '' && !Number.isNaN(montoNum) && montoNum > 0 && (saldo == null || montoNum <= saldo + 0.001)

  const confirmar = async () => {
    if (!idVenta || !montoValido || enviando) return
    setEnviando(true)
    try {
      const res = await ejecutarRegistrarPago(api, {
        id_venta: idVenta,
        metodo,
        monto: montoNum,
        referencia: referencia.trim() || undefined,
      })
      const estado = res.data?.estado_venta
      showSuccess(
        estado?.toUpperCase() === 'PAGADA'
          ? `Pago registrado — venta liquidada (${formatearMoneda(montoNum)})`
          : `Pago registrado — ${formatearMoneda(montoNum)}`
      )
      onExito?.(res.data)
    } catch (err) {
      showError(err, 'No se pudo registrar el pago')
      if (debeRefetchA0TrasError(err)) {
        onErrorNegocio?.()
      }
    } finally {
      setEnviando(false)
    }
  }

  if (!item) return null

  return (
    <Modal titulo={tituloModal(item)} abierto={abierto} onCerrar={cerrar}>
      <div className="space-y-4">
        <div className="text-sm text-slate-600 space-y-1">
          <p>{item.cliente_nombre || '—'}</p>
          {item.vehiculo_resumen && <p>{item.vehiculo_resumen}</p>}
          {idVenta != null && (
            <p className="text-slate-700">
              Venta #{idVenta}
              {saldo != null && ` — Saldo pendiente: ${formatearMoneda(saldo)}`}
            </p>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Monto <span className="text-red-600">*</span>
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={saldo ?? undefined}
              value={monto}
              onChange={(e) => setMonto(e.target.value)}
              disabled={enviando}
              className="w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm touch-manipulation disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Método</label>
            <select
              value={metodo}
              onChange={(e) => setMetodo(e.target.value)}
              disabled={enviando}
              className="w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm touch-manipulation disabled:opacity-50"
            >
              {METODOS_PAGO.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Referencia (opc.)</label>
            <input
              type="text"
              value={referencia}
              onChange={(e) => setReferencia(e.target.value)}
              disabled={enviando}
              placeholder="Opcional"
              className="w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm touch-manipulation disabled:opacity-50"
            />
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={cerrar}
            disabled={enviando}
            className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 touch-manipulation disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={confirmar}
            disabled={enviando || !montoValido}
            className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 touch-manipulation disabled:opacity-50"
          >
            {enviando ? 'Registrando...' : 'Confirmar pago'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
