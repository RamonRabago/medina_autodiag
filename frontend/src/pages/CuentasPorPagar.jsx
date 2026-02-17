import { useState, useEffect, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { useInvalidateQueries } from '../hooks/useApi'
import { formatearFechaSolo, formatearFechaHora } from '../utils/fechas'
import { aNumero, esNumeroValido } from '../utils/numeros'
import { showError } from '../utils/toast'

export default function CuentasPorPagar() {
  const invalidate = useInvalidateQueries()
  const [items, setItems] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [totalSaldoPendiente, setTotalSaldoPendiente] = useState(0)
  const [aging, setAging] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filtroProveedor, setFiltroProveedor] = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [modalPagoAbierto, setModalPagoAbierto] = useState(false)
  const [ordenSeleccionada, setOrdenSeleccionada] = useState(null)
  const [pagoForm, setPagoForm] = useState({ monto: '', metodo: 'EFECTIVO', referencia: '' })
  const [enviandoPago, setEnviandoPago] = useState(false)
  const [modalHistorialAbierto, setModalHistorialAbierto] = useState(false)
  const [historialOrden, setHistorialOrden] = useState(null)
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [ordenPor, setOrdenPor] = useState('fecha')
  const [ordenDir, setOrdenDir] = useState('desc')
  const [exportando, setExportando] = useState(false)
  // Cuentas manuales
  const [itemsManuales, setItemsManuales] = useState([])
  const [totalSaldoManual, setTotalSaldoManual] = useState(0)
  const [modalNuevaCuenta, setModalNuevaCuenta] = useState(false)
  const [modalPagoManual, setModalPagoManual] = useState(false)
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(null)
  const [modalHistorialManual, setModalHistorialManual] = useState(false)
  const [historialCuenta, setHistorialCuenta] = useState(null)
  const [cargandoHistorialManual, setCargandoHistorialManual] = useState(false)
  const [formNuevaCuenta, setFormNuevaCuenta] = useState({ concepto: '', id_proveedor: '', acreedor_nombre: '', referencia_factura: '', monto_total: '', fecha_vencimiento: '' })
  const [enviandoCuenta, setEnviandoCuenta] = useState(false)
  const [agingManual, setAgingManual] = useState(null)
  const [searchParams] = useSearchParams()
  const tabInicial = searchParams.get('tab') === 'manuales' ? 'manuales' : 'oc'
  const [tab, setTab] = useState(tabInicial)
  const [pagoFormManual, setPagoFormManual] = useState({ monto: '', metodo: 'EFECTIVO', referencia: '' })
  const [enviandoPagoManual, setEnviandoPagoManual] = useState(false)
  const [ordenPorManual, setOrdenPorManual] = useState('fecha')
  const [ordenDirManual, setOrdenDirManual] = useState('desc')
  const [incluirSaldadasManual, setIncluirSaldadasManual] = useState(false)

  const toggleOrden = (col) => {
    if (ordenPor === col) setOrdenDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setOrdenPor(col); setOrdenDir(col === 'saldo' || col === 'antiguedad' ? 'desc' : col === 'fecha' ? 'desc' : 'asc') }
  }
  const ThSort = ({ col, label, right }) => (
    <th className={`px-2 sm:px-4 py-3 text-xs font-medium text-slate-500 uppercase cursor-pointer hover:bg-slate-100 active:bg-slate-200 select-none min-h-[44px] touch-manipulation ${right ? 'text-right' : 'text-left'}`} onClick={() => toggleOrden(col)}>
      <span className={`flex items-center gap-1 ${right ? 'justify-end' : ''}`}>{label}{ordenPor === col && <span>{ordenDir === 'asc' ? '▲' : '▼'}</span>}</span>
    </th>
  )
  const toggleOrdenManual = (col) => {
    if (ordenPorManual === col) setOrdenDirManual((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setOrdenPorManual(col); setOrdenDirManual(col === 'saldo' || col === 'antiguedad' ? 'desc' : col === 'fecha' ? 'desc' : 'asc') }
  }
  const ThSortManual = ({ col, label, right }) => (
    <th className={`px-2 sm:px-4 py-3 text-xs font-medium text-slate-500 uppercase cursor-pointer hover:bg-slate-100 active:bg-slate-200 select-none min-h-[44px] touch-manipulation ${right ? 'text-right' : 'text-left'}`} onClick={() => toggleOrdenManual(col)}>
      <span className={`flex items-center gap-1 ${right ? 'justify-end' : ''}`}>{label}{ordenPorManual === col && <span>{ordenDirManual === 'asc' ? '▲' : '▼'}</span>}</span>
    </th>
  )

  const abrirModalHistorial = (item) => {
    setHistorialOrden(null)
    setModalHistorialAbierto(true)
    setCargandoHistorial(true)
    api.get(`/ordenes-compra/${item.id_orden_compra}`)
      .then((r) => setHistorialOrden(r.data))
      .catch((err) => { showError(err, 'Error al cargar historial'); setHistorialOrden(null) })
      .finally(() => setCargandoHistorial(false))
  }

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const params = { orden_por: ordenPor, direccion: ordenDir }
      if (filtroProveedor) params.id_proveedor = filtroProveedor
      if (fechaDesde) params.fecha_desde = fechaDesde
      if (fechaHasta) params.fecha_hasta = fechaHasta
      const paramsManual = { orden_por: ordenPorManual, direccion: ordenDirManual }
      if (filtroProveedor) paramsManual.id_proveedor = filtroProveedor
      if (fechaDesde) paramsManual.fecha_desde = fechaDesde
      if (fechaHasta) paramsManual.fecha_hasta = fechaHasta
      if (incluirSaldadasManual) paramsManual.incluir_saldadas = true
      const [rCxC, rProv, rManual] = await Promise.all([
        api.get('/ordenes-compra/cuentas-por-pagar', { params }),
        api.get('/proveedores/', { params: { limit: 500 } }),
        api.get('/cuentas-pagar-manuales', { params: paramsManual }),
      ])
      setItems(rCxC.data?.items ?? [])
      setTotalSaldoPendiente(rCxC.data?.total_saldo_pendiente ?? 0)
      setAging(rCxC.data?.aging ?? null)
      setProveedores(rProv.data?.proveedores ?? rProv.data ?? [])
      setItemsManuales(rManual.data?.items ?? [])
      setTotalSaldoManual(rManual.data?.total_saldo_pendiente ?? 0)
      setAgingManual(rManual.data?.aging ?? null)
    } catch (err) {
      showError(err, 'Error al cargar cuentas por pagar')
      setItems([])
      setTotalSaldoPendiente(0)
    } finally {
      setLoading(false)
    }
  }, [filtroProveedor, fechaDesde, fechaHasta, ordenPor, ordenDir, ordenPorManual, ordenDirManual, incluirSaldadasManual])

  useEffect(() => { cargar() }, [cargar])

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
    if (!ordenSeleccionada || !esNumeroValido(pagoForm.monto) || aNumero(pagoForm.monto) <= 0) return
    const monto = Math.round(aNumero(pagoForm.monto) * 100) / 100
    const saldo = ordenSeleccionada.saldo_pendiente ?? 0
    if (monto > saldo) {
      showError(`El monto no puede exceder el saldo pendiente ($${saldo.toFixed(2)})`)
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
      showError(err, 'Error al registrar pago')
    } finally {
      setEnviandoPago(false)
    }
  }

  const abrirModalHistorialManual = (item) => {
    setHistorialCuenta(null)
    setModalHistorialManual(true)
    setCargandoHistorialManual(true)
    api.get(`/cuentas-pagar-manuales/${item.id_cuenta}`)
      .then((r) => setHistorialCuenta(r.data))
      .catch((err) => { showError(err, 'Error al cargar historial'); setHistorialCuenta(null) })
      .finally(() => setCargandoHistorialManual(false))
  }
  const abrirModalPagoManual = (item) => {
    setCuentaSeleccionada(item)
    setPagoFormManual({ monto: item?.saldo_pendiente?.toString() ?? '', metodo: 'EFECTIVO', referencia: '' })
    setModalPagoManual(true)
  }
  const registrarPagoManual = async () => {
    if (!cuentaSeleccionada || !esNumeroValido(pagoFormManual.monto) || aNumero(pagoFormManual.monto) <= 0) return
    const monto = Math.round(aNumero(pagoFormManual.monto) * 100) / 100
    const saldo = cuentaSeleccionada.saldo_pendiente ?? 0
    if (monto > saldo) {
      showError(`El monto no puede exceder el saldo pendiente ($${saldo.toFixed(2)})`)
      return
    }
    setEnviandoPagoManual(true)
    try {
      await api.post(`/cuentas-pagar-manuales/${cuentaSeleccionada.id_cuenta}/pagar`, {
        monto,
        metodo: pagoFormManual.metodo,
        referencia: pagoFormManual.referencia?.trim() || null,
      })
      invalidate(['cuentas-pagar-manuales'])
      setModalPagoManual(false)
      setCuentaSeleccionada(null)
      cargar()
    } catch (err) {
      showError(err, 'Error al registrar pago')
    } finally {
      setEnviandoPagoManual(false)
    }
  }
  const crearCuentaManual = async () => {
    if (!formNuevaCuenta.concepto?.trim()) { showError('Concepto requerido'); return }
    if (!esNumeroValido(formNuevaCuenta.monto_total) || aNumero(formNuevaCuenta.monto_total) <= 0) { showError('Monto total debe ser un número mayor a 0'); return }
    if (!formNuevaCuenta.id_proveedor && !formNuevaCuenta.acreedor_nombre?.trim()) { showError('Indique proveedor o nombre del acreedor'); return }
    setEnviandoCuenta(true)
    try {
      await api.post('/cuentas-pagar-manuales', {
        concepto: formNuevaCuenta.concepto.trim(),
        id_proveedor: formNuevaCuenta.id_proveedor || null,
        acreedor_nombre: formNuevaCuenta.acreedor_nombre?.trim() || null,
        referencia_factura: formNuevaCuenta.referencia_factura?.trim() || null,
        monto_total: aNumero(formNuevaCuenta.monto_total),
        fecha_vencimiento: formNuevaCuenta.fecha_vencimiento || null,
      })
      invalidate(['cuentas-pagar-manuales'])
      setModalNuevaCuenta(false)
      setFormNuevaCuenta({ concepto: '', id_proveedor: '', acreedor_nombre: '', referencia_factura: '', monto_total: '', fecha_vencimiento: '' })
      cargar()
    } catch (err) {
      showError(err, 'Error al crear cuenta')
    } finally {
      setEnviandoCuenta(false)
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  const totalGeneral = totalSaldoPendiente + (totalSaldoManual ?? 0)
  const agingActivo = tab === 'oc' ? aging : agingManual

  return (
    <div className="min-h-0 flex flex-col">
      <h1 className="text-xl sm:text-2xl font-bold text-slate-800 mb-4">Cuentas por pagar</h1>
      <p className="text-sm text-slate-600 mb-4">Saldos pendientes de pago: ordenes de compra recibidas y facturas manuales (renta, servicios, etc.).</p>

      <div className="flex gap-2 mb-6 border-b border-slate-200 overflow-x-auto">
        <button type="button" onClick={() => setTab('oc')} className={`min-h-[44px] px-4 py-2 text-sm font-medium rounded-t-lg shrink-0 touch-manipulation ${tab === 'oc' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'}`}>
          Por OC ({items.length})
        </button>
        <button type="button" onClick={() => setTab('manuales')} className={`min-h-[44px] px-4 py-2 text-sm font-medium rounded-t-lg shrink-0 touch-manipulation ${tab === 'manuales' ? 'bg-white border border-slate-200 border-b-0 -mb-px text-primary-600' : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'}`}>
          Manuales ({itemsManuales.length})
        </button>
      </div>

      <div className="mb-6 flex flex-wrap gap-4 items-center">
        <div className="p-4 bg-amber-50 rounded-lg min-w-[180px]">
          <p className="text-xs text-slate-500">Total saldo pendiente</p>
          <p className="text-xl font-bold text-amber-700">
            ${totalGeneral.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="p-4 bg-slate-50 rounded-lg min-w-[120px]">
          <p className="text-xs text-slate-500">{tab === 'oc' ? 'Cuentas OC' : 'Cuentas manuales'}</p>
          <p className="text-xl font-bold">{tab === 'oc' ? items.length : itemsManuales.length}</p>
        </div>
        {agingActivo && (
          <>
            <div className="p-4 bg-green-50 rounded-lg min-w-[140px]">
              <p className="text-xs text-slate-500">0-30 días</p>
              <p className="text-lg font-bold text-green-700">${(agingActivo["0_30"]?.total_saldo ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
              <p className="text-xs text-slate-600">{agingActivo["0_30"]?.count ?? 0} cuenta(s)</p>
            </div>
            <div className="p-4 bg-amber-50 rounded-lg min-w-[140px]">
              <p className="text-xs text-slate-500">31-60 días</p>
              <p className="text-lg font-bold text-amber-700">${(agingActivo["31_60"]?.total_saldo ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
              <p className="text-xs text-slate-600">{agingActivo["31_60"]?.count ?? 0} cuenta(s)</p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg min-w-[140px]">
              <p className="text-xs text-slate-500">Más de 60 días</p>
              <p className="text-lg font-bold text-red-700">${(agingActivo["61_mas"]?.total_saldo ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p>
              <p className="text-xs text-slate-600">{agingActivo["61_mas"]?.count ?? 0} cuenta(s)</p>
            </div>
          </>
        )}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Desde</label>
          <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Hasta</label>
          <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Proveedor</label>
          <select value={filtroProveedor} onChange={(e) => setFiltroProveedor(e.target.value)} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation min-w-[140px]">
            <option value="">Todos</option>
            {proveedores.map((p) => (
              <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
            ))}
          </select>
        </div>
        {tab === 'manuales' && (
          <>
            <label className="flex items-center gap-2 text-sm text-slate-600 min-h-[44px] touch-manipulation cursor-pointer">
              <input type="checkbox" checked={incluirSaldadasManual} onChange={(e) => setIncluirSaldadasManual(e.target.checked)} className="rounded w-5 h-5" />
              Incluir saldadas
            </label>
            <button type="button" onClick={() => setModalNuevaCuenta(true)} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 touch-manipulation">
              Nueva cuenta
            </button>
          </>
        )}
        <button type="button" onClick={cargar} className="min-h-[44px] px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 active:bg-slate-800 touch-manipulation">
          Actualizar
        </button>
        <button
          type="button"
          onClick={async () => {
            if (exportando) return
            setExportando(true)
            try {
              const params = {}
              if (filtroProveedor) params.id_proveedor = filtroProveedor
              if (fechaDesde) params.fecha_desde = fechaDesde
              if (fechaHasta) params.fecha_hasta = fechaHasta
              const endpoint = tab === 'manuales' ? '/exportaciones/cuentas-pagar-manuales' : '/exportaciones/cuentas-por-pagar'
              const res = await api.get(endpoint, { params, responseType: 'blob' })
              const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || (tab === 'manuales' ? 'cuentas_pagar_manuales.xlsx' : 'cuentas_por_pagar.xlsx')
              const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
              const link = document.createElement('a')
              link.href = window.URL.createObjectURL(blob)
              link.download = fn
              link.click()
              window.URL.revokeObjectURL(link.href)
            } catch (err) {
              showError(err, 'Error al exportar')
            } finally {
              setExportando(false)
            }
          }}
          disabled={exportando}
          className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 disabled:opacity-60 disabled:cursor-not-allowed touch-manipulation"
        >
          {exportando ? 'Exportando...' : 'Exportar'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden border border-slate-200 flex-1 min-h-0">
        {tab === 'oc' && (
          items.length === 0 ? (
            <p className="p-8 text-slate-500 text-center">No hay cuentas por pagar de ordenes de compra.</p>
          ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-2 sm:px-4 py-3 text-left text-xs text-slate-500">Orden</th>
                  <ThSort col="proveedor" label="Proveedor" />
                  <th className="px-2 sm:px-4 py-3 text-right text-xs text-slate-500">Total</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs text-slate-500">Pagado</th>
                  <ThSort col="saldo" label="Saldo" right />
                  <ThSort col="fecha" label="Fecha" />
                  <ThSort col="antiguedad" label="Antigüedad" />
                  <th className="px-2 sm:px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id_orden_compra}>
                    <td className="px-2 sm:px-4 py-2 font-medium">
                      <Link to={`/ordenes-compra/editar/${item.id_orden_compra}`} className="text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded touch-manipulation py-1">
                        {item.numero}
                      </Link>
                    </td>
                    <td className="px-2 sm:px-4 py-2">{item.nombre_proveedor}</td>
                    <td className="px-2 sm:px-4 py-2 text-right">${(item.total_a_pagar ?? 0).toFixed(2)}</td>
                    <td className="px-2 sm:px-4 py-2 text-right">${(item.total_pagado ?? 0).toFixed(2)}</td>
                    <td className="px-2 sm:px-4 py-2 text-right font-medium text-amber-700">${(item.saldo_pendiente ?? 0).toFixed(2)}</td>
                    <td className="px-2 sm:px-4 py-2 text-sm text-slate-600">{formatearFechaSolo(item.fecha_recepcion)}</td>
                    <td className="px-2 sm:px-4 py-2">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${item.antiguedad_rango === '0-30' ? 'bg-green-100 text-green-800' : item.antiguedad_rango === '31-60' ? 'bg-amber-100 text-amber-800' : item.antiguedad_rango === '61+' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600'}`}>
                        {item.dias_desde_recepcion != null ? `${item.dias_desde_recepcion} días` : item.antiguedad_rango || '-'}
                      </span>
                    </td>
                    <td className="px-2 sm:px-4 py-2">
                      <div className="flex gap-2 flex-wrap">
                        <button type="button" onClick={() => abrirModalHistorial(item)} className="min-h-[36px] px-3 py-1.5 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Historial</button>
                        <Link to={`/ordenes-compra/editar/${item.id_orden_compra}`} className="min-h-[36px] px-3 py-1.5 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 active:bg-slate-100 inline-flex items-center touch-manipulation">Ver orden</Link>
                        <button type="button" onClick={() => abrirModalPago(item)} className="min-h-[36px] px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 active:bg-emerald-800 touch-manipulation">Pagar</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )
        )}
        {tab === 'manuales' && (
          itemsManuales.length === 0 ? (
            <p className="p-8 text-slate-500 text-center">No hay cuentas por pagar manuales. Use &quot;Nueva cuenta&quot; para facturas, renta, servicios, etc.</p>
          ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-2 sm:px-4 py-3 text-left text-xs text-slate-500">Concepto</th>
                  <ThSortManual col="proveedor" label="Acreedor" />
                  <th className="px-2 sm:px-4 py-3 text-left text-xs text-slate-500">Ref.</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs text-slate-500">Total</th>
                  <th className="px-2 sm:px-4 py-3 text-right text-xs text-slate-500">Pagado</th>
                  <ThSortManual col="saldo" label="Saldo" right />
                  <ThSortManual col="fecha" label="Venc." />
                  <ThSortManual col="antiguedad" label="Antigüedad" />
                  <th className="px-2 sm:px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {itemsManuales.map((item) => (
                  <tr key={item.id_cuenta}>
                    <td className="px-2 sm:px-4 py-2 font-medium">{item.concepto}</td>
                    <td className="px-2 sm:px-4 py-2">{item.nombre_acreedor || '-'}</td>
                    <td className="px-2 sm:px-4 py-2 text-sm text-slate-600">{item.referencia_factura || '-'}</td>
                    <td className="px-2 sm:px-4 py-2 text-right">${(item.monto_total ?? 0).toFixed(2)}</td>
                    <td className="px-2 sm:px-4 py-2 text-right">${(item.total_pagado ?? 0).toFixed(2)}</td>
                    <td className="px-2 sm:px-4 py-2 text-right font-medium text-amber-700">${(item.saldo_pendiente ?? 0).toFixed(2)}</td>
                    <td className="px-2 sm:px-4 py-2 text-sm text-slate-600">{formatearFechaSolo(item.fecha_vencimiento)}</td>
                    <td className="px-2 sm:px-4 py-2">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${item.antiguedad_rango === '0-30' ? 'bg-green-100 text-green-800' : item.antiguedad_rango === '31-60' ? 'bg-amber-100 text-amber-800' : item.antiguedad_rango === '61+' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600'}`}>
                        {item.dias_desde_registro != null ? `${item.dias_desde_registro} días` : item.antiguedad_rango || '-'}
                      </span>
                    </td>
                    <td className="px-2 sm:px-4 py-2">
                      <div className="flex gap-2 flex-wrap">
                        <button type="button" onClick={() => abrirModalHistorialManual(item)} className="min-h-[36px] px-3 py-1.5 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Historial</button>
                        <button type="button" onClick={() => abrirModalPagoManual(item)} className="min-h-[36px] px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 active:bg-emerald-800 touch-manipulation">Pagar</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )
        )}
      </div>

      {modalNuevaCuenta && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-auto">
            <h2 className="text-lg font-semibold mb-4">Nueva cuenta por pagar</h2>
            <p className="text-sm text-slate-600 mb-4">Facturas, renta, servicios u otros gastos sin orden de compra.</p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-600 mb-1">Concepto *</label>
                <input type="text" value={formNuevaCuenta.concepto} onChange={(e) => setFormNuevaCuenta((f) => ({ ...f, concepto: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" placeholder="Ej. Renta enero, Luz" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Proveedor (opcional)</label>
                <select value={formNuevaCuenta.id_proveedor} onChange={(e) => setFormNuevaCuenta((f) => ({ ...f, id_proveedor: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
                  <option value="">-- Sin proveedor --</option>
                  {proveedores.map((p) => <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Nombre acreedor (si no hay proveedor)</label>
                <input type="text" value={formNuevaCuenta.acreedor_nombre} onChange={(e) => setFormNuevaCuenta((f) => ({ ...f, acreedor_nombre: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" placeholder="CFE, arrendador, etc." />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Referencia / Nº factura (opcional)</label>
                <input type="text" value={formNuevaCuenta.referencia_factura} onChange={(e) => setFormNuevaCuenta((f) => ({ ...f, referencia_factura: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" placeholder="Nº factura" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Monto total *</label>
                <input type="number" step="0.01" min="0" value={formNuevaCuenta.monto_total} onChange={(e) => setFormNuevaCuenta((f) => ({ ...f, monto_total: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Fecha vencimiento (opcional)</label>
                <input type="date" value={formNuevaCuenta.fecha_vencimiento} onChange={(e) => setFormNuevaCuenta((f) => ({ ...f, fecha_vencimiento: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-2 justify-end">
              <button type="button" onClick={() => { setModalNuevaCuenta(false); setFormNuevaCuenta({ concepto: '', id_proveedor: '', acreedor_nombre: '', referencia_factura: '', monto_total: '', fecha_vencimiento: '' }) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
              <button type="button" onClick={crearCuentaManual} disabled={enviandoCuenta || !formNuevaCuenta.concepto?.trim() || !esNumeroValido(formNuevaCuenta.monto_total) || aNumero(formNuevaCuenta.monto_total) <= 0} className="min-h-[44px] px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-50 touch-manipulation">{enviandoCuenta ? 'Guardando...' : 'Crear cuenta'}</button>
            </div>
          </div>
        </div>
      )}

      {modalHistorialManual && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-lg w-full mx-4 max-h-[85vh] overflow-auto">
            <h2 className="text-lg font-semibold mb-4">Historial de pagos</h2>
            {cargandoHistorialManual ? <p className="text-slate-500 py-4">Cargando...</p> : historialCuenta ? (
              <>
                <p className="text-sm text-slate-600 mb-2">{historialCuenta.concepto}</p>
                <p className="text-sm text-slate-600 mb-4">{historialCuenta.nombre_acreedor || '-'}{historialCuenta.referencia_factura ? ` · Ref: ${historialCuenta.referencia_factura}` : ''}</p>
                <p className="text-sm text-amber-700 font-medium mb-4">Total: ${(historialCuenta.monto_total ?? 0).toFixed(2)} · Pagado: ${(historialCuenta.total_pagado ?? 0).toFixed(2)} · Saldo: ${(historialCuenta.saldo_pendiente ?? 0).toFixed(2)}</p>
                {historialCuenta.pagos?.length > 0 ? (
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50"><tr><th className="px-4 py-2 text-left text-slate-500">Fecha</th><th className="px-4 py-2 text-right text-slate-500">Monto</th><th className="px-4 py-2 text-left text-slate-500">Método</th><th className="px-4 py-2 text-left text-slate-500">Referencia</th></tr></thead>
                    <tbody className="divide-y divide-slate-100">
                      {historialCuenta.pagos.map((p) => <tr key={p.id_pago}><td className="px-4 py-2">{formatearFechaHora(p.fecha)}</td><td className="px-4 py-2 text-right font-medium">${(p.monto || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td><td className="px-4 py-2">{p.metodo}</td><td className="px-4 py-2 text-slate-600">{p.referencia || '-'}</td></tr>)}
                    </tbody>
                  </table>
                ) : <p className="text-slate-500 py-4">Aún no hay pagos registrados.</p>}
              </>
            ) : <p className="text-slate-500 py-4">No se pudo cargar.</p>}
            <div className="mt-4 flex justify-end"><button type="button" onClick={() => setModalHistorialManual(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cerrar</button></div>
          </div>
        </div>
      )}

      {modalPagoManual && cuentaSeleccionada && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold mb-4">Registrar pago</h2>
            <p className="text-sm text-slate-600 mb-2">{cuentaSeleccionada.concepto} – {cuentaSeleccionada.nombre_acreedor || '-'}</p>
            <p className="text-sm text-amber-700 font-medium mb-4">Saldo pendiente: ${(cuentaSeleccionada.saldo_pendiente ?? 0).toFixed(2)}</p>
            <div className="space-y-3">
              <div><label className="block text-sm text-slate-600 mb-1">Monto</label><input type="number" step="0.01" min="0" value={pagoFormManual.monto} onChange={(e) => setPagoFormManual((f) => ({ ...f, monto: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" /></div>
              <div><label className="block text-sm text-slate-600 mb-1">Método</label><select value={pagoFormManual.metodo} onChange={(e) => setPagoFormManual((f) => ({ ...f, metodo: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation"><option value="EFECTIVO">Efectivo</option><option value="TARJETA">Tarjeta</option><option value="TRANSFERENCIA">Transferencia</option><option value="CHEQUE">Cheque</option></select></div>
              <div><label className="block text-sm text-slate-600 mb-1">Referencia (opcional)</label><input type="text" value={pagoFormManual.referencia} onChange={(e) => setPagoFormManual((f) => ({ ...f, referencia: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" placeholder="Nº transferencia, cheque..." /></div>
            </div>
            <div className="mt-6 flex flex-wrap gap-2 justify-end">
              <button type="button" onClick={() => { setModalPagoManual(false); setCuentaSeleccionada(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
              <button type="button" onClick={registrarPagoManual} disabled={enviandoPagoManual || !esNumeroValido(pagoFormManual.monto) || aNumero(pagoFormManual.monto) <= 0} className="min-h-[44px] px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-50 touch-manipulation">{enviandoPagoManual ? 'Guardando...' : 'Registrar pago'}</button>
            </div>
          </div>
        </div>
      )}

      {modalHistorialAbierto && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-lg w-full mx-4 max-h-[85vh] overflow-auto">
            <h2 className="text-lg font-semibold mb-4">Historial de pagos</h2>
            {cargandoHistorial ? (
              <p className="text-slate-500 py-4">Cargando...</p>
            ) : historialOrden ? (
              <>
                <p className="text-sm text-slate-600 mb-4">
                  Orden <strong>{historialOrden.numero}</strong> – {historialOrden.nombre_proveedor}
                </p>
                <p className="text-sm text-amber-700 font-medium mb-4">
                  Total: ${(historialOrden.total_a_pagar ?? 0).toFixed(2)} · Pagado: ${(historialOrden.total_pagado ?? 0).toFixed(2)} · Saldo: ${(historialOrden.saldo_pendiente ?? 0).toFixed(2)}
                </p>
                {historialOrden.pagos?.length > 0 ? (
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50"><tr><th className="px-4 py-2 text-left text-slate-500">Fecha</th><th className="px-4 py-2 text-right text-slate-500">Monto</th><th className="px-4 py-2 text-left text-slate-500">Método</th><th className="px-4 py-2 text-left text-slate-500">Referencia</th></tr></thead>
                    <tbody className="divide-y divide-slate-100">
                      {historialOrden.pagos.map((p) => (
                        <tr key={p.id_pago}><td className="px-4 py-2">{formatearFechaHora(p.fecha)}</td><td className="px-4 py-2 text-right font-medium">${(p.monto || 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</td><td className="px-4 py-2">{p.metodo}</td><td className="px-4 py-2 text-slate-600">{p.referencia || '-'}</td></tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-slate-500 py-4">Aún no hay pagos registrados.</p>
                )}
              </>
            ) : (
              <p className="text-slate-500 py-4">No se pudo cargar el historial.</p>
            )}
            <div className="mt-4 flex justify-end">
              <button type="button" onClick={() => setModalHistorialAbierto(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cerrar</button>
            </div>
          </div>
        </div>
      )}

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
                <input type="number" step="0.01" min="0" value={pagoForm.monto} onChange={(e) => setPagoForm((f) => ({ ...f, monto: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Método</label>
                <select value={pagoForm.metodo} onChange={(e) => setPagoForm((f) => ({ ...f, metodo: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation">
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="TARJETA">Tarjeta</option>
                  <option value="TRANSFERENCIA">Transferencia</option>
                  <option value="CHEQUE">Cheque</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-600 mb-1">Referencia (opcional)</label>
                <input type="text" value={pagoForm.referencia} onChange={(e) => setPagoForm((f) => ({ ...f, referencia: e.target.value }))} className="w-full px-3 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" placeholder="Nº de factura, transferencia..." />
              </div>
            </div>
            <div className="mt-6 flex flex-wrap gap-2 justify-end">
              <button type="button" onClick={() => { setModalPagoAbierto(false); setOrdenSeleccionada(null) }} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
              <button type="button" onClick={registrarPago} disabled={enviandoPago || !esNumeroValido(pagoForm.monto) || aNumero(pagoForm.monto) <= 0} className="min-h-[44px] px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-50 touch-manipulation">{enviandoPago ? 'Guardando...' : 'Registrar pago'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
