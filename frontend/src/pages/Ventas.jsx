import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'

export default function Ventas() {
  const { user } = useAuth()
  const [ventas, setVentas] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [clientes, setClientes] = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [servicios, setServicios] = useState([])
  const [form, setForm] = useState({ id_cliente: null, id_vehiculo: null, requiere_factura: false, detalles: [] })
  const [detalleActual, setDetalleActual] = useState({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalDetalleAbierto, setModalDetalleAbierto] = useState(false)
  const [ventaDetalle, setVentaDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [filtros, setFiltros] = useState({ estado: '', id_cliente: '', fecha_desde: '', fecha_hasta: '' })
  const [pagina, setPagina] = useState(1)
  const [limit] = useState(20)
  const [totalVentas, setTotalVentas] = useState(0)
  const [totalPaginas, setTotalPaginas] = useState(1)
  const [tabActivo, setTabActivo] = useState('listado')
  const [estadisticas, setEstadisticas] = useState(null)
  const [productosVendidos, setProductosVendidos] = useState([])
  const [clientesFrecuentes, setClientesFrecuentes] = useState([])
  const [cuentasCobrar, setCuentasCobrar] = useState([])
  const [filtrosReportes, setFiltrosReportes] = useState({ fecha_desde: '', fecha_hasta: '' })
  const [cargandoReportes, setCargandoReportes] = useState(false)

  const cargar = () => {
    const params = { limit, skip: (pagina - 1) * limit }
    if (filtros.estado) params.estado = filtros.estado
    if (filtros.id_cliente) params.id_cliente = parseInt(filtros.id_cliente)
    if (filtros.fecha_desde) params.fecha_desde = filtros.fecha_desde
    if (filtros.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta
    api.get('/ventas/', { params }).then((res) => {
      const d = res.data
      if (d?.ventas) {
        setVentas(d.ventas)
        setTotalVentas(d.total ?? d.ventas.length)
        setTotalPaginas(d.total_paginas ?? 1)
      } else {
        setVentas(Array.isArray(d) ? d : [])
        setTotalVentas(Array.isArray(d) ? d.length : 0)
        setTotalPaginas(1)
      }
    }).catch(() => setVentas([]))
    .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [filtros, pagina])
  useEffect(() => {
    api.get('/clientes/', { params: { limit: 500 } }).then((r) => {
      const d = r.data
      setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
    }).catch(() => setClientes([]))
  }, [])

  const cargarDatosModal = async () => {
    const [rRepuestos, rServicios, rClientes] = await Promise.allSettled([
      api.get('/repuestos/', { params: { limit: 200 } }),
      api.get('/servicios/', { params: { limit: 200 } }),
      api.get('/clientes/', { params: { limit: 500 } }),
    ])
    if (rRepuestos.status === 'fulfilled') {
      const d = rRepuestos.value?.data
      setRepuestos(Array.isArray(d) ? d : d?.repuestos ?? d?.items ?? [])
    }
    if (rServicios.status === 'fulfilled') {
      const d = rServicios.value?.data
      setServicios(Array.isArray(d) ? d : d?.servicios ?? [])
    }
    if (rClientes.status === 'fulfilled') {
      const d = rClientes.value?.data
      setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
    }
  }

  const abrirNueva = async () => {
    setForm({ id_cliente: null, id_vehiculo: null, requiere_factura: false, detalles: [] })
    setDetalleActual({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
    setError('')
    await cargarDatosModal()
    setModalAbierto(true)
  }

  useEffect(() => {
    if (form.id_cliente && modalAbierto) {
      api.get(`/vehiculos/cliente/${form.id_cliente}`).then((r) => setVehiculos(r.data)).catch(() => setVehiculos([]))
    } else setVehiculos([])
  }, [form.id_cliente, modalAbierto])

  const agregarDetalle = () => {
    if (!detalleActual.id_item || !detalleActual.descripcion || detalleActual.precio_unitario <= 0) {
      setError('Completa producto/servicio, descripción y precio')
      return
    }
    const item = detalleActual.tipo === 'PRODUCTO'
      ? repuestos.find(r => r.id_repuesto === parseInt(detalleActual.id_item))
      : servicios.find(s => s.id === parseInt(detalleActual.id_item) || s.id_servicio === parseInt(detalleActual.id_item))
    setForm({
      ...form,
      detalles: [...form.detalles, {
        tipo: detalleActual.tipo,
        id_item: parseInt(detalleActual.id_item),
        descripcion: detalleActual.descripcion,
        cantidad: detalleActual.cantidad,
        precio_unitario: parseFloat(detalleActual.precio_unitario),
      }],
    })
    setDetalleActual({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
    setError('')
  }

  const quitarDetalle = (idx) => {
    setForm({ ...form, detalles: form.detalles.filter((_, i) => i !== idx) })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.detalles.length) { setError('Agrega al menos un producto o servicio'); return }
    setEnviando(true)
    try {
      await api.post('/ventas/', {
        id_cliente: form.id_cliente || null,
        id_vehiculo: form.id_vehiculo || null,
        requiere_factura: form.requiere_factura,
        detalles: form.detalles,
      })
      cargar()
      setModalAbierto(false)
    } catch (err) {
      const msg = err.response?.data?.detail
      setError(Array.isArray(msg) ? msg.map((m) => m.msg).join(', ') : msg)
    } finally {
      setEnviando(false)
    }
  }

  const abrirDetalle = async (idVenta) => {
    setCargandoDetalle(true)
    setVentaDetalle(null)
    setModalDetalleAbierto(true)
    try {
      const res = await api.get(`/ventas/${idVenta}`)
      setVentaDetalle(res.data)
    } catch { setVentaDetalle(null) }
    finally { setCargandoDetalle(false) }
  }

  const descargarTicket = async (idVenta, tipo = 'nota') => {
    try {
      const res = await api.get(`/ventas/${idVenta}/ticket`, { params: { tipo }, responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `venta-${idVenta}-${tipo}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al descargar ticket')
    }
  }

  const cargarReportes = async () => {
    setCargandoReportes(true)
    const params = {}
    if (filtrosReportes.fecha_desde) params.fecha_desde = filtrosReportes.fecha_desde
    if (filtrosReportes.fecha_hasta) params.fecha_hasta = filtrosReportes.fecha_hasta
    try {
      const [rEst, rProd, rCli, rCxC] = await Promise.allSettled([
        api.get('/ventas/estadisticas/resumen', { params }),
        api.get('/ventas/reportes/productos-mas-vendidos', { params: { ...params, limit: 20 } }),
        api.get('/ventas/reportes/clientes-frecuentes', { params: { ...params, limit: 20 } }),
        api.get('/ventas/reportes/cuentas-por-cobrar', { params }),
      ])
      if (rEst.status === 'fulfilled') setEstadisticas(rEst.value.data)
      if (rProd.status === 'fulfilled') setProductosVendidos(rProd.value.data?.productos || [])
      if (rCli.status === 'fulfilled') setClientesFrecuentes(rCli.value.data?.clientes || [])
      if (rCxC.status === 'fulfilled') setCuentasCobrar(rCxC.value.data?.items || rCxC.value.data?.ventas || [])
    } finally { setCargandoReportes(false) }
  }

  const exportarExcel = async (tipo) => {
    const params = {}
    if (filtrosReportes.fecha_desde) params.fecha_desde = filtrosReportes.fecha_desde
    if (filtrosReportes.fecha_hasta) params.fecha_hasta = filtrosReportes.fecha_hasta
    const urls = { ventas: '/exportaciones/ventas', productos: '/exportaciones/productos-vendidos', clientes: '/exportaciones/clientes-frecuentes', cuentas: '/exportaciones/cuentas-por-cobrar' }
    const url = urls[tipo] || '/exportaciones/ventas'
    try {
      const res = await api.get(url, { params: { ...params, limit: 1000 }, responseType: 'blob' })
      const fn = res.headers['content-disposition']?.match(/filename="?([^";]+)"?/)?.[1] || `reporte_${tipo}.xlsx`
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = fn
      link.click()
      window.URL.revokeObjectURL(link.href)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al exportar')
    }
  }

  if (loading) return <p className="text-slate-500">Cargando...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-slate-800">Ventas</h1>
        <div className="flex gap-2">
          <button onClick={() => setTabActivo('listado')} className={`px-4 py-2 rounded-lg font-medium ${tabActivo === 'listado' ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600'}`}>Listado</button>
          <button onClick={() => { setTabActivo('reportes'); cargarReportes() }} className={`px-4 py-2 rounded-lg font-medium ${tabActivo === 'reportes' ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600'}`}>Reportes</button>
          <button onClick={abrirNueva} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium">Nueva venta</button>
        </div>
      </div>

      {tabActivo === 'listado' && (
        <>
          <div className="bg-white rounded-lg shadow p-4 mb-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Estado</label>
                <select value={filtros.estado} onChange={(e) => { setFiltros((f) => ({ ...f, estado: e.target.value })); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
                  <option value="">Todos</option>
                  <option value="PENDIENTE">Pendiente</option>
                  <option value="PAGADA">Pagada</option>
                  <option value="CANCELADA">Cancelada</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Cliente</label>
                <select value={filtros.id_cliente} onChange={(e) => { setFiltros((f) => ({ ...f, id_cliente: e.target.value })); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[160px]">
                  <option value="">Todos</option>
                  {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Fecha desde</label>
                <input type="date" value={filtros.fecha_desde} onChange={(e) => { setFiltros((f) => ({ ...f, fecha_desde: e.target.value })); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Fecha hasta</label>
                <input type="date" value={filtros.fecha_hasta} onChange={(e) => { setFiltros((f) => ({ ...f, fecha_hasta: e.target.value })); setPagina(1) }} className="px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fecha</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Cliente</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Saldo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Estado</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {ventas.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">No hay ventas</td></tr>
                ) : (
                  ventas.map((v) => (
                    <tr key={v.id_venta} className="hover:bg-slate-50">
                      <td className="px-4 py-3 text-sm text-slate-800">{v.id_venta}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{v.fecha ? new Date(v.fecha).toLocaleDateString() : '-'}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{v.nombre_cliente || '-'}</td>
                      <td className="px-4 py-3 text-sm font-medium text-slate-800">${(v.total ?? 0).toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm"><span className={v.saldo_pendiente > 0 ? 'text-amber-600 font-medium' : ''}>${(v.saldo_pendiente ?? 0).toFixed(2)}</span></td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${v.estado === 'CANCELADA' ? 'bg-slate-200' : v.estado === 'PAGADA' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>{v.estado || 'PENDIENTE'}</span></td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex gap-2 justify-end">
                          {v.estado !== 'CANCELADA' && <button onClick={() => descargarTicket(v.id_venta)} className="text-sm text-slate-600 hover:text-slate-800">📄 Ticket</button>}
                          <button onClick={() => abrirDetalle(v.id_venta)} className="text-sm text-primary-600 hover:text-primary-700">Ver detalle</button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPaginas > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-slate-600">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, totalVentas)} de {totalVentas}</p>
              <div className="flex gap-2">
                <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Anterior</button>
                <span className="px-3 py-1 text-sm text-slate-700">Página {pagina} de {totalPaginas}</span>
                <button onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="px-3 py-1 border border-slate-300 rounded-lg text-sm disabled:opacity-50">Siguiente</button>
              </div>
            </div>
          )}
        </>
      )}

      {tabActivo === 'reportes' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex flex-wrap gap-3 items-end mb-4">
              <input type="date" value={filtrosReportes.fecha_desde} onChange={(e) => setFiltrosReportes((f) => ({ ...f, fecha_desde: e.target.value }))} className="px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <input type="date" value={filtrosReportes.fecha_hasta} onChange={(e) => setFiltrosReportes((f) => ({ ...f, fecha_hasta: e.target.value }))} className="px-3 py-2 border border-slate-300 rounded-lg text-sm" />
              <button onClick={cargarReportes} disabled={cargandoReportes} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{cargandoReportes ? 'Cargando...' : 'Actualizar'}</button>
            </div>
          </div>
          {estadisticas && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Estadísticas</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Total ventas</p><p className="text-xl font-bold">{estadisticas.total_ventas}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Monto total</p><p className="text-xl font-bold">${(estadisticas.monto_total || 0).toFixed(2)}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Promedio</p><p className="text-xl font-bold">${(estadisticas.promedio_por_venta || 0).toFixed(2)}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Pend/Pag/Can</p><p className="text-sm font-medium">{estadisticas.por_estado?.pendientes ?? 0} / {estadisticas.por_estado?.pagadas ?? 0} / {estadisticas.por_estado?.canceladas ?? 0}</p></div>
              </div>
              <button onClick={() => exportarExcel('ventas')} className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">📥 Exportar ventas a Excel</button>
            </div>
          )}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 flex justify-between"><h2 className="text-lg font-semibold">Productos más vendidos</h2><button onClick={() => exportarExcel('productos')} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm">📥 Exportar</button></div>
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs text-slate-500">Producto</th><th className="px-4 py-3 text-right text-xs text-slate-500">Cantidad</th><th className="px-4 py-3 text-right text-xs text-slate-500">Monto</th></tr></thead>
              <tbody>{productosVendidos.map((p) => <tr key={p.id_repuesto}><td className="px-4 py-2 text-sm">{p.codigo} - {p.nombre}</td><td className="px-4 py-2 text-sm text-right">{p.cantidad_vendida}</td><td className="px-4 py-2 text-sm text-right">${(p.monto_total || 0).toFixed(2)}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 flex justify-between"><h2 className="text-lg font-semibold">Clientes frecuentes</h2><button onClick={() => exportarExcel('clientes')} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm">📥 Exportar</button></div>
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs text-slate-500">Cliente</th><th className="px-4 py-3 text-right text-xs text-slate-500">Ventas</th><th className="px-4 py-3 text-right text-xs text-slate-500">Total</th></tr></thead>
              <tbody>{clientesFrecuentes.map((c) => <tr key={c.id_cliente}><td className="px-4 py-2 text-sm">{c.nombre}</td><td className="px-4 py-2 text-sm text-right">{c.total_ventas}</td><td className="px-4 py-2 text-sm text-right">${(c.monto_total || 0).toFixed(2)}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 flex justify-between"><h2 className="text-lg font-semibold">Cuentas por cobrar</h2><button onClick={() => exportarExcel('cuentas')} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm">📥 Exportar</button></div>
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs text-slate-500">ID</th><th className="px-4 py-3 text-left text-xs text-slate-500">Cliente</th><th className="px-4 py-3 text-right text-xs text-slate-500">Total</th><th className="px-4 py-3 text-right text-xs text-slate-500">Saldo</th></tr></thead>
              <tbody>{cuentasCobrar.map((v) => <tr key={v.id_venta}><td className="px-4 py-2 text-sm">{v.id_venta}</td><td className="px-4 py-2 text-sm">{v.nombre_cliente || '-'}</td><td className="px-4 py-2 text-sm text-right">${(v.total || 0).toFixed(2)}</td><td className="px-4 py-2 text-sm text-right font-medium text-amber-700">${(v.saldo_pendiente ?? 0).toFixed(2)}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}

      <Modal titulo="Detalle de venta" abierto={modalDetalleAbierto} onCerrar={() => { setModalDetalleAbierto(false); setVentaDetalle(null) }}>
        {cargandoDetalle ? <p className="text-slate-500 py-4">Cargando...</p> : ventaDetalle ? (
          <div className="space-y-4">
            <p><strong>ID:</strong> {ventaDetalle.id_venta}</p>
            <p><strong>Fecha:</strong> {ventaDetalle.fecha ? new Date(ventaDetalle.fecha).toLocaleString() : '-'}</p>
            <p><strong>Cliente:</strong> {ventaDetalle.nombre_cliente || '-'}</p>
            <p><strong>Total:</strong> ${(ventaDetalle.total ?? 0).toFixed(2)}</p>
            <p><strong>Estado:</strong> {ventaDetalle.estado || '-'}</p>
            {ventaDetalle.detalles?.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Productos / Servicios</h4>
                <ul className="list-disc pl-4">{ventaDetalle.detalles.map((d, i) => <li key={i}>{d.descripcion} x{d.cantidad} ${(d.subtotal ?? 0).toFixed(2)}</li>)}</ul>
              </div>
            )}
            {ventaDetalle.estado !== 'CANCELADA' && <button onClick={() => descargarTicket(ventaDetalle.id_venta)} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm">📄 Descargar ticket</button>}
          </div>
        ) : null}
      </Modal>

      <Modal titulo="Nueva venta" abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cliente (opcional)</label>
            <select value={form.id_cliente || ''} onChange={(e) => setForm({ ...form, id_cliente: e.target.value ? parseInt(e.target.value) : null })} onFocus={cargarDatosModal} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="">— Sin cliente —</option>
              {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
            </select>
          </div>
          {form.id_cliente && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Vehículo (opcional)</label>
              <select value={form.id_vehiculo || ''} onChange={(e) => setForm({ ...form, id_vehiculo: e.target.value ? parseInt(e.target.value) : null })} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
                <option value="">-- Sin vehículo --</option>
                {vehiculos.map((v) => <option key={v.id_vehiculo} value={v.id_vehiculo}>{v.marca} {v.modelo} {v.anio}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Agregar producto/servicio</label>
            <div className="flex gap-2 flex-wrap">
              <select value={detalleActual.tipo} onChange={(e) => setDetalleActual({ ...detalleActual, tipo: e.target.value, id_item: '' })} className="px-3 py-2 border rounded-lg text-sm">
                <option value="PRODUCTO">Producto</option>
                <option value="SERVICIO">Servicio</option>
              </select>
              <select value={detalleActual.id_item} onChange={(e) => {
                const id = e.target.value
                const item = detalleActual.tipo === 'PRODUCTO' ? repuestos.find(r => r.id_repuesto === parseInt(id)) : servicios.find(s => (s.id ?? s.id_servicio) === parseInt(id))
                setDetalleActual({ ...detalleActual, id_item: id, descripcion: item ? (item.nombre || `${item.codigo || ''} ${item.nombre || ''}`.trim()) : '', precio_unitario: item ? (parseFloat(item.precio_venta) || parseFloat(item.precio_base) || 0) : 0 })
              }} className="px-3 py-2 border rounded-lg text-sm min-w-[140px]">
                <option value="">{detalleActual.tipo === 'PRODUCTO' ? 'Producto...' : 'Servicio...'}</option>
                {(detalleActual.tipo === 'PRODUCTO' ? repuestos : servicios).map((x) => (
                  <option key={x.id_repuesto ?? x.id ?? x.id_servicio} value={x.id_repuesto ?? x.id ?? x.id_servicio}>{x.codigo || ''} {x.nombre}</option>
                ))}
              </select>
              <input type="text" value={detalleActual.descripcion} onChange={(e) => setDetalleActual({ ...detalleActual, descripcion: e.target.value })} placeholder="Descripción" className="px-3 py-2 border rounded-lg text-sm flex-1 min-w-[120px]" />
              <input type="number" min={1} value={detalleActual.cantidad} onChange={(e) => setDetalleActual({ ...detalleActual, cantidad: parseInt(e.target.value) || 1 })} className="w-16 px-2 py-2 border rounded-lg text-sm" />
              <input type="number" min={0} step={0.01} value={detalleActual.precio_unitario} onChange={(e) => setDetalleActual({ ...detalleActual, precio_unitario: parseFloat(e.target.value) || 0 })} placeholder="Precio" className="w-24 px-2 py-2 border rounded-lg text-sm" />
              <button type="button" onClick={agregarDetalle} className="px-3 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300">+ Agregar</button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Detalles</label>
            <ul className="border rounded-lg divide-y">
              {form.detalles.map((d, i) => (
                <li key={i} className="px-3 py-2 flex justify-between">
                  <span>{d.descripcion} x{d.cantidad} @ ${d.precio_unitario} = ${(d.cantidad * d.precio_unitario).toFixed(2)}</span>
                  <button type="button" onClick={() => quitarDetalle(i)} className="text-red-600 text-sm">Quitar</button>
                </li>
              ))}
            </ul>
            {form.detalles.length > 0 && <p className="mt-2 font-medium">Total: ${form.detalles.reduce((s, d) => s + d.cantidad * d.precio_unitario, 0).toFixed(2)}</p>}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviando || !form.detalles.length} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">{enviando ? 'Guardando...' : 'Guardar venta'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
