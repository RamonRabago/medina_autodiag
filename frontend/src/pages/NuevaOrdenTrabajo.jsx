import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import Modal from '../components/Modal'
import { useAuth } from '../context/AuthContext'
import { aNumero, aEntero } from '../utils/numeros'
import PageLoading from '../components/PageLoading'
import { normalizeDetail, showError } from '../utils/toast'

const PASOS = [
  { id: 1, titulo: 'Cliente y vehículo', desc: 'Datos del cliente y vehículo' },
  { id: 2, titulo: 'Asignación', desc: 'Técnico, prioridad y fecha' },
  { id: 3, titulo: 'Diagnóstico', desc: 'Revisión inicial y observaciones' },
  { id: 4, titulo: 'Productos y servicios', desc: 'Detalle de la orden' },
]

export default function NuevaOrdenTrabajo() {
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  useEffect(() => {
    if (!authLoading && user?.rol === 'TECNICO') {
      navigate('/ordenes-trabajo', { replace: true })
    }
  }, [authLoading, user?.rol, navigate])

  const [paso, setPaso] = useState(1)
  const [form, setForm] = useState({
    cliente_id: '',
    vehiculo_id: '',
    tecnico_id: '',
    prioridad: 'NORMAL',
    diagnostico_inicial: '',
    observaciones_cliente: '',
    requiere_autorizacion: false,
    cliente_proporciono_refacciones: false,
    servicios: [],
    repuestos: [],
  })
  const [detalleActual, setDetalleActual] = useState({ tipo: 'SERVICIO', id_item: '', descripcion_libre: '', repuesto_tipo: 'catalogo', cantidad: 1, precio_unitario: 0, precio_compra_estimado: 0 })
  const [clienteBuscar, setClienteBuscar] = useState('')
  const [mostrarDropdownCliente, setMostrarDropdownCliente] = useState(false)
  const [clientes, setClientes] = useState([])
  const [vehiculos, setVehiculos] = useState([])
  const [tecnicos, setTecnicos] = useState([])
  const [servicios, setServicios] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [loading, setLoading] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [modalVehiculo, setModalVehiculo] = useState(false)
  const [formVehiculo, setFormVehiculo] = useState({ marca: '', modelo: '', anio: new Date().getFullYear(), color: '', numero_serie: '', motor: '' })
  const [enviandoVehiculo, setEnviandoVehiculo] = useState(false)
  const [modalServicioRepuestos, setModalServicioRepuestos] = useState({ abierto: false, servicio: null })
  const [modalConfirmarCrear, setModalConfirmarCrear] = useState(false)
  const [config, setConfig] = useState({ markup_porcentaje: 20 })

  useEffect(() => {
    api.get('/config').then((r) => setConfig(r.data || { markup_porcentaje: 20 })).catch(() => {})
  }, [])

  const aplicarMarkupEnDetalle = () => {
    const pc = Number(detalleActual.precio_compra_estimado)
    if (!pc || pc <= 0) return
    const markup = 1 + (config.markup_porcentaje || 20) / 100
    const pv = Math.round(pc * markup * 100) / 100
    setDetalleActual((d) => ({ ...d, precio_unitario: pv }))
  }

  useEffect(() => {
    const cargar = async () => {
      setLoading(true)
      const [rClientes, rServicios, rRepuestos, rUsuarios] = await Promise.allSettled([
        api.get('/clientes/', { params: { limit: 500, skip: 0 } }),
        api.get('/servicios/', { params: { limit: 100 } }),
        api.get('/repuestos/', { params: { limit: 500 } }),
        api.get('/usuarios/'),
      ])
      if (rClientes.status === 'fulfilled') {
        const d = rClientes.value?.data
        setClientes(Array.isArray(d) ? d : d?.clientes ?? [])
      } else setClientes([])
      if (rServicios.status === 'fulfilled') {
        const d = rServicios.value?.data
        setServicios(d?.servicios ?? d ?? [])
      } else setServicios([])
      if (rRepuestos.status === 'fulfilled') {
        const d = rRepuestos.value?.data
        setRepuestos(Array.isArray(d) ? d : d?.items ?? d?.repuestos ?? [])
      } else setRepuestos([])
      if (rUsuarios.status === 'fulfilled') {
        const users = Array.isArray(rUsuarios.value?.data) ? rUsuarios.value.data : []
        setTecnicos(users.filter((u) => u.rol === 'TECNICO'))
      } else setTecnicos([])
      setLoading(false)
    }
    cargar()
  }, [])

  useEffect(() => {
    if (form.cliente_id) {
      api.get(`/vehiculos/cliente/${form.cliente_id}`)
        .then((r) => setVehiculos(Array.isArray(r.data) ? r.data : []))
        .catch((err) => { showError(err, 'Error al cargar vehículos'); setVehiculos([]) })
    } else {
      setVehiculos([])
    }
  }, [form.cliente_id])

  const abrirAgregarVehiculo = () => {
    setFormVehiculo({ marca: '', modelo: '', anio: new Date().getFullYear(), color: '', numero_serie: '', motor: '' })
    setModalVehiculo(true)
  }

  const handleVehiculoSubmit = async (e) => {
    e.preventDefault()
    if (!form.cliente_id) return
    setEnviandoVehiculo(true)
    try {
      const res = await api.post('/vehiculos/', {
        id_cliente: aEntero(form.cliente_id),
        marca: formVehiculo.marca.trim(),
        modelo: formVehiculo.modelo.trim(),
        anio: aEntero(formVehiculo.anio),
        color: formVehiculo.color?.trim() || null,
        numero_serie: formVehiculo.numero_serie?.trim() || null,
        motor: formVehiculo.motor?.trim() || null,
      })
      const nuevo = res.data
      setVehiculos((prev) => [...prev, nuevo])
      setForm((prev) => ({ ...prev, vehiculo_id: String(nuevo.id_vehiculo) }))
      setModalVehiculo(false)
    } catch (err) {
      showError(err, 'Error al agregar vehículo')
    } finally {
      setEnviandoVehiculo(false)
    }
  }

  const puedeAgregar =
    (detalleActual.tipo === 'SERVICIO' && detalleActual.id_item && aEntero(detalleActual.cantidad, 1) >= 1) ||
    (detalleActual.tipo === 'PRODUCTO' && detalleActual.repuesto_tipo === 'catalogo' && detalleActual.id_item && aEntero(detalleActual.cantidad, 1) >= 1) ||
    (detalleActual.tipo === 'PRODUCTO' && detalleActual.repuesto_tipo === 'libre' && (detalleActual.descripcion_libre || '').trim() && aEntero(detalleActual.cantidad, 1) >= 1)
  const servicioSeleccionadoRequiereRepuestos =
    detalleActual.tipo === 'SERVICIO' &&
    detalleActual.id_item &&
    (() => {
      const s = servicios.find((x) => (x.id ?? x.id_servicio) === aEntero(detalleActual.id_item))
      return !!s?.requiere_repuestos
    })()
  const hayServiciosQueRequierenRepuestos = form.servicios?.some((fs) => {
    const s = servicios.find((x) => (x.id ?? x.id_servicio) === fs.servicio_id)
    return !!s?.requiere_repuestos
  })
  const requiereAdvertenciaRepuestos =
    hayServiciosQueRequierenRepuestos && (form.repuestos?.length || 0) === 0 && !form.cliente_proporciono_refacciones

  const agregarServicioConfirmado = (idItem, cantidad, precio, s) => {
    setForm({
      ...form,
      servicios: [...form.servicios, { servicio_id: idItem, cantidad, precio_unitario: precio || (s ? Number(s.precio_base) : 0) }],
    })
    setDetalleActual({ tipo: 'SERVICIO', id_item: '', cantidad: 1, precio_unitario: 0 })
    setModalServicioRepuestos({ abierto: false, servicio: null })
  }

  const agregarDetalle = () => {
    if (!puedeAgregar) return
    const idItem = aEntero(detalleActual.id_item)
    const cantidad = aEntero(detalleActual.cantidad, 1)
    const precio = Number(detalleActual.precio_unitario) || 0
    if (detalleActual.tipo === 'SERVICIO') {
      const s = servicios.find((x) => (x.id ?? x.id_servicio) === idItem)
      if (s?.requiere_repuestos && (form.repuestos?.length || 0) === 0 && !form.cliente_proporciono_refacciones) {
        setModalServicioRepuestos({ abierto: true, servicio: { idItem, cantidad, precio, s } })
        return
      }
      agregarServicioConfirmado(idItem, cantidad, precio, s)
    } else {
      if (detalleActual.repuesto_tipo === 'libre') {
        const desc = (detalleActual.descripcion_libre || '').trim()
        const precio = Number(detalleActual.precio_unitario) || 0
        const precioCompra = Number(detalleActual.precio_compra_estimado) || null
        setForm({
          ...form,
          repuestos: [...form.repuestos, { descripcion_libre: desc, cantidad, precio_unitario: precio, precio_compra_estimado: precioCompra || undefined }],
        })
        setDetalleActual({ ...detalleActual, descripcion_libre: '', cantidad: 1, precio_unitario: 0, precio_compra_estimado: 0 })
      } else {
        const r = repuestos.find((x) => (x.id_repuesto ?? x.id) === idItem)
        const precioCompra = r?.precio_compra != null ? Number(r.precio_compra) : null
        setForm({
          ...form,
          repuestos: [...form.repuestos, { repuesto_id: idItem, cantidad, precio_unitario: precio || (r ? Number(r.precio_venta) : 0), precio_compra_estimado: precioCompra }],
        })
        setDetalleActual({ ...detalleActual, id_item: '', cantidad: 1, precio_unitario: 0 })
      }
    }
  }
  const quitarServicio = (idx) => setForm({ ...form, servicios: form.servicios.filter((_, i) => i !== idx) })
  const quitarRepuesto = (idx) => setForm({ ...form, repuestos: form.repuestos.filter((_, i) => i !== idx) })

  const tieneProductosOServicios = (form.servicios?.length || 0) > 0 || (form.repuestos?.length || 0) > 0
  const diagnosticoOK = (form.diagnostico_inicial || '').trim().length > 0
  const observacionesOK = (form.observaciones_cliente || '').trim().length > 0
  const puedeGuardar = tieneProductosOServicios && diagnosticoOK && observacionesOK

  const validarPaso1 = () => form.cliente_id && form.vehiculo_id
  const validarPaso2 = () => true
  const validarPaso3 = () => diagnosticoOK && observacionesOK
  const validarPaso4 = () => puedeGuardar

  const puedeAvanzar = () => {
    if (paso === 1) return validarPaso1()
    if (paso === 2) return validarPaso2()
    if (paso === 3) return validarPaso3()
    if (paso === 4) return validarPaso4()
    return false
  }

  const handleSiguiente = () => {
    setError('')
    if (paso === 1 && !validarPaso1()) {
      setError('Selecciona cliente y vehículo.')
      return
    }
    if (paso === 3 && !validarPaso3()) {
      setError('Completa diagnóstico inicial y observaciones del cliente.')
      return
    }
    if (paso < 4) setPaso((p) => p + 1)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.vehiculo_id || !form.cliente_id) {
      setError('Selecciona cliente y vehículo')
      return
    }
    if (!tieneProductosOServicios) {
      setError('Debes agregar al menos un producto o servicio a la orden.')
      return
    }
    const diag = (form.diagnostico_inicial || '').trim()
    const obs = (form.observaciones_cliente || '').trim()
    if (!diag) {
      setError('El diagnóstico inicial es obligatorio.')
      return
    }
    if (!obs) {
      setError('Las observaciones del cliente son obligatorias.')
      return
    }
    if (requiereAdvertenciaRepuestos) {
      setModalConfirmarCrear(true)
      return
    }
    ejecutarCrearOrden()
  }

  const ejecutarCrearOrden = async () => {
    setModalConfirmarCrear(false)
    setEnviando(true)
    try {
      await api.post('/ordenes-trabajo/', {
        vehiculo_id: aEntero(form.vehiculo_id),
        cliente_id: aEntero(form.cliente_id),
        tecnico_id: form.tecnico_id ? aEntero(form.tecnico_id) : null,
        prioridad: form.prioridad,
        diagnostico_inicial: form.diagnostico_inicial || null,
        observaciones_cliente: form.observaciones_cliente || null,
        requiere_autorizacion: form.requiere_autorizacion,
        cliente_proporciono_refacciones: !!form.cliente_proporciono_refacciones,
        servicios: form.servicios.length ? form.servicios.map((s) => ({ servicio_id: s.servicio_id, cantidad: s.cantidad || 1, precio_unitario: s.precio_unitario || null })) : [],
        repuestos: form.repuestos.length ? form.repuestos.map((r) => {
          const base = { cantidad: r.cantidad || 1, precio_unitario: r.precio_unitario ?? null, precio_compra_estimado: r.precio_compra_estimado ?? null }
          if (r.descripcion_libre?.trim()) {
            return { ...base, descripcion_libre: r.descripcion_libre.trim() }
          }
          return { ...base, repuesto_id: r.repuesto_id }
        }) : [],
      })
      navigate('/ordenes-trabajo')
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al crear orden')
    } finally {
      setEnviando(false)
    }
  }

  if (authLoading || user?.rol === 'TECNICO') return null
  if (loading) return <PageLoading mensaje="Cargando datos..." />

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6 flex items-center gap-4">
        <Link to="/ordenes-trabajo" className="text-slate-600 hover:text-slate-800 text-sm font-medium">
          ← Volver a órdenes
        </Link>
        <h1 className="text-2xl font-bold text-slate-800">Nueva orden de trabajo</h1>
      </div>

      {/* Indicador de pasos */}
      <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
        {PASOS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPaso(p.id)}
            className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${
              paso === p.id ? 'bg-primary-600 text-white' : paso > p.id ? 'bg-primary-100 text-primary-700' : 'bg-slate-100 text-slate-500'
            }`}
          >
            {p.id}. {p.titulo}
          </button>
        ))}
      </div>

      {error && <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Paso 1: Cliente y vehículo */}
        {paso === 1 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            <h2 className="text-lg font-semibold text-slate-800">{PASOS[0].titulo}</h2>
            <div className="relative">
              <label className="block text-sm font-medium text-slate-700 mb-1">Cliente *</label>
              <div className="flex gap-1">
                <input
                  type="text"
                  value={form.cliente_id ? clientes.find((c) => c.id_cliente === aEntero(form.cliente_id))?.nombre ?? '' : clienteBuscar}
                  onChange={(e) => {
                    const v = e.target.value
                    setClienteBuscar(v)
                    setMostrarDropdownCliente(true)
                    if (!v) setForm({ ...form, cliente_id: '', vehiculo_id: '' })
                  }}
                  onFocus={() => setMostrarDropdownCliente(true)}
                  onBlur={() => setTimeout(() => setMostrarDropdownCliente(false), 150)}
                  placeholder="Escribe para buscar (nombre o teléfono)..."
                  className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  autoComplete="off"
                />
                {form.cliente_id && (
                  <button type="button" onClick={() => setForm({ ...form, cliente_id: '', vehiculo_id: '' })} className="px-3 py-2 border border-slate-300 rounded-lg text-slate-500 hover:bg-slate-50" title="Limpiar">
                    ✕
                  </button>
                )}
              </div>
              {mostrarDropdownCliente && !form.cliente_id && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {(clientes || [])
                    .filter(
                      (c) =>
                        !clienteBuscar.trim() ||
                        (c.nombre || '').toLowerCase().includes(clienteBuscar.toLowerCase()) ||
                        (c.telefono || '').includes(clienteBuscar)
                    )
                    .slice(0, 20)
                    .map((c) => (
                      <button
                        key={c.id_cliente}
                        type="button"
                        onClick={() => {
                          setForm({ ...form, cliente_id: String(c.id_cliente), vehiculo_id: '' })
                          setClienteBuscar('')
                          setMostrarDropdownCliente(false)
                        }}
                        className="w-full px-4 py-2 text-left hover:bg-slate-50 text-sm text-slate-700"
                      >
                        {c.nombre} {c.telefono ? `(${c.telefono})` : ''}
                      </button>
                    ))}
                  {(!clientes || clientes.length === 0) && (
                    <div className="px-4 py-3 text-sm text-slate-500">No hay clientes. Crea uno en la sección Clientes.</div>
                  )}
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Vehículo *</label>
              {form.cliente_id && (vehiculos || []).length === 0 ? (
                <div className="p-4 border border-amber-200 bg-amber-50 rounded-lg">
                  <p className="text-sm text-amber-800 mb-2">Este cliente no tiene vehículos registrados. Agrega uno en la sección Clientes o regístralo aquí.</p>
                  <button type="button" onClick={abrirAgregarVehiculo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm font-medium">
                    + Agregar vehículo
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <select
                    value={form.vehiculo_id || ''}
                    onChange={(e) => setForm({ ...form, vehiculo_id: e.target.value })}
                    required
                    className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    disabled={!form.cliente_id}
                  >
                    <option value="">Seleccionar...</option>
                    {(vehiculos || []).map((v) => (
                      <option key={v.id_vehiculo} value={v.id_vehiculo}>
                        {v.marca} {v.modelo} {v.anio}
                      </option>
                    ))}
                  </select>
                  {form.cliente_id && (vehiculos || []).length > 0 && (
                    <button type="button" onClick={abrirAgregarVehiculo} className="px-3 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 text-sm" title="Agregar otro vehículo">
                      +
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Paso 2: Técnico, prioridad, fecha */}
        {paso === 2 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            <h2 className="text-lg font-semibold text-slate-800">{PASOS[1].titulo}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Técnico (opcional)</label>
                <select value={form.tecnico_id || ''} onChange={(e) => setForm({ ...form, tecnico_id: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="">Sin asignar</option>
                  {(tecnicos || []).map((t) => (
                    <option key={t.id_usuario ?? t.id} value={t.id_usuario ?? t.id}>
                      {t.nombre || t.email} (Técnico)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Prioridad</label>
                <select value={form.prioridad} onChange={(e) => setForm({ ...form, prioridad: e.target.value })} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500">
                  <option value="BAJA">Baja</option>
                  <option value="NORMAL">Normal</option>
                  <option value="ALTA">Alta</option>
                  <option value="URGENTE">Urgente</option>
                </select>
              </div>
            </div>
            <p className="text-sm text-slate-600 italic">Precios sujetos a cambios sin previo aviso.</p>
          </div>
        )}

        {/* Paso 3: Diagnóstico y observaciones */}
        {paso === 3 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            <h2 className="text-lg font-semibold text-slate-800">{PASOS[2].titulo}</h2>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1" title="Describe el problema que reporta el cliente o la revisión preliminar del técnico">
                Diagnóstico inicial *
              </label>
              <textarea
                value={form.diagnostico_inicial}
                onChange={(e) => setForm({ ...form, diagnostico_inicial: e.target.value })}
                rows={4}
                placeholder="Ej: Cliente reporta ruido en frenos al frenar. Revisión preliminar: desgaste en pastillas delanteras."
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 placeholder-slate-400"
              />
              <p className="text-xs text-slate-500 mt-1">Qué reporta el cliente o lo que detectó el técnico en la revisión inicial.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1" title="Comentarios o instrucciones adicionales del cliente">
                Observaciones del cliente *
              </label>
              <textarea
                value={form.observaciones_cliente}
                onChange={(e) => setForm({ ...form, observaciones_cliente: e.target.value })}
                rows={4}
                placeholder="Ej: Cliente solicita llamar antes de iniciar. Prioridad: necesita el vehículo hoy."
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 placeholder-slate-400"
              />
              <p className="text-xs text-slate-500 mt-1">Preferencias, restricciones o instrucciones adicionales del cliente.</p>
            </div>
          </div>
        )}

        {/* Paso 4: Productos y servicios */}
        {paso === 4 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
            <h2 className="text-lg font-semibold text-slate-800">{PASOS[3].titulo}</h2>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Agregar producto o servicio</label>
              <div className="flex gap-2 flex-wrap items-end">
                <div>
                  <label className="block text-xs text-slate-500 mb-0.5">Tipo</label>
                  <select value={detalleActual.tipo} onChange={(e) => setDetalleActual({ ...detalleActual, tipo: e.target.value, id_item: '' })} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
                    <option value="SERVICIO">Servicio</option>
                    <option value="PRODUCTO">Producto</option>
                  </select>
                </div>
                {detalleActual.tipo === 'PRODUCTO' && (
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Origen</label>
                    <select value={detalleActual.repuesto_tipo} onChange={(e) => setDetalleActual({ ...detalleActual, repuesto_tipo: e.target.value, id_item: '', descripcion_libre: '' })} className="px-3 py-2 border border-slate-300 rounded-lg text-sm">
                      <option value="catalogo">Del catálogo</option>
                      <option value="libre">Descripción libre (no en inventario)</option>
                    </select>
                  </div>
                )}
                {detalleActual.tipo === 'SERVICIO' ? (
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Servicio *</label>
                    <select
                      value={detalleActual.id_item}
                      onChange={(e) => {
                        const id = e.target.value
                        const idNum = aEntero(id)
                        const item = servicios.find((s) => (s.id ?? s.id_servicio) === idNum)
                        setDetalleActual({ ...detalleActual, id_item: id, precio_unitario: item ? Number(item.precio_base) : 0 })
                      }}
                      className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]"
                    >
                      <option value="">Seleccionar...</option>
                      {servicios.map((x) => (
                        <option key={x.id ?? x.id_servicio} value={x.id ?? x.id_servicio}>{x.codigo || ''} {x.nombre}</option>
                      ))}
                    </select>
                  </div>
                ) : detalleActual.repuesto_tipo === 'libre' ? (
                  <div className="flex gap-2 flex-wrap items-end">
                    <div>
                      <label className="block text-xs text-slate-500 mb-0.5">Descripción *</label>
                      <input type="text" value={detalleActual.descripcion_libre} onChange={(e) => setDetalleActual({ ...detalleActual, descripcion_libre: e.target.value })} placeholder="Ej: Bomba de agua genérica" className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]" />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-500 mb-0.5">P. compra est.</label>
                      <input type="number" min={0} step={0.01} value={detalleActual.precio_compra_estimado || ''} onChange={(e) => setDetalleActual({ ...detalleActual, precio_compra_estimado: aNumero(e.target.value) })} placeholder="0" className="w-20 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs text-slate-500 mb-0.5">Producto *</label>
                    <select
                      value={detalleActual.id_item}
                      onChange={(e) => {
                        const id = e.target.value
                        const idNum = aEntero(id)
                        const item = repuestos.find((r) => (r.id_repuesto ?? r.id) === idNum)
                        setDetalleActual({ ...detalleActual, id_item: id, precio_unitario: item ? Number(item.precio_venta) : 0, precio_compra_estimado: item?.precio_compra != null ? Number(item.precio_compra) : 0 })
                      }}
                      className="px-3 py-2 border border-slate-300 rounded-lg text-sm min-w-[180px]"
                    >
                      <option value="">Seleccionar...</option>
                      {repuestos.map((x) => (
                        <option key={x.id_repuesto ?? x.id} value={x.id_repuesto ?? x.id}>{x.codigo || ''} {x.nombre}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="block text-xs text-slate-500 mb-0.5">Cantidad</label>
                  <input type="number" min={1} value={detalleActual.cantidad} onChange={(e) => setDetalleActual({ ...detalleActual, cantidad: aEntero(e.target.value, 1) })} className="w-20 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-0.5">Precio</label>
                  <div className="flex gap-1 items-center">
                    <input type="number" min={0} step={0.01} value={detalleActual.precio_unitario || ''} onChange={(e) => setDetalleActual({ ...detalleActual, precio_unitario: aNumero(e.target.value) })} placeholder="Auto" className="w-24 px-2 py-2 border border-slate-300 rounded-lg text-sm" />
                    {(detalleActual.tipo === 'PRODUCTO' || detalleActual.repuesto_tipo === 'libre') && (detalleActual.precio_compra_estimado > 0) && (
                      <button type="button" onClick={aplicarMarkupEnDetalle} title={`Aplicar ${config.markup_porcentaje ?? 20}% markup sobre P. compra est.`} className="px-2 py-1.5 bg-amber-100 text-amber-800 rounded text-xs font-medium hover:bg-amber-200">
                        +{config.markup_porcentaje ?? 20}%
                      </button>
                    )}
                  </div>
                </div>
                <button type="button" onClick={agregarDetalle} disabled={!puedeAgregar} className="px-4 py-2 bg-slate-200 rounded-lg text-sm hover:bg-slate-300 disabled:opacity-50 disabled:cursor-not-allowed">
                  + Agregar
                </button>
              </div>
              {servicioSeleccionadoRequiereRepuestos && (
                <p className="text-xs text-amber-700 mt-2 bg-amber-50 px-3 py-2 rounded">
                  ⚠️ Este servicio suele requerir repuestos. Considera agregar los repuestos necesarios o marcar "Cliente proporcionó refacciones" si aplica.
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Productos y servicios agregados *</label>
              {requiereAdvertenciaRepuestos && (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg mb-2">
                  ⚠️ Hay servicios que suelen requerir repuestos. Agrega los repuestos necesarios o marca "Cliente proporcionó refacciones" si el cliente los trae.
                </p>
              )}
              <div className={`border rounded-lg divide-y max-h-48 overflow-y-auto ${!tieneProductosOServicios ? 'border-amber-300 bg-amber-50' : 'border-slate-200'}`}>
                {form.servicios.length === 0 && form.repuestos.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-amber-700 text-center">Agrega al menos un producto o servicio antes de crear la orden.</p>
                ) : (
                  <>
                    {form.servicios.map((s, i) => {
                      const serv = servicios.find((x) => (x.id ?? x.id_servicio) === s.servicio_id)
                      return (
                        <div key={`s-${i}`} className="px-4 py-3 flex justify-between items-center text-sm">
                          <span>
                            🔧 {serv?.nombre ?? `Servicio #${s.servicio_id}`} x{s.cantidad} @ ${(Number(s.precio_unitario) || 0).toFixed(2)}
                          </span>
                          <button type="button" onClick={() => quitarServicio(i)} className="text-red-600 hover:text-red-700 text-xs font-medium">
                            Quitar
                          </button>
                        </div>
                      )
                    })}
                    {form.repuestos.map((r, i) => {
                      const rep = r.repuesto_id ? repuestos.find((x) => (x.id_repuesto ?? x.id) === r.repuesto_id) : null
                      const nombre = r.descripcion_libre?.trim() || rep?.nombre || `Repuesto #${r.repuesto_id || 'N/A'}`
                      return (
                        <div key={`r-${i}`} className="px-4 py-3 flex justify-between items-center text-sm">
                          <span>
                            📦 {nombre} x{r.cantidad} @ ${(Number(r.precio_unitario) || 0).toFixed(2)}
                          </span>
                          <button type="button" onClick={() => quitarRepuesto(i)} className="text-red-600 hover:text-red-700 text-xs font-medium">
                            Quitar
                          </button>
                        </div>
                      )
                    })}
                  </>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-3 pt-2 border-t border-slate-200">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.requiere_autorizacion} onChange={(e) => setForm({ ...form, requiere_autorizacion: e.target.checked })} />
                <span className="text-sm text-slate-700">Requiere autorización del cliente</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer" title="Marcar si el cliente trajo refacciones (total o parcial). Al finalizar no se descontará nada del inventario.">
                <input type="checkbox" checked={!!form.cliente_proporciono_refacciones} onChange={(e) => setForm({ ...form, cliente_proporciono_refacciones: e.target.checked })} />
                <span className="text-sm text-slate-700">Cliente proporcionó refacciones (total o parcial)</span>
              </label>
            </div>
          </div>
        )}

        {/* Navegación */}
        <div className="flex justify-between items-center pt-4 border-t border-slate-200">
          <div>
            {paso > 1 && (
              <button type="button" onClick={() => setPaso((p) => p - 1)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium">
                ← Anterior
              </button>
            )}
          </div>
          <div className="flex gap-2">
            {paso < 4 ? (
              <button type="button" onClick={handleSiguiente} disabled={!puedeAvanzar()} className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium">
                Siguiente →
              </button>
            ) : (
              <button type="submit" disabled={enviando || !puedeGuardar} className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium">
                {enviando ? 'Guardando...' : 'Crear orden'}
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Modal agregar vehículo */}
      <Modal titulo={`Agregar vehículo — ${clientes.find((c) => c.id_cliente === aEntero(form.cliente_id))?.nombre || 'Cliente'}`} abierto={modalVehiculo} onCerrar={() => setModalVehiculo(false)}>
        <form onSubmit={handleVehiculoSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label>
              <input type="text" value={formVehiculo.marca} onChange={(e) => setFormVehiculo({ ...formVehiculo, marca: e.target.value })} required placeholder="Ej: Nissan" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label>
              <input type="text" value={formVehiculo.modelo} onChange={(e) => setFormVehiculo({ ...formVehiculo, modelo: e.target.value })} required placeholder="Ej: Versa" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Año *</label>
              <input type="number" min={1900} max={2030} value={formVehiculo.anio} onChange={(e) => setFormVehiculo({ ...formVehiculo, anio: e.target.value })} required className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Color (opcional)</label>
              <input type="text" value={formVehiculo.color} onChange={(e) => setFormVehiculo({ ...formVehiculo, color: e.target.value })} placeholder="Ej: Blanco" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Motor (opcional)</label>
              <input type="text" value={formVehiculo.motor} onChange={(e) => setFormVehiculo({ ...formVehiculo, motor: e.target.value })} placeholder="Ej: 1.8" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">VIN / Núm. serie (opcional)</label>
              <input type="text" value={formVehiculo.numero_serie} onChange={(e) => setFormVehiculo({ ...formVehiculo, numero_serie: e.target.value })} placeholder="Ej: 1HGBH41JXMN109186" className="w-full px-4 py-2 border border-slate-300 rounded-lg" />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalVehiculo(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
              Cancelar
            </button>
            <button type="submit" disabled={enviandoVehiculo} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
              {enviandoVehiculo ? 'Guardando...' : 'Agregar'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal servicio que requiere repuestos */}
      <Modal titulo="Servicio con repuestos requeridos" abierto={modalServicioRepuestos.abierto} onCerrar={() => setModalServicioRepuestos({ abierto: false, servicio: null })}>
        {modalServicioRepuestos.servicio && (
          <div className="space-y-4">
            <p className="text-slate-600">
              El servicio <strong>&quot;{modalServicioRepuestos.servicio.s?.nombre}&quot;</strong> requiere repuestos para su ejecución.
            </p>
            <p className="text-sm text-slate-500">
              Puede agregar los repuestos más adelante o marcar la opción &quot;Cliente proporcionó refacciones&quot; si el cliente trae sus propias piezas.
            </p>
            <p className="text-sm font-medium text-slate-700">¿Desea agregar el servicio a la orden?</p>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setModalServicioRepuestos({ abierto: false, servicio: null })} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
                Cancelar
              </button>
              <button type="button" onClick={() => agregarServicioConfirmado(modalServicioRepuestos.servicio.idItem, modalServicioRepuestos.servicio.cantidad, modalServicioRepuestos.servicio.precio, modalServicioRepuestos.servicio.s)} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                Agregar servicio
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal confirmar crear orden sin repuestos */}
      <Modal titulo="Confirmar orden" abierto={modalConfirmarCrear} onCerrar={() => setModalConfirmarCrear(false)}>
        <div className="space-y-4">
          <p className="text-slate-600">
            Hay servicios en la orden que requieren repuestos. No se han agregado repuestos ni se ha marcado &quot;Cliente proporcionó refacciones&quot;.
          </p>
          <p className="text-sm font-medium text-slate-700">¿Desea continuar y crear la orden de todos modos?</p>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalConfirmarCrear(false)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50">
              Volver
            </button>
            <button type="button" onClick={ejecutarCrearOrden} disabled={enviando} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
              {enviando ? 'Creando...' : 'Crear orden'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
