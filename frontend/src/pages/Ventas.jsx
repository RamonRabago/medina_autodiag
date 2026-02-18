import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { formatearFechaSolo, formatearFechaHora } from '../utils/fechas'

/** Fecha de venta: prioriza venta.fecha; si falta, extrae de numero_orden (OT-YYYYMMDD-NNN). */
function obtenerFechaVentaDetalle(venta) {
  const f = formatearFechaHora(venta?.fecha)
  if (f !== '-') return f
  const num = venta?.orden_vinculada?.numero_orden
  if (!num || typeof num !== 'string') return '-'
  const m = num.match(/OT-(\d{4})(\d{2})(\d{2})-\d+/)
  if (m) return formatearFechaSolo(`${m[1]}-${m[2]}-${m[3]}`)
  return '-'
}
import { aNumero, aEntero, esNumeroValido } from '../utils/numeros'
import PageLoading from '../components/PageLoading'
import LoadingSpinner from '../components/LoadingSpinner'
import { normalizeDetail, showError, showSuccess } from '../utils/toast'
import { useApiQuery, useInvalidateQueries } from '../hooks/useApi'

export default function Ventas() {
  const { user } = useAuth()
  const invalidate = useInvalidateQueries()
  const [modalAbierto, setModalAbierto] = useState(false)
  const [clientes, setClientes] = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [servicios, setServicios] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [form, setForm] = useState({ id_cliente: null, id_vehiculo: null, id_vendedor: null, requiere_factura: false, comentarios: '', detalles: [] })
  const [detalleActual, setDetalleActual] = useState({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
  const [error, setError] = useState('')
  const [errorCargar, setErrorCargar] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modalDetalleAbierto, setModalDetalleAbierto] = useState(false)
  const [ventaDetalle, setVentaDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [filtros, setFiltros] = useState({ estado: '', id_cliente: '', fecha_desde: '', fecha_hasta: '' })
  const [pagina, setPagina] = useState(1)
  const [limit] = useState(20)
  const [tabActivo, setTabActivo] = useState('listado')
  const [estadisticas, setEstadisticas] = useState(null)
  const [productosVendidos, setProductosVendidos] = useState([])
  const [clientesFrecuentes, setClientesFrecuentes] = useState([])
  const [cuentasCobrar, setCuentasCobrar] = useState([])
  const [reporteUtilidad, setReporteUtilidad] = useState(null)
  const [reporteComisiones, setReporteComisiones] = useState(null)
  const [filtrosReportes, setFiltrosReportes] = useState({ fecha_desde: '', fecha_hasta: '' })
  const [cargandoReportes, setCargandoReportes] = useState(false)
  const [modalCancelarAbierto, setModalCancelarAbierto] = useState(false)
  const [ventaACancelar, setVentaACancelar] = useState(null)
  const [ventaACancelarDetalle, setVentaACancelarDetalle] = useState(null)
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const [productosCancelacion, setProductosCancelacion] = useState([])
  const [pagoForm, setPagoForm] = useState({ monto: '', metodo: 'EFECTIVO', referencia: '' })
  const [enviandoPago, setEnviandoPago] = useState(false)
  const [ordenesDisponibles, setOrdenesDisponibles] = useState([])
  const [ordenSeleccionadaVincular, setOrdenSeleccionadaVincular] = useState('')
  const [vinculando, setVinculando] = useState(false)
  const [modalEditarAbierto, setModalEditarAbierto] = useState(false)
  const [formEditar, setFormEditar] = useState({ id_cliente: null, id_vehiculo: null, id_vendedor: null, requiere_factura: false, comentarios: '', detalles: [] })
  const [detalleActualEditar, setDetalleActualEditar] = useState({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
  const [errorEditar, setErrorEditar] = useState('')
  const [enviandoEditar, setEnviandoEditar] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [config, setConfig] = useState({ iva_porcentaje: 8 })
  const [errorConfig, setErrorConfig] = useState('')

  useEffect(() => {
    api.get('/config')
      .then((r) => { setConfig(r.data || { iva_porcentaje: 8 }); setErrorConfig('') })
      .catch((err) => { setErrorConfig(normalizeDetail(err.response?.data?.detail) || 'No se pudo cargar configuración de IVA') })
  }, [])

  const ivaFactor = 1 + (config.iva_porcentaje || 8) / 100
  const puedeVerComisiones = ['ADMIN', 'CAJA', 'EMPLEADO', 'TECNICO'].includes(user?.rol)

  const ventasParams = { limit, skip: (pagina - 1) * limit }
  if (filtros.estado) ventasParams.estado = filtros.estado
  if (filtros.id_cliente) ventasParams.id_cliente = aEntero(filtros.id_cliente)
  if (filtros.fecha_desde) ventasParams.fecha_desde = filtros.fecha_desde
  if (filtros.fecha_hasta) ventasParams.fecha_hasta = filtros.fecha_hasta

  const { data: ventasData, isLoading: loading, isError: ventasError, error: ventasErr } = useApiQuery(
    ['ventas', pagina, filtros.estado, filtros.id_cliente, filtros.fecha_desde, filtros.fecha_hasta],
    () => api.get('/ventas/', { params: ventasParams }).then((r) => r.data),
    { staleTime: 45 * 1000 }
  )
  const ventas = ventasData?.ventas ?? (Array.isArray(ventasData) ? ventasData : [])
  const totalVentas = ventasData?.total ?? (Array.isArray(ventasData) ? ventasData.length : 0)
  const totalPaginas = ventasData?.total_paginas ?? 1
  const recargar = () => invalidate(['ventas'])

  useEffect(() => {
    if (ventasError && ventasErr) setErrorCargar(ventasErr?.code === 'ECONNABORTED' ? 'Tiempo de espera agotado.' : 'Error al cargar ventas.')
    else setErrorCargar('')
  }, [ventasError, ventasErr])

  const idVentaUrl = searchParams.get('id')
  useEffect(() => {
    if (idVentaUrl) {
      const id = aEntero(idVentaUrl)
      if (id > 0) {
        setModalDetalleAbierto(true)
        setCargandoDetalle(true)
        setVentaDetalle(null)
        api.get(`/ventas/${id}`).then((res) => setVentaDetalle(res.data)).catch((err) => { showError(err, 'Error al cargar venta'); setVentaDetalle(null) }).finally(() => setCargandoDetalle(false))
        setSearchParams({})
      }
    }
  }, [idVentaUrl])

  useEffect(() => {
    api.get('/clientes/', { params: { limit: 500 } }).then((r) => {
      const d = r.data
      setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
    }).catch((err) => { showError(err, 'Error al cargar clientes'); setClientes([]) })
  }, [])

  const cargarDatosModal = async () => {
    const [rRepuestos, rServicios, rClientes, rUsuarios] = await Promise.allSettled([
      api.get('/repuestos/', { params: { limit: 200 } }),
      api.get('/servicios/', { params: { limit: 500 } }),
      api.get('/clientes/', { params: { limit: 500 } }),
      api.get('/usuarios/'),
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
    if (rUsuarios.status === 'fulfilled') {
      const d = rUsuarios.value?.data
      setUsuarios(Array.isArray(d) ? d : [])
    }
  }

  const abrirNueva = async () => {
    setForm({ id_cliente: null, id_vehiculo: null, id_vendedor: user?.id_usuario || null, requiere_factura: false, comentarios: '', detalles: [] })
    setDetalleActual({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
    setError('')
    await cargarDatosModal()
    setModalAbierto(true)
  }

  useEffect(() => {
    if (form.id_cliente && modalAbierto) {
      api.get(`/vehiculos/cliente/${form.id_cliente}`).then((r) => setVehiculos(r.data)).catch((err) => { showError(err, 'Error al cargar vehículos'); setVehiculos([]) })
    } else setVehiculos([])
  }, [form.id_cliente, modalAbierto])

  useEffect(() => {
    if (ventaDetalle?.saldo_pendiente != null && ventaDetalle.saldo_pendiente > 0) {
      setPagoForm((prev) => ({ ...prev, monto: Number(ventaDetalle.saldo_pendiente).toFixed(2) }))
    } else if (ventaDetalle) {
      setPagoForm((prev) => ({ ...prev, monto: '' }))
    }
  }, [ventaDetalle])

  const agregarDetalle = () => {
    if (!detalleActual.id_item || !detalleActual.descripcion || detalleActual.precio_unitario <= 0) {
      setError('Completa producto/servicio, descripción y precio')
      return
    }
    const idItem = aEntero(detalleActual.id_item)
    const item = detalleActual.tipo === 'PRODUCTO'
      ? repuestos.find(r => r.id_repuesto === idItem)
      : servicios.find(s => s.id === idItem || s.id_servicio === idItem)
    setForm({
      ...form,
      detalles: [...form.detalles, {
        tipo: detalleActual.tipo,
        id_item: idItem,
        descripcion: detalleActual.descripcion,
        cantidad: detalleActual.cantidad,
        precio_unitario: aNumero(detalleActual.precio_unitario),
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
      const res = await api.post('/ventas/', {
        id_cliente: form.id_cliente || null,
        id_vehiculo: form.id_vehiculo || null,
        id_vendedor: form.id_vendedor || null,
        requiere_factura: form.requiere_factura,
        comentarios: form.comentarios?.trim() || null,
        detalles: form.detalles,
      })
      showSuccess(`Venta #${res.data?.id_venta ?? ''} creada. Total: $${(res.data?.total ?? 0).toFixed(2)}`)
      recargar()
      setModalAbierto(false)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al crear venta')
    } finally {
      setEnviando(false)
    }
  }

  const abrirModalCancelar = async (idVenta) => {
    setVentaACancelar(idVenta)
    setMotivoCancelacion('')
    setVentaACancelarDetalle(null)
    setProductosCancelacion([])
    setModalCancelarAbierto(true)
    try {
      const res = await api.get(`/ventas/${idVenta}`)
      const v = res.data
      setVentaACancelarDetalle(v)
      const productos = (v.detalles || []).filter(d => (d.tipo || '').toUpperCase() === 'PRODUCTO')
      if (productos.length > 0) {
        setProductosCancelacion(productos.map(p => ({
          id_detalle: p.id_detalle,
          descripcion: p.descripcion,
          cantidad: p.cantidad || 1,
          es_consumible: !!p.es_consumible,
          cantidad_reutilizable: p.es_consumible ? 0 : (p.cantidad || 1),
          cantidad_mer: p.es_consumible ? (p.cantidad || 1) : 0,
          motivo_mer: p.es_consumible ? '' : ''
        })))
      } else {
        setProductosCancelacion([])
      }
    } catch {
      setVentaACancelarDetalle(null)
      setProductosCancelacion([])
    }
  }

  const aplicarConsumiblesMerma = () => {
    setProductosCancelacion(prev => prev.map(p => ({
      ...p,
      cantidad_reutilizable: p.es_consumible ? 0 : p.cantidad,
      cantidad_mer: p.es_consumible ? p.cantidad : 0,
      motivo_mer: p.motivo_mer || ''
    })))
  }

  const actualizarProductoCancelacion = (idx, field, value) => {
    setProductosCancelacion(prev => {
      const p = { ...prev[idx] }
      if (field === 'cantidad_reutilizable') {
        const c = Math.max(0, Math.min(aEntero(value), p.cantidad))
        p.cantidad_reutilizable = c
        p.cantidad_mer = p.cantidad - c
      } else if (field === 'cantidad_mer') {
        const c = Math.max(0, Math.min(aEntero(value), p.cantidad))
        p.cantidad_mer = c
        p.cantidad_reutilizable = p.cantidad - c
      } else {
        p[field] = value
      }
      const next = [...prev]
      next[idx] = p
      return next
    })
  }

  const confirmarCancelar = async () => {
    if (!ventaACancelar || !motivoCancelacion.trim() || motivoCancelacion.trim().length < 5) return
    const payload = { motivo: motivoCancelacion.trim() }
    if (productosCancelacion.length > 0) {
      const productosValidos = productosCancelacion.every(p => {
        const reutil = p.cantidad_reutilizable ?? 0
        const mer = p.cantidad_mer ?? 0
        return reutil + mer === p.cantidad && (mer === 0 || (p.motivo_mer || '').trim().length > 0)
      })
      if (!productosValidos) {
        showError('Para productos marcados como MERMA debes indicar el motivo. Además, la suma de reutilizable + merma debe ser la cantidad total.')
        return
      }
      payload.productos = productosCancelacion.map(p => ({
        id_detalle: p.id_detalle,
        cantidad_reutilizable: aEntero(p.cantidad_reutilizable),
        cantidad_mer: aEntero(p.cantidad_mer),
        motivo_mer: (p.motivo_mer || '').trim() || null
      }))
    }
    try {
      await api.post(`/ventas/${ventaACancelar}/cancelar`, payload)
      setModalCancelarAbierto(false)
      setVentaACancelar(null)
      setVentaACancelarDetalle(null)
      setMotivoCancelacion('')
      setProductosCancelacion([])
      recargar()
      if (modalDetalleAbierto && ventaDetalle?.id_venta === ventaACancelar) {
        setModalDetalleAbierto(false)
        setVentaDetalle(null)
      }
    } catch (err) {
      showError(err, 'Error al cancelar')
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

  const registrarPago = async () => {
    if (!ventaDetalle || !esNumeroValido(pagoForm.monto) || aNumero(pagoForm.monto) <= 0) return
    const monto = Math.round(aNumero(pagoForm.monto) * 100) / 100
    const saldo = Math.round(Number(ventaDetalle.saldo_pendiente ?? 0) * 100) / 100
    if (monto > saldo) {
      showError(`El monto no puede exceder el saldo pendiente ($${saldo.toFixed(2)})`)
      return
    }
    setEnviandoPago(true)
    try {
      await api.post('/pagos/', {
        id_venta: ventaDetalle.id_venta,
        metodo: pagoForm.metodo,
        monto,
        referencia: pagoForm.referencia.trim() || null,
      })
      const res = await api.get(`/ventas/${ventaDetalle.id_venta}`)
      setVentaDetalle(res.data)
      const liquidada = res.data?.estado === 'PAGADA'
      showSuccess(liquidada ? 'Pago registrado. Venta liquidada.' : 'Pago registrado correctamente.')
      recargar()
    } catch (err) {
      showError(err, 'Error al registrar pago')
    } finally {
      setEnviandoPago(false)
    }
  }

  const cargarOrdenesDisponibles = async () => {
    try {
      const res = await api.get('/ventas/ordenes-disponibles', { params: { limit: 100 } })
      setOrdenesDisponibles(Array.isArray(res.data) ? res.data : [])
    } catch { setOrdenesDisponibles([]) }
  }

  const vincularOrden = async () => {
    if (!ventaDetalle || !ordenSeleccionadaVincular) return
    setVinculando(true)
    try {
      await api.put(`/ventas/${ventaDetalle.id_venta}/vincular-orden`, { id_orden: aEntero(ordenSeleccionadaVincular) })
      const res = await api.get(`/ventas/${ventaDetalle.id_venta}`)
      setVentaDetalle(res.data)
      setOrdenSeleccionadaVincular('')
      recargar()
      cargarOrdenesDisponibles()
    } catch (err) {
      showError(err, 'Error al vincular')
    } finally { setVinculando(false) }
  }

  const abrirEditar = () => {
    if (!ventaDetalle) return
    setFormEditar({
      id_cliente: ventaDetalle.id_cliente || null,
      id_vehiculo: ventaDetalle.id_vehiculo || null,
      id_vendedor: ventaDetalle.id_vendedor || null,
      requiere_factura: ventaDetalle.requiere_factura || false,
      comentarios: ventaDetalle.comentarios || '',
      detalles: (ventaDetalle.detalles || []).map((d) => ({
        tipo: d.tipo,
        id_item: d.id_item,
        descripcion: d.descripcion,
        cantidad: d.cantidad,
        precio_unitario: d.precio_unitario ?? 0,
      })),
    })
    setDetalleActualEditar({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
    setErrorEditar('')
    cargarDatosModal()
    setModalEditarAbierto(true)
  }

  useEffect(() => {
    if (formEditar.id_cliente && modalEditarAbierto) {
      api.get(`/vehiculos/cliente/${formEditar.id_cliente}`).then((r) => setVehiculos(r.data)).catch((err) => { showError(err, 'Error al cargar vehículos'); setVehiculos([]) })
    } else if (modalEditarAbierto) setVehiculos([])
  }, [formEditar.id_cliente, modalEditarAbierto])

  const agregarDetalleEditar = () => {
    if (!detalleActualEditar.id_item || !detalleActualEditar.descripcion || detalleActualEditar.precio_unitario <= 0) {
      setErrorEditar('Completa producto/servicio, descripción y precio')
      return
    }
    const idItemEd = aEntero(detalleActualEditar.id_item)
    const item = detalleActualEditar.tipo === 'PRODUCTO'
      ? repuestos.find((r) => r.id_repuesto === idItemEd)
      : servicios.find((s) => (s.id ?? s.id_servicio) === idItemEd)
    setFormEditar({
      ...formEditar,
      detalles: [...formEditar.detalles, {
        tipo: detalleActualEditar.tipo,
        id_item: idItemEd,
        descripcion: detalleActualEditar.descripcion,
        cantidad: detalleActualEditar.cantidad,
        precio_unitario: aNumero(detalleActualEditar.precio_unitario),
      }],
    })
    setDetalleActualEditar({ tipo: 'PRODUCTO', id_item: '', descripcion: '', cantidad: 1, precio_unitario: 0 })
    setErrorEditar('')
  }

  const quitarDetalleEditar = (idx) => {
    setFormEditar({ ...formEditar, detalles: formEditar.detalles.filter((_, i) => i !== idx) })
  }

  const guardarEditar = async (e) => {
    e.preventDefault()
    setErrorEditar('')
    if (!formEditar.detalles.length) { setErrorEditar('Agrega al menos un producto o servicio'); return }
    setEnviandoEditar(true)
    try {
      const putRes = await api.put(`/ventas/${ventaDetalle.id_venta}`, {
        id_cliente: formEditar.id_cliente || null,
        id_vehiculo: formEditar.id_vehiculo || null,
        id_vendedor: formEditar.id_vendedor || null,
        requiere_factura: formEditar.requiere_factura,
        comentarios: formEditar.comentarios?.trim() || null,
        detalles: formEditar.detalles,
      })
      if (putRes.data?.estado_actualizado && putRes.data?.mensaje) {
        showSuccess(putRes.data.mensaje)
      } else {
        showSuccess('Venta actualizada')
      }
      const res = await api.get(`/ventas/${ventaDetalle.id_venta}`)
      setVentaDetalle(res.data)
      cargar()
      setModalEditarAbierto(false)
    } catch (err) {
      setErrorEditar(normalizeDetail(err.response?.data?.detail) || 'Error al guardar')
    } finally {
      setEnviandoEditar(false)
    }
  }

  const desvincularOrden = async () => {
    if (!ventaDetalle) return
    if (!confirm('¿Desvincular la orden de trabajo de esta venta?')) return
    setVinculando(true)
    try {
      await api.put(`/ventas/${ventaDetalle.id_venta}/vincular-orden`, { id_orden: null })
      const res = await api.get(`/ventas/${ventaDetalle.id_venta}`)
      setVentaDetalle(res.data)
      cargarOrdenesDisponibles()
    } catch (err) {
      showError(err, 'Error al desvincular')
    } finally { setVinculando(false) }
  }

  const descargarTicket = async (idVenta, tipo = 'nota') => {
    try {
      const res = await api.get(`/ventas/${idVenta}/ticket`, { params: { tipo }, responseType: 'blob' })
      const contentType = res.headers?.['content-type'] || ''
      if (contentType.includes('application/json')) {
        const text = await res.data.text()
        const json = JSON.parse(text)
        showError(json?.detail || 'Error al descargar ticket', 'Error al descargar ticket')
        return
      }
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `venta-${idVenta}-${tipo}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      let msg = 'Error al descargar ticket'
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text()
          const json = JSON.parse(text)
          msg = json?.detail || msg
        } catch (_) {}
      } else if (err?.response?.data?.detail != null) {
        msg = typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail)
      }
      showError(msg, 'Error al descargar ticket')
    }
  }

  const cargarReportes = async () => {
    setCargandoReportes(true)
    const params = {}
    if (filtrosReportes.fecha_desde) params.fecha_desde = filtrosReportes.fecha_desde
    if (filtrosReportes.fecha_hasta) params.fecha_hasta = filtrosReportes.fecha_hasta
    const llamadas = [
      api.get('/ventas/estadisticas/resumen', { params }),
      api.get('/ventas/reportes/productos-mas-vendidos', { params: { ...params, limit: 20 } }),
      api.get('/ventas/reportes/clientes-frecuentes', { params: { ...params, limit: 20 } }),
      api.get('/ventas/reportes/cuentas-por-cobrar', { params }),
      api.get('/ventas/reportes/utilidad', { params }),
    ]
    if (puedeVerComisiones) llamadas.push(api.get('/ventas/reportes/comisiones', { params }))
    try {
      const resultados = await Promise.allSettled(llamadas)
      if (resultados[0]?.status === 'fulfilled') setEstadisticas(resultados[0].value.data)
      if (resultados[1]?.status === 'fulfilled') setProductosVendidos(resultados[1].value.data?.productos || [])
      if (resultados[2]?.status === 'fulfilled') setClientesFrecuentes(resultados[2].value.data?.clientes || [])
      if (resultados[3]?.status === 'fulfilled') setCuentasCobrar(resultados[3].value.data?.items || resultados[3].value.data?.ventas || [])
      if (resultados[4]?.status === 'fulfilled') setReporteUtilidad(resultados[4].value.data)
      if (puedeVerComisiones && resultados[5]?.status === 'fulfilled') setReporteComisiones(resultados[5].value.data)
      else setReporteComisiones(null)
    } finally { setCargandoReportes(false) }
  }

  const exportarExcel = async (tipo) => {
    const params = {}
    if (filtrosReportes.fecha_desde) params.fecha_desde = filtrosReportes.fecha_desde
    if (filtrosReportes.fecha_hasta) params.fecha_hasta = filtrosReportes.fecha_hasta
    const urls = { ventas: '/exportaciones/ventas', productos: '/exportaciones/productos-vendidos', clientes: '/exportaciones/clientes-frecuentes', cuentas: '/exportaciones/cuentas-por-cobrar', utilidad: '/exportaciones/utilidad', comisiones: '/exportaciones/comisiones' }
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
      showError(err, 'Error al exportar')
    }
  }

  if (loading) return <PageLoading mensaje="Cargando ventas..." />
  if (errorCargar) return <div className="p-4 rounded-lg bg-red-50 text-red-700"><p>{errorCargar}</p><button onClick={recargar} className="mt-2 min-h-[44px] px-4 py-2 bg-red-100 rounded-lg hover:bg-red-200 active:bg-red-300 text-sm touch-manipulation">Reintentar</button></div>

  return (
    <div className="min-h-0">
      {errorConfig && (
        <div className="p-3 rounded-lg bg-amber-50 text-amber-800 mb-4 text-sm">
          {errorConfig}. Se usará IVA 8% por defecto.
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Ventas</h1>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setTabActivo('listado')} className={`min-h-[44px] px-4 py-2 rounded-lg font-medium touch-manipulation ${tabActivo === 'listado' ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 active:bg-slate-300'}`}>Listado</button>
          <button onClick={() => { setTabActivo('reportes'); cargarReportes() }} className={`min-h-[44px] px-4 py-2 rounded-lg font-medium touch-manipulation ${tabActivo === 'reportes' ? 'bg-primary-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 active:bg-slate-300'}`}>Reportes</button>
          <Link to="/ventas/ingresos" className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 font-medium inline-flex items-center justify-center touch-manipulation">Ingresos</Link>
          <button onClick={abrirNueva} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation">Nueva venta</button>
        </div>
      </div>

      {tabActivo === 'listado' && (
        <>
          <div className="bg-white rounded-lg shadow p-4 mb-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Estado</label>
                <select value={filtros.estado} onChange={(e) => { setFiltros((f) => ({ ...f, estado: e.target.value })); setPagina(1) }} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation w-full sm:w-auto">
                  <option value="">Todos</option>
                  <option value="PENDIENTE">Pendiente</option>
                  <option value="PAGADA">Pagada</option>
                  <option value="CANCELADA">Cancelada</option>
                </select>
              </div>
              <div className="min-w-[140px] sm:min-w-[160px] flex-1 sm:flex-initial">
                <label className="block text-xs text-slate-500 mb-1">Cliente</label>
                <select value={filtros.id_cliente} onChange={(e) => { setFiltros((f) => ({ ...f, id_cliente: e.target.value })); setPagina(1) }} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation w-full">
                  <option value="">Todos</option>
                  {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Fecha desde</label>
                <input type="date" value={filtros.fecha_desde} onChange={(e) => { setFiltros((f) => ({ ...f, fecha_desde: e.target.value })); setPagina(1) }} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Fecha hasta</label>
                <input type="date" value={filtros.fecha_hasta} onChange={(e) => { setFiltros((f) => ({ ...f, fecha_hasta: e.target.value })); setPagina(1) }} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
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
                      <td className="px-4 py-3 text-sm text-slate-600">{formatearFechaSolo(v.fecha)}</td>
                      <td className="px-4 py-3 text-sm text-slate-600">{v.nombre_cliente || '-'}</td>
                      <td className="px-4 py-3 text-sm font-medium text-slate-800">${(v.total ?? 0).toFixed(2)}</td>
                      <td className="px-4 py-3 text-sm"><span className={v.saldo_pendiente > 0 ? 'text-amber-600 font-medium' : ''}>${(v.saldo_pendiente ?? 0).toFixed(2)}</span></td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${v.estado === 'CANCELADA' ? 'bg-slate-200' : v.estado === 'PAGADA' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>{v.estado || 'PENDIENTE'}</span></td>
                      <td className="px-2 sm:px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex gap-1 sm:gap-2 justify-end flex-wrap">
                          {v.estado !== 'CANCELADA' && <button type="button" onClick={() => descargarTicket(v.id_venta)} className="min-h-[40px] px-2 py-1.5 text-sm text-slate-600 hover:text-slate-800 active:bg-slate-100 rounded touch-manipulation">📄</button>}
                          <button type="button" onClick={() => abrirDetalle(v.id_venta)} className="min-h-[40px] px-2 py-1.5 text-sm text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded touch-manipulation">Ver</button>
                          {v.estado !== 'CANCELADA' && <button type="button" onClick={() => abrirModalCancelar(v.id_venta)} className="min-h-[40px] px-2 py-1.5 text-sm text-red-600 hover:text-red-700 active:bg-red-50 rounded touch-manipulation">Cancelar</button>}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPaginas > 1 && (
            <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <p className="text-sm text-slate-600 order-2 sm:order-1">Mostrando {(pagina - 1) * limit + 1} - {Math.min(pagina * limit, totalVentas)} de {totalVentas}</p>
              <div className="flex gap-2 justify-center sm:justify-end order-1 sm:order-2">
                <button type="button" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 touch-manipulation active:bg-slate-50">Anterior</button>
                <span className="min-h-[44px] px-3 py-2 flex items-center text-sm text-slate-700">Pág. {pagina} de {totalPaginas}</span>
                <button type="button" onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))} disabled={pagina >= totalPaginas} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 touch-manipulation active:bg-slate-50">Siguiente</button>
              </div>
            </div>
          )}
        </>
      )}

      {tabActivo === 'reportes' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex flex-wrap gap-3 items-end mb-4">
              <input type="date" value={filtrosReportes.fecha_desde} onChange={(e) => setFiltrosReportes((f) => ({ ...f, fecha_desde: e.target.value }))} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              <input type="date" value={filtrosReportes.fecha_hasta} onChange={(e) => setFiltrosReportes((f) => ({ ...f, fecha_hasta: e.target.value }))} className="px-3 py-2 min-h-[44px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
              <button type="button" onClick={cargarReportes} disabled={cargandoReportes} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{cargandoReportes ? 'Cargando...' : 'Actualizar'}</button>
            </div>
          </div>
          {reporteUtilidad && (
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Reporte de utilidad</h2>
              <p className="text-sm text-slate-600 mb-3">Utilidad bruta = Ingresos - Costo (CMV) - Pérdidas merma. Utilidad neta = Utilidad bruta - Gastos operativos.</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 sm:gap-4 mb-4">
                <div className="p-4 bg-green-50 rounded-lg"><p className="text-xs text-slate-500">Total ingresos</p><p className="text-xl font-bold text-green-700">${(reporteUtilidad.total_ingresos ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p></div>
                <div className="p-4 bg-red-50 rounded-lg"><p className="text-xs text-slate-500">Total costo (CMV)</p><p className="text-xl font-bold text-red-600">${(reporteUtilidad.total_costo ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p></div>
                <div className="p-4 bg-amber-50 rounded-lg"><p className="text-xs text-slate-500">Pérdidas merma</p><p className="text-xl font-bold text-amber-700">${(reporteUtilidad.perdidas_mer ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p></div>
                <div className="p-4 bg-blue-50 rounded-lg"><p className="text-xs text-slate-500">Utilidad bruta</p><p className="text-xl font-bold text-blue-700">${(reporteUtilidad.total_utilidad_bruta ?? reporteUtilidad.total_utilidad ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p></div>
                <div className="p-4 bg-red-50 rounded-lg"><p className="text-xs text-slate-500">Gastos operativos</p><p className="text-xl font-bold text-red-600">${(reporteUtilidad.total_gastos ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p></div>
                <div className="p-4 bg-emerald-50 rounded-lg"><p className="text-xs text-slate-500">Utilidad neta</p><p className="text-xl font-bold text-emerald-700">${(reporteUtilidad.total_utilidad_neta ?? reporteUtilidad.total_utilidad ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Ventas</p><p className="text-xl font-bold">{reporteUtilidad.cantidad_ventas ?? 0}</p></div>
              </div>
              <button type="button" onClick={() => exportarExcel('utilidad')} className="mb-4 min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm touch-manipulation">Exportar utilidad a Excel</button>
              {(reporteUtilidad.detalle?.length ?? 0) > 0 && (
                <div className="overflow-x-auto max-h-64 overflow-y-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs text-slate-500">ID</th>
                        <th className="px-4 py-2 text-left text-xs text-slate-500">Fecha</th>
                        <th className="px-4 py-2 text-right text-xs text-slate-500">Ingresos</th>
                        <th className="px-4 py-2 text-right text-xs text-slate-500">Costo</th>
                        <th className="px-4 py-2 text-right text-xs text-slate-500">Utilidad</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {reporteUtilidad.detalle.map((d) => (
                        <tr key={d.id_venta}>
                          <td className="px-4 py-1.5">{d.id_venta}</td>
                          <td className="px-4 py-1.5">{d.fecha}</td>
                          <td className="px-4 py-1.5 text-right">${(d.ingresos ?? 0).toFixed(2)}</td>
                          <td className="px-4 py-1.5 text-right">${(d.costo ?? 0).toFixed(2)}</td>
                          <td className={`px-4 py-1.5 text-right font-medium ${(d.utilidad ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>${(d.utilidad ?? 0).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
          {reporteComisiones && puedeVerComisiones && (
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Comisiones devengadas</h2>
              <p className="text-sm text-slate-600 mb-3">Comisiones calculadas al quedar ventas como PAGADAS (por fecha de venta). {user?.rol === 'EMPLEADO' || user?.rol === 'TECNICO' ? 'Solo tus comisiones.' : ''}</p>
              <div className="flex flex-wrap gap-3 items-center mb-4">
                <span className="p-3 bg-primary-50 rounded-lg text-primary-800 font-semibold">Total: ${(reporteComisiones.total_comisiones ?? 0).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
                <button type="button" onClick={() => exportarExcel('comisiones')} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm touch-manipulation">Exportar a Excel</button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs text-slate-500">Empleado</th>
                      <th className="px-4 py-2 text-right text-xs text-slate-500">Comisión</th>
                      <th className="px-4 py-2 text-right text-xs text-slate-500">Registros</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(reporteComisiones.empleados || []).map((e) => (
                      <tr key={e.id_usuario}>
                        <td className="px-4 py-2 text-sm font-medium">{e.nombre}</td>
                        <td className="px-4 py-2 text-sm text-right">${(e.total_comision ?? 0).toFixed(2)}</td>
                        <td className="px-4 py-2 text-sm text-right text-slate-500">{e.registros ?? 0}</td>
                      </tr>
                    ))}
                    {(reporteComisiones.empleados?.length ?? 0) === 0 && (
                      <tr><td colSpan={3} className="px-4 py-6 text-center text-slate-500">No hay comisiones en el período</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {estadisticas && (
            <div className="bg-white rounded-lg shadow p-4 sm:p-6">
              <h2 className="text-lg font-semibold text-slate-800 mb-4">Estadísticas</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Total ventas</p><p className="text-xl font-bold">{estadisticas.total_ventas}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Monto total</p><p className="text-xl font-bold">${(estadisticas.monto_total || 0).toFixed(2)}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Promedio</p><p className="text-xl font-bold">${(estadisticas.promedio_por_venta || 0).toFixed(2)}</p></div>
                <div className="p-4 bg-slate-50 rounded-lg"><p className="text-xs text-slate-500">Pend/Pag/Can</p><p className="text-sm font-medium">{estadisticas.por_estado?.pendientes ?? 0} / {estadisticas.por_estado?.pagadas ?? 0} / {estadisticas.por_estado?.canceladas ?? 0}</p></div>
              </div>
              <button type="button" onClick={() => exportarExcel('ventas')} className="mt-4 min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 text-sm touch-manipulation">📥 Exportar ventas a Excel</button>
            </div>
          )}
          <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
            <div className="p-4 flex flex-col sm:flex-row justify-between gap-2"><h2 className="text-lg font-semibold">Productos más vendidos</h2><button type="button" onClick={() => exportarExcel('productos')} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg text-sm touch-manipulation self-start sm:self-center">📥 Exportar</button></div>
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs text-slate-500">Producto</th><th className="px-4 py-3 text-right text-xs text-slate-500">Cantidad</th><th className="px-4 py-3 text-right text-xs text-slate-500">Monto</th></tr></thead>
              <tbody>{productosVendidos.map((p, i) => <tr key={i}><td className="px-4 py-2 text-sm">{p.producto || p.nombre || '-'}</td><td className="px-4 py-2 text-sm text-right">{p.cantidad ?? p.cantidad_vendida ?? 0}</td><td className="px-4 py-2 text-sm text-right">${((p.monto ?? p.monto_total) || 0).toFixed(2)}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
            <div className="p-4 flex flex-col sm:flex-row justify-between gap-2"><h2 className="text-lg font-semibold">Clientes frecuentes</h2><button type="button" onClick={() => exportarExcel('clientes')} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg text-sm touch-manipulation self-start sm:self-center">📥 Exportar</button></div>
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs text-slate-500">Cliente</th><th className="px-4 py-3 text-right text-xs text-slate-500">Ventas</th><th className="px-4 py-3 text-right text-xs text-slate-500">Total</th></tr></thead>
              <tbody>{clientesFrecuentes.map((c, i) => <tr key={i}><td className="px-4 py-2 text-sm">{c.cliente ?? c.nombre ?? '-'}</td><td className="px-4 py-2 text-sm text-right">{c.ventas ?? c.total_ventas ?? 0}</td><td className="px-4 py-2 text-sm text-right">${((c.total ?? c.monto_total) || 0).toFixed(2)}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
            <div className="p-4 flex flex-col sm:flex-row justify-between gap-2"><h2 className="text-lg font-semibold">Cuentas por cobrar</h2><button type="button" onClick={() => exportarExcel('cuentas')} className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg text-sm touch-manipulation self-start sm:self-center">📥 Exportar</button></div>
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left text-xs text-slate-500">ID</th><th className="px-4 py-3 text-left text-xs text-slate-500">Cliente</th><th className="px-4 py-3 text-right text-xs text-slate-500">Total</th><th className="px-4 py-3 text-right text-xs text-slate-500">Saldo</th></tr></thead>
              <tbody>{cuentasCobrar.map((v) => <tr key={v.id_venta}><td className="px-4 py-2 text-sm">{v.id_venta}</td><td className="px-4 py-2 text-sm">{v.nombre_cliente || '-'}</td><td className="px-4 py-2 text-sm text-right">${(v.total || 0).toFixed(2)}</td><td className="px-4 py-2 text-sm text-right font-medium text-amber-700">${(v.saldo_pendiente ?? 0).toFixed(2)}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      )}

      <Modal titulo="Detalle de venta" abierto={modalDetalleAbierto} onCerrar={() => { setModalDetalleAbierto(false); setVentaDetalle(null); setPagoForm({ monto: '', metodo: 'EFECTIVO', referencia: '' }); setOrdenSeleccionadaVincular('') }}>
        {cargandoDetalle ? <p className="text-slate-500 py-4">Cargando...</p> : ventaDetalle ? (
          <div className="space-y-4">
            <p><strong>ID:</strong> {ventaDetalle.id_venta}</p>
            <p><strong>Fecha:</strong> {obtenerFechaVentaDetalle(ventaDetalle)}</p>
            <p><strong>Cliente:</strong> {ventaDetalle.nombre_cliente || '-'}</p>
            <p><strong>Total:</strong> ${(ventaDetalle.total ?? 0).toFixed(2)}</p>
            <p><strong>Saldo pendiente:</strong> <span className={ventaDetalle.saldo_pendiente > 0 ? 'text-amber-600 font-medium' : 'text-green-600'}>${(ventaDetalle.saldo_pendiente ?? 0).toFixed(2)}</span></p>
            <p><strong>Estado:</strong> {ventaDetalle.estado || '-'}</p>
            {ventaDetalle.orden_vinculada && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <h4 className="font-medium mb-1">Orden de trabajo vinculada</h4>
                <p className="text-sm text-slate-700">{ventaDetalle.orden_vinculada.numero_orden} — {ventaDetalle.orden_vinculada.cliente_nombre || '-'} / {ventaDetalle.orden_vinculada.vehiculo_info || '-'} ({ventaDetalle.orden_vinculada.estado})</p>
                {ventaDetalle.estado !== 'CANCELADA' && (
                  <button onClick={desvincularOrden} disabled={vinculando} className="mt-2 text-sm text-amber-600 hover:text-amber-700 disabled:opacity-50">Desvincular orden</button>
                )}
              </div>
            )}
            {!ventaDetalle.orden_vinculada && ventaDetalle.estado !== 'CANCELADA' && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <h4 className="font-medium mb-2">Vincular orden de trabajo</h4>
                <div className="flex flex-wrap gap-2 items-end">
                  <div className="min-w-[200px]">
                    <label className="block text-xs text-slate-500 mb-1">Orden (ENTREGADA/COMPLETADA)</label>
                    <select value={ordenSeleccionadaVincular} onChange={(e) => setOrdenSeleccionadaVincular(e.target.value)} onFocus={cargarOrdenesDisponibles} className="w-full px-3 py-2 border rounded-lg text-sm">
                      <option value="">— Seleccionar —</option>
                      {ordenesDisponibles.map((o) => (
                        <option key={o.id} value={o.id}>{o.numero_orden} — {o.cliente_nombre || '-'} ({o.vehiculo_info || '-'})</option>
                      ))}
                    </select>
                  </div>
                  <button onClick={vincularOrden} disabled={vinculando || !ordenSeleccionadaVincular} className="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm hover:bg-slate-700 disabled:opacity-50">Vincular</button>
                </div>
              </div>
            )}
            {ventaDetalle.detalles?.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Productos / Servicios</h4>
                <ul className="list-disc pl-4">{ventaDetalle.detalles.map((d, i) => <li key={i}>{d.descripcion} x{d.cantidad} ${(d.subtotal ?? 0).toFixed(2)}</li>)}</ul>
              </div>
            )}
            {(ventaDetalle.pagos?.length ?? 0) > 0 && (
              <div>
                <h4 className="font-medium mb-2">Historial de pagos</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm border border-slate-200 rounded-lg overflow-hidden">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs text-slate-500">Fecha</th>
                        <th className="px-3 py-2 text-left text-xs text-slate-500">Método</th>
                        <th className="px-3 py-2 text-right text-xs text-slate-500">Monto</th>
                        <th className="px-3 py-2 text-left text-xs text-slate-500">Referencia</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {ventaDetalle.pagos.map((p) => (
                        <tr key={p.id_pago}>
                          <td className="px-3 py-2 text-slate-700">{formatearFechaHora(p.fecha)}</td>
                          <td className="px-3 py-2 text-slate-700">{p.metodo || '-'}</td>
                          <td className="px-3 py-2 text-right font-medium text-green-700">${(p.monto ?? 0).toFixed(2)}</td>
                          <td className="px-3 py-2 text-slate-600">{p.referencia || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {ventaDetalle.estado !== 'CANCELADA' && (
              <>
                <div className="flex gap-2 flex-wrap">
                  <button onClick={() => descargarTicket(ventaDetalle.id_venta)} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700">📄 Descargar ticket</button>
                  <button onClick={abrirEditar} className="px-4 py-2 bg-slate-600 text-white rounded-lg text-sm hover:bg-slate-700">✏️ Editar venta</button>
                  <button onClick={() => abrirModalCancelar(ventaDetalle.id_venta)} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">❌ Cancelar venta</button>
                </div>
                {ventaDetalle.saldo_pendiente > 0 && (
                  <div className="mt-4 p-4 border border-slate-200 rounded-lg bg-slate-50">
                    <h4 className="font-medium text-slate-800 mb-2">Registrar pago</h4>
                    <p className="text-sm text-slate-600 mb-2">Requiere tener un turno de caja abierto (menú Caja).</p>
                    <div className="flex flex-wrap gap-3 items-end">
                      <div>
                        <label className="block text-xs text-slate-500 mb-1">Monto</label>
                        <input type="number" step={0.01} min={0} max={ventaDetalle.saldo_pendiente} value={pagoForm.monto} onChange={(e) => setPagoForm((f) => ({ ...f, monto: e.target.value }))} className="w-28 px-3 py-2 border rounded-lg text-sm" placeholder="0.00" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-500 mb-1">Método</label>
                        <select value={pagoForm.metodo} onChange={(e) => setPagoForm((f) => ({ ...f, metodo: e.target.value }))} className="px-3 py-2 border rounded-lg text-sm">
                          <option value="EFECTIVO">Efectivo</option>
                          <option value="TARJETA">Tarjeta</option>
                          <option value="TRANSFERENCIA">Transferencia</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-slate-500 mb-1">Referencia (opc.)</label>
                        <input type="text" value={pagoForm.referencia} onChange={(e) => setPagoForm((f) => ({ ...f, referencia: e.target.value }))} className="w-32 px-3 py-2 border rounded-lg text-sm" placeholder="Opcional" />
                      </div>
                      <button onClick={registrarPago} disabled={enviandoPago || !esNumeroValido(pagoForm.monto) || aNumero(pagoForm.monto) <= 0} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 inline-flex items-center gap-2">💳 {enviandoPago ? <><LoadingSpinner size="sm" /> Guardando...</> : 'Registrar pago'}</button>
                    </div>
                  </div>
                )}
              </>
            )}
            {ventaDetalle.estado === 'CANCELADA' && ventaDetalle.motivo_cancelacion && (
              <div className="mt-3 p-3 bg-red-50 rounded-lg">
                <p className="text-sm font-medium text-slate-700">Motivo de cancelación:</p>
                <p className="text-sm text-slate-600 mt-1">{ventaDetalle.motivo_cancelacion}</p>
              </div>
            )}
          </div>
        ) : null}
      </Modal>

      <Modal titulo="Editar venta" abierto={modalEditarAbierto} onCerrar={() => setModalEditarAbierto(false)}>
        <form onSubmit={guardarEditar} className="space-y-4">
          {errorEditar && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{errorEditar}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cliente (opcional)</label>
            <select value={formEditar.id_cliente || ''} onChange={(e) => setFormEditar({ ...formEditar, id_cliente: e.target.value ? aEntero(e.target.value) : null, id_vehiculo: null })} onFocus={cargarDatosModal} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="">— Sin cliente —</option>
              {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
            </select>
          </div>
          {formEditar.id_cliente && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Vehículo (opcional)</label>
              <select value={formEditar.id_vehiculo || ''} onChange={(e) => setFormEditar({ ...formEditar, id_vehiculo: e.target.value ? aEntero(e.target.value) : null })} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
                <option value="">-- Sin vehículo --</option>
                {vehiculos.map((v) => <option key={v.id_vehiculo} value={v.id_vehiculo}>{v.marca} {v.modelo} {v.anio}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Vendedor (opcional, para comisiones)</label>
            <select value={formEditar.id_vendedor || ''} onChange={(e) => setFormEditar({ ...formEditar, id_vendedor: e.target.value ? aEntero(e.target.value) : null })} onFocus={cargarDatosModal} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="">— Sin asignar —</option>
              {(usuarios || []).filter((u) => u.activo !== false).map((u) => (
                <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="requiere_factura_editar" checked={formEditar.requiere_factura} onChange={(e) => setFormEditar({ ...formEditar, requiere_factura: e.target.checked })} className="rounded border-slate-300" />
            <label htmlFor="requiere_factura_editar" className="text-sm font-medium text-slate-700">Requiere factura (aplica {config.iva_porcentaje ?? 8}% IVA)</label>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Comentarios (aparecen en el ticket)</label>
            <textarea value={formEditar.comentarios || ''} onChange={(e) => setFormEditar({ ...formEditar, comentarios: e.target.value })} rows={2} placeholder="Ej: Próxima cita en 3 meses, revisar frenos..." className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Agregar producto/servicio</label>
            <div className="flex gap-2 flex-wrap items-end">
              <select value={detalleActualEditar.tipo} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, tipo: e.target.value, id_item: '' })} className="px-3 py-2 border rounded-lg text-sm">
                <option value="PRODUCTO">Producto</option>
                <option value="SERVICIO">Servicio</option>
              </select>
              <select value={detalleActualEditar.id_item} onChange={(e) => {
                const id = e.target.value
                const idNum = aEntero(id)
                const item = detalleActualEditar.tipo === 'PRODUCTO' ? repuestos.find((r) => r.id_repuesto === idNum) : servicios.find((s) => (s.id ?? s.id_servicio) === idNum)
                setDetalleActualEditar({ ...detalleActualEditar, id_item: id, descripcion: item ? (item.nombre || `${item.codigo || ''} ${item.nombre || ''}`.trim()) : '', precio_unitario: item ? aNumero(item.precio_venta ?? item.precio_base) : 0 })
              }} className="px-3 py-2 border rounded-lg text-sm min-w-[140px]">
                <option value="">{detalleActualEditar.tipo === 'PRODUCTO' ? 'Producto...' : 'Servicio...'}</option>
                {(detalleActualEditar.tipo === 'PRODUCTO' ? repuestos : servicios).map((x) => (
                  <option key={x.id_repuesto ?? x.id ?? x.id_servicio} value={x.id_repuesto ?? x.id ?? x.id_servicio}>{x.codigo || ''} {x.nombre}</option>
                ))}
              </select>
              <input type="text" value={detalleActualEditar.descripcion} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, descripcion: e.target.value })} placeholder="Descripción" className="px-3 py-2 border rounded-lg text-sm flex-1 min-w-[120px]" />
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Cantidad</label>
                <input type="number" min={0.001} step={0.001} value={detalleActualEditar.cantidad} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, cantidad: Math.max(0.001, aNumero(e.target.value, 1)) })} className="w-20 px-2 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Precio de venta</label>
                <input type="number" min={0} step={0.01} value={detalleActualEditar.precio_unitario} onChange={(e) => setDetalleActualEditar({ ...detalleActualEditar, precio_unitario: aNumero(e.target.value) })} className="w-24 px-2 py-2 border rounded-lg text-sm" />
              </div>
              <button type="button" onClick={agregarDetalleEditar} className="px-3 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300 self-end">+ Agregar</button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Detalles (puedes quitar y agregar)</label>
            <ul className="border rounded-lg divide-y">
              {formEditar.detalles.map((d, i) => (
                <li key={i} className="px-3 py-2 flex justify-between">
                  <span>{d.descripcion} x{d.cantidad} @ ${d.precio_unitario} = ${(d.cantidad * d.precio_unitario).toFixed(2)}</span>
                  <button type="button" onClick={() => quitarDetalleEditar(i)} className="text-red-600 text-sm">Quitar</button>
                </li>
              ))}
            </ul>
            {formEditar.detalles.length > 0 && (() => {
              const sub = formEditar.detalles.reduce((s, d) => s + d.cantidad * d.precio_unitario, 0)
              const tot = formEditar.requiere_factura ? sub * ivaFactor : sub
              return <p className="mt-2 font-medium">Total: ${tot.toFixed(2)}{formEditar.requiere_factura ? ` (con IVA ${config.iva_porcentaje ?? 8}%)` : ''}</p>
            })()}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalEditarAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviandoEditar || !formEditar.detalles.length} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 inline-flex items-center gap-2">{enviandoEditar ? <><LoadingSpinner size="sm" /> Guardando...</> : 'Guardar cambios'}</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Cancelar venta" abierto={modalCancelarAbierto} onCerrar={() => { setModalCancelarAbierto(false); setVentaACancelar(null); setVentaACancelarDetalle(null); setMotivoCancelacion(''); setProductosCancelacion([]) }}>
        <div className="space-y-4">
          <p className="text-slate-600">Se marcará esta venta como CANCELADA. Indica el motivo de la cancelación:</p>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Motivo <span className="text-red-500">*</span></label>
            <textarea
              value={motivoCancelacion}
              onChange={(e) => setMotivoCancelacion(e.target.value)}
              placeholder="Ej: Error en el pedido, cliente desistió, duplicado... (mín. 5 caracteres)"
              rows={3}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {productosCancelacion.length > 0 && (
            <div className="border border-amber-200 rounded-lg bg-amber-50/50 p-4 space-y-3">
              <p className="text-sm font-medium text-amber-900">Venta con productos: indica para cada uno si es reutilizable o merma</p>
              <button type="button" onClick={aplicarConsumiblesMerma} className="text-xs px-2 py-1 bg-amber-200 text-amber-900 rounded hover:bg-amber-300">
                Marcar consumibles (aceite, filtros, etc.) como merma
              </button>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {productosCancelacion.map((p, idx) => (
                  <div key={p.id_detalle} className="bg-white rounded border border-slate-200 p-2 text-sm">
                    <p className="font-medium text-slate-800 mb-1">{p.descripcion} × {p.cantidad} {p.es_consumible && <span className="text-amber-600 text-xs">(consumible)</span>}</p>
                    <div className="flex flex-wrap gap-4 items-center">
                      <label className="flex items-center gap-1">
                        <span className="text-slate-600">Reutilizable:</span>
                        <input type="number" min={0} max={p.cantidad} value={p.cantidad_reutilizable ?? 0} onChange={(e) => actualizarProductoCancelacion(idx, 'cantidad_reutilizable', e.target.value)} className="w-14 px-2 py-0.5 border rounded text-sm" />
                      </label>
                      <label className="flex items-center gap-1">
                        <span className="text-slate-600">Merma:</span>
                        <input type="number" min={0} max={p.cantidad} value={p.cantidad_mer ?? 0} onChange={(e) => actualizarProductoCancelacion(idx, 'cantidad_mer', e.target.value)} className="w-14 px-2 py-0.5 border rounded text-sm" />
                      </label>
                      {(p.cantidad_mer ?? 0) > 0 && (
                        <label className="flex-1 min-w-[180px]">
                          <span className="text-slate-600 text-xs">Motivo merma:</span>
                          <input type="text" value={p.motivo_mer || ''} onChange={(e) => actualizarProductoCancelacion(idx, 'motivo_mer', e.target.value)} placeholder="Ej: aceite ya usado" className="w-full px-2 py-0.5 border rounded text-sm" />
                        </label>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => { setModalCancelarAbierto(false); setVentaACancelar(null); setVentaACancelarDetalle(null); setMotivoCancelacion(''); setProductosCancelacion([]) }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">No cancelar</button>
            <button type="button" onClick={confirmarCancelar} disabled={!motivoCancelacion.trim() || motivoCancelacion.trim().length < 5} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed">Confirmar cancelación</button>
          </div>
        </div>
      </Modal>

      <Modal titulo="Nueva venta" abierto={modalAbierto} onCerrar={() => setModalAbierto(false)}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Cliente (opcional)</label>
            <select value={form.id_cliente || ''} onChange={(e) => setForm({ ...form, id_cliente: e.target.value ? aEntero(e.target.value) : null })} onFocus={cargarDatosModal} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="">— Sin cliente —</option>
              {clientes.map((c) => <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>)}
            </select>
          </div>
          {form.id_cliente && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Vehículo (opcional)</label>
              <select value={form.id_vehiculo || ''} onChange={(e) => setForm({ ...form, id_vehiculo: e.target.value ? aEntero(e.target.value) : null })} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
                <option value="">-- Sin vehículo --</option>
                {vehiculos.map((v) => <option key={v.id_vehiculo} value={v.id_vehiculo}>{v.marca} {v.modelo} {v.anio}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Vendedor (opcional, para comisiones)</label>
            <select value={form.id_vendedor || ''} onChange={(e) => setForm({ ...form, id_vendedor: e.target.value ? aEntero(e.target.value) : null })} onFocus={cargarDatosModal} className="w-full px-4 py-2 border border-slate-300 rounded-lg">
              <option value="">— Usuario actual —</option>
              {(usuarios || []).filter((u) => u.activo !== false).map((u) => (
                <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Agregar producto/servicio</label>
            <div className="flex gap-2 flex-wrap items-end">
              <select value={detalleActual.tipo} onChange={(e) => setDetalleActual({ ...detalleActual, tipo: e.target.value, id_item: '' })} className="px-3 py-2 border rounded-lg text-sm">
                <option value="PRODUCTO">Producto</option>
                <option value="SERVICIO">Servicio</option>
              </select>
              <select value={detalleActual.id_item} onChange={(e) => {
                const id = e.target.value
                const idNum = aEntero(id)
                const item = detalleActual.tipo === 'PRODUCTO' ? repuestos.find(r => r.id_repuesto === idNum) : servicios.find(s => (s.id ?? s.id_servicio) === idNum)
                setDetalleActual({ ...detalleActual, id_item: id, descripcion: item ? (item.nombre || `${item.codigo || ''} ${item.nombre || ''}`.trim()) : '', precio_unitario: item ? aNumero(item.precio_venta ?? item.precio_base) : 0 })
              }} className="px-3 py-2 border rounded-lg text-sm min-w-[140px]">
                <option value="">{detalleActual.tipo === 'PRODUCTO' ? 'Producto...' : 'Servicio...'}</option>
                {(detalleActual.tipo === 'PRODUCTO' ? repuestos : servicios).map((x) => (
                  <option key={x.id_repuesto ?? x.id ?? x.id_servicio} value={x.id_repuesto ?? x.id ?? x.id_servicio}>{x.codigo || ''} {x.nombre}</option>
                ))}
              </select>
              <input type="text" value={detalleActual.descripcion} onChange={(e) => setDetalleActual({ ...detalleActual, descripcion: e.target.value })} placeholder="Descripción" className="px-3 py-2 border rounded-lg text-sm flex-1 min-w-[120px]" />
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Cantidad</label>
                <input type="number" min={0.001} step={0.001} value={detalleActual.cantidad} onChange={(e) => setDetalleActual({ ...detalleActual, cantidad: Math.max(0.001, aNumero(e.target.value, 1)) })} className="w-20 px-2 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-0.5">Precio de venta</label>
                <input type="number" min={0} step={0.01} value={detalleActual.precio_unitario} onChange={(e) => setDetalleActual({ ...detalleActual, precio_unitario: aNumero(e.target.value) })} className="w-24 px-2 py-2 border rounded-lg text-sm" />
              </div>
              <button type="button" onClick={agregarDetalle} className="px-3 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300 self-end">+ Agregar</button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="requiere_factura" checked={form.requiere_factura} onChange={(e) => setForm({ ...form, requiere_factura: e.target.checked })} className="rounded border-slate-300" />
            <label htmlFor="requiere_factura" className="text-sm font-medium text-slate-700">Requiere factura (aplica {config.iva_porcentaje ?? 8}% IVA)</label>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Comentarios (aparecen en el ticket)</label>
            <textarea value={form.comentarios || ''} onChange={(e) => setForm({ ...form, comentarios: e.target.value })} rows={2} placeholder="Ej: Próxima cita en 3 meses, revisar frenos..." className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm" />
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
            {form.detalles.length > 0 && (() => {
              const sub = form.detalles.reduce((s, d) => s + d.cantidad * d.precio_unitario, 0)
              const tot = form.requiere_factura ? sub * ivaFactor : sub
              return <p className="mt-2 font-medium">Total: ${tot.toFixed(2)}{form.requiere_factura ? ` (con IVA ${config.iva_porcentaje ?? 8}%)` : ''}</p>
            })()}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalAbierto(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">Cancelar</button>
            <button type="submit" disabled={enviando || !form.detalles.length} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 inline-flex items-center gap-2">{enviando ? <><LoadingSpinner size="sm" /> Guardando...</> : 'Guardar venta'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
