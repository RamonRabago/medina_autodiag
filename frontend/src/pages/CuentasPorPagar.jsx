import { useState, useEffect } from 'react'
import api from '../services/api'
import { useInvalidateQueries } from '../hooks/useApi'

export default function CuentasPorPagar() {
  const invalidate = useInvalidateQueries()
  const [items, setItems] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [totalSaldoPendiente, setTotalSaldoPendiente] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filtroProveedor, setFiltroProveedor] = useState('')
  const [modalPagoAbierto, setModalPagoAbierto] = useState(false)
  const [ordenSeleccionada, setOrdenSeleccionada] = useState(null)
  const [pagoForm, setPagoForm] = useState({ monto: '', metodo: 'EFECTIVO', referencia: '' })
  const [enviandoPago, setEnviandoPago] = useState(false)

  const cargar = async () => {
    setLoading(true)
    try {
      const params = filtroProveedor ? { id_proveedor: filtroProveedor } : {}
      const [rCxC, rProv] = await Promise.all([
        api.get('/ordenes-compra/cuentas-por-pagar', { params }),
        api.get('/proveedores/', { params: { limit: 500 } }),
      ])
      setItems(rCxC.data?.items ?? [])
      setTotalSaldoPendiente(rCxC.data?.total_saldo_pendiente ?? 0)
      setProveedores(rProv.data?.proveedores ?? rProv.data ?? [])
    } catch (err) {
      setItems([])
      setTotalSaldoPendiente(0)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [filtroProveedor])

  const abrirModalPago = (item) => {
    setOrdenSeleccionada(item)
    setPagoForm({
      monto: item?.saldo_pendiente?.toString() ?? '',
      metodo: 'EFECTIVO',
      referencia: '',
    })
    setModalPagoAbierto(true)
  }

  const registrarPago = async () => {
    if (!ordenSeleccionada || !pagoForm.monto || parseFloat(pagoForm.monto) <= 0) return
    const monto = Math.round(parseFloat(pagoForm.monto) * 100) / 100
    const saldo = ordenSeleccionada.saldo_pendiente ?? 0
    if (monto > saldo) {
      alert(`El monto no puede exceder el saldo pendiente ($${saldo.toFixed(2)})`)
      return
    }
    setEnviandoPago(true)
    try {
      await api.post(`/ordenes-compra/${ordenSeleccionada.id_orden_compra}/pagar`, {
        monto,
        metodo: pagoForm.metodo,
        referencia: pagoForm.referencia?.trim() || null,
      })
      invalidate(['ordenes-compra'])
      invalidate(['ordenes-compra-alertas'])
      setModalPagoAbierto(false)
      setOrdenSeleccionada(null)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al registrar pago')
    } finally {
      setEnviandoPago(false)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Cuentas por pagar</h1>
      <p className="text-sm text-slate-600 mb-4">
        Órdenes de compra recibidas con saldo pendiente de pago a proveedores.
      </p>

      <div className="mb-6 flex flex-wrap gap-4 items-center">
        <div className="p-4 bg-amber-50 rounded-lg min-w-[180px]">
          <p className="text-xs text-slate-500">Total saldo pendiente</p>
          <p className="text-xl font-bold text-amber-700">
            ${totalSaldoPendiente.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="p-4 bg-slate-50 rounded-lg min-w-[120px]">
          <p className="text-xs text-slate-500">Cuentas</p>
          <p className="text-xl font-bold">{items.length}</p>
        </div>
        <select
          value={filtroProveedor}
          onChange={(e) => setFiltroProveedor(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Todos los proveedores</option>
          {proveedores.map((p) => (
            <option key={p.id_proveedor} value={p.id_proveedor}>
              {p.nombre}
            </option>
          ))}
        </select>
        <button
          onClick={cargar}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Actualizar
        </button>
        <button
          onClick={async () => {
            try {
              const params = filtroProveedor ? { id_proveedor: filtroProveedor } : {}
              const res = await api.get('/exportaciones/cuentas-por-pagar', { params, responseType: 'blob' })
              const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || 'cuentas_por_pagar.xlsx'
              const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
              const link = document.createElement('a')
              link.href = window.URL.createObjectURL(blob)
              link.download = fn
              link.click()
              window.URL.revokeObjectURL(link.href)
            } catch (err) {
              alert(err.response?.data?.detail || 'Error al exportar')
            }
          }}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
        >
          Exportar a Excel
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {items.length === 0 ? (
          <p className="p-8 text-slate-500 text-center">No hay cuentas por pagar.</p>
        ) : (
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs text-slate-500">Orden</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500">Proveedor</th>
                <th className="px-4 py-3 text-right text-xs text-slate-500">Total a pagar</th>
                <th className="px-4 py-3 text-right text-xs text-slate-500">Pagado</th>
                <th className="px-4 py-3 text-right text-xs text-slate-500">Saldo pendiente</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500">Fecha recepción</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.id_orden_compra}>
                  <td className="px-4 py-2 font-medium">{item.numero}</td>
                  <td className="px-4 py-2">{item.nombre_proveedor}</td>
                  <td className="px-4 py-2 text-right">${(item.total_a_pagar ?? 0).toFixed(2)}</td>
                  <td className="px-4 py-2 text-right">${(item.total_pagado ?? 0).toFixed(2)}</td>
                  <td className="px-4 py-2 text-right font-medium text-amber-700">
                    ${(item.saldo_pendiente ?? 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-sm text-slate-600">
                    {item.fecha_recepcion ? new Date(item.fecha_recepcion).toLocaleDateString('es-MX') : '-'}
                  </td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => abrirModalPago(item)}
                      className="px-3 py-1 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700"
                    >
                      Registrar pago
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modalPagoAbierto && ordenSeleccionada && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold mb-4">Registrar pago</h2>
            <p className="text-sm text-slate-600 mb-2">
              Orden <strong>{ordenSeleccionada.numero}</strong> – {ordenSeleccionada.nombre_proveedor}
            </p>
            <p className="text-sm text-amber-700 font-medium mb-4">
              Saldo pendiente: ${(ordenSeleccionada.saldo_pendiente ?? 0).toFixed(2)}
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Monto</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={pagoForm.monto}
                  onChange={(e) => setPagoForm((f) => ({ ...f, monto: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Método</label>
                <select
                  value={pagoForm.metodo}
                  onChange={(e) => setPagoForm((f) => ({ ...f, metodo: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                >
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="TARJETA">Tarjeta</option>
                  <option value="TRANSFERENCIA">Transferencia</option>
                  <option value="CHEQUE">Cheque</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Referencia (opcional)</label>
                <input
                  type="text"
                  value={pagoForm.referencia}
                  onChange={(e) => setPagoForm((f) => ({ ...f, referencia: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  placeholder="Nº de factura, transferencia..."
                />
              </div>
            </div>
            <div className="mt-6 flex gap-2 justify-end">
              <button
                onClick={() => {
                  setModalPagoAbierto(false)
                  setOrdenSeleccionada(null)
                }}
                className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                onClick={registrarPago}
                disabled={enviandoPago || !pagoForm.monto || parseFloat(pagoForm.monto) <= 0}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
              >
                {enviandoPago ? 'Guardando...' : 'Registrar pago'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
