import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useInvalidateQueries } from '../hooks/useApi'
import SearchableRepuestoSelect from '../components/SearchableRepuestoSelect'
import SearchableVehiculoSelect from '../components/SearchableVehiculoSelect'
import Modal from '../components/Modal'
import { aNumero, aEntero } from '../utils/numeros'
import { normalizeDetail } from '../utils/toast'

export default function NuevaOrdenCompra() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const invalidate = useInvalidateQueries()

  const [proveedores, setProveedores] = useState([])
  const [repuestos, setRepuestos] = useState([])
  const [catalogoVehiculos, setCatalogoVehiculos] = useState([])
  const [modalVehiculo, setModalVehiculo] = useState(false)
  const [formVehiculo, setFormVehiculo] = useState({ anio: new Date().getFullYear(), marca: '', modelo: '', version_trim: '', motor: '', vin: '' })
  const [enviandoVehiculo, setEnviandoVehiculo] = useState(false)
  const [form, setForm] = useState({
    id_proveedor: '',
    id_catalogo_vehiculo: '',
    observaciones: '',
    items: [{ tipo: 'nuevo', id_repuesto: '', nombre_nuevo: '', cantidad_solicitada: 1, precio_unitario_estimado: 0 }],
  })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const puedeGestionar = user?.rol === 'ADMIN' || user?.rol === 'CAJA'

  useEffect(() => {
    Promise.allSettled([
      api.get('/proveedores/', { params: { limit: 500 } }),
      api.get('/repuestos/', { params: { limit: 500, activo: true } }),
      api.get('/catalogo-vehiculos/', { params: { limit: 300 } }),
    ]).then(([rProv, rRep, rCat]) => {
      const prov = rProv.status === 'fulfilled' ? (rProv.value.data?.proveedores ?? rProv.value.data ?? []) : []
      const rep = rRep.status === 'fulfilled' ? (rRep.value.data?.repuestos ?? rRep.value.data ?? []) : []
      const cat = rCat.status === 'fulfilled' ? (rCat.value.data?.vehiculos ?? rCat.value.data ?? []) : []
      setProveedores(Array.isArray(prov) ? prov : [])
      setRepuestos(Array.isArray(rep) ? rep : [])
      setCatalogoVehiculos(Array.isArray(cat) ? cat : [])
    })
  }, [])

  const abrirAgregarVehiculo = () => {
    setFormVehiculo({ anio: new Date().getFullYear(), marca: '', modelo: '', version_trim: '', motor: '', vin: '' })
    setModalVehiculo(true)
  }

  const handleVehiculoSubmit = async (e) => {
    e.preventDefault()
    setEnviandoVehiculo(true)
    setError('')
    try {
      const res = await api.post('/catalogo-vehiculos/', {
        anio: aEntero(formVehiculo.anio),
        marca: formVehiculo.marca.trim(),
        modelo: formVehiculo.modelo.trim(),
        version_trim: formVehiculo.version_trim?.trim() || null,
        motor: formVehiculo.motor?.trim() || null,
        vin: formVehiculo.vin?.trim() || null,
      })
      const nuevo = res.data
      setCatalogoVehiculos((prev) => [{ ...nuevo, id: nuevo.id }, ...prev])
      setForm((prev) => ({ ...prev, id_catalogo_vehiculo: String(nuevo.id) }))
      setModalVehiculo(false)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al agregar vehículo')
    } finally {
      setEnviandoVehiculo(false)
    }
  }

  const agregarItem = () => {
    setForm((f) => ({ ...f, items: [...f.items, { tipo: 'nuevo', id_repuesto: '', nombre_nuevo: '', cantidad_solicitada: 1, precio_unitario_estimado: 0 }] }))
  }

  const quitarItem = (idx) => {
    setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== idx) }))
  }

  const actualizarItem = (idx, campo, valor) => {
    setForm((f) => {
      const nuevo = { ...f, items: f.items.map((it, i) => (i === idx ? { ...it, [campo]: valor } : it)) }
      if (campo === 'id_repuesto' && valor) {
        const rep = repuestos.find((r) => r && String(r.id_repuesto) === String(valor))
        if (rep) {
          if (!f.id_proveedor && rep.id_proveedor) {
            nuevo.id_proveedor = String(rep.id_proveedor)
          }
          const it = nuevo.items[idx]
          const precioActual = it?.precio_unitario_estimado ?? 0
          if (precioActual <= 0 && rep.precio_compra != null) {
            nuevo.items = nuevo.items.map((item, i) =>
              i === idx ? { ...item, precio_unitario_estimado: aNumero(rep.precio_compra) } : item
            )
          }
        }
      }
      return nuevo
    })
  }

  const crearOrden = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.id_proveedor) {
      setError('Selecciona un proveedor')
      return
    }
    const items = form.items.filter((it) => {
      const tieneRepuesto = it.tipo === 'existente' ? it.id_repuesto : it.nombre_nuevo?.trim()
      return tieneRepuesto && it.cantidad_solicitada > 0
    })
    if (items.length === 0) {
      setError('Agrega al menos un repuesto')
      return
    }

    setEnviando(true)
    try {
      const res = await api.post('/ordenes-compra/', {
        id_proveedor: aEntero(form.id_proveedor),
        id_catalogo_vehiculo: form.id_catalogo_vehiculo ? aEntero(form.id_catalogo_vehiculo) : null,
        observaciones: form.observaciones?.trim() || null,
        items: items.map((it) => {
          const base = {
            cantidad_solicitada: aEntero(it.cantidad_solicitada, 1),
            precio_unitario_estimado: aNumero(it.precio_unitario_estimado),
          }
          if (it.tipo === 'existente') {
            return { ...base, id_repuesto: aEntero(it.id_repuesto) }
          }
          return { ...base, nombre_nuevo: it.nombre_nuevo?.trim() || '' }
        }),
      })
      const ordenCreada = res.data
      invalidate(['ordenes-compra'])
      navigate(`/ordenes-compra?ver=${ordenCreada.id_orden_compra}`)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al crear orden')
    } finally {
      setEnviando(false)
    }
  }

  if (!puedeGestionar) {
    return (
      <div>
        <p className="text-slate-500">No tienes permiso para crear órdenes de compra.</p>
        <Link to="/ordenes-compra" className="text-primary-600 hover:underline">Volver a órdenes</Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto min-h-0 flex flex-col">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-6">
        <Link to="/ordenes-compra" className="min-h-[44px] inline-flex items-center text-slate-600 hover:text-slate-800 active:text-slate-900 touch-manipulation">← Ordenes de compra</Link>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Nueva orden de compra</h1>
      </div>

      <form onSubmit={crearOrden} className="bg-white rounded-lg shadow p-4 sm:p-6 space-y-6 border border-slate-200">
        {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{error}</div>}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Proveedor *</label>
          <select value={form.id_proveedor} onChange={(e) => setForm({ ...form, id_proveedor: e.target.value })} className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" required>
            <option value="">Seleccionar...</option>
            {proveedores.filter((p) => p.activo !== false).map((p) => (
              <option key={p.id_proveedor} value={p.id_proveedor}>{p.nombre}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Para qué vehículo (opcional)</label>
          <div className="flex gap-2 items-center flex-wrap">
            <SearchableVehiculoSelect vehiculos={catalogoVehiculos} value={form.id_catalogo_vehiculo} onChange={(v) => setForm({ ...form, id_catalogo_vehiculo: v })} placeholder="Buscar por año, marca, modelo..." className="min-h-[44px] sm:h-10 flex-1 min-w-0" />
            <button type="button" onClick={abrirAgregarVehiculo} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 text-sm font-medium touch-manipulation">+ Agregar vehículo</button>
          </div>
          <p className="text-xs text-slate-500 mt-1">Año, marca, modelo, versión, motor (catálogo independiente)</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Observaciones</label>
          <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={3} className="w-full px-4 py-2 min-h-[80px] text-base sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 touch-manipulation" placeholder="Notas adicionales sobre la orden" />
        </div>

        <div>
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2 mb-2">
            <label className="text-sm font-medium text-slate-700">Repuestos *</label>
            <button type="button" onClick={agregarItem} className="min-h-[44px] px-3 py-2 text-sm text-primary-600 hover:text-primary-700 active:bg-primary-50 rounded font-medium touch-manipulation">+ Agregar repuesto</button>
          </div>
          <div className="space-y-3 border border-slate-200 rounded-lg p-4 bg-slate-50/50">
            {form.items.map((it, idx) => (
              <div key={idx} className="flex gap-3 items-center flex-wrap p-3 bg-white rounded-lg border border-slate-100">
                <select value={it.tipo} onChange={(e) => actualizarItem(idx, 'tipo', e.target.value)} className="min-h-[44px] sm:h-10 px-3 border border-slate-300 rounded-lg text-base sm:text-sm shrink-0 touch-manipulation">
                  <option value="existente">Del catálogo</option>
                  <option value="nuevo">Repuesto nuevo</option>
                </select>
                {it.tipo === 'existente' ? (
                  <SearchableRepuestoSelect repuestos={repuestos} value={it.id_repuesto} onChange={(v) => actualizarItem(idx, 'id_repuesto', v)} placeholder="Buscar repuesto..." className="flex-1 min-w-[140px] min-h-[44px] sm:h-10" />
                ) : (
                  <input type="text" placeholder="Nombre del repuesto" value={it.nombre_nuevo} onChange={(e) => actualizarItem(idx, 'nombre_nuevo', e.target.value)} className="flex-1 min-w-[140px] min-h-[44px] sm:h-10 px-3 border border-slate-300 rounded-lg text-base sm:text-sm touch-manipulation" aria-label="Nombre" />
                )}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 whitespace-nowrap">Cant.</span>
                  <input type="number" min={1} value={it.cantidad_solicitada} onChange={(e) => actualizarItem(idx, 'cantidad_solicitada', aEntero(e.target.value, 1))} className="w-16 min-h-[44px] sm:h-10 px-2 border border-slate-300 rounded-lg text-base sm:text-sm text-center touch-manipulation" aria-label="Cantidad" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 whitespace-nowrap">Precio est.</span>
                  <input type="number" step={0.01} min={0} value={it.precio_unitario_estimado} onChange={(e) => actualizarItem(idx, 'precio_unitario_estimado', aNumero(e.target.value))} className="w-24 min-h-[44px] sm:h-10 px-2 border border-slate-300 rounded-lg text-base sm:text-sm touch-manipulation" aria-label="Precio estimado" placeholder="0" />
                </div>
                <button type="button" onClick={() => quitarItem(idx)} className="min-h-[44px] min-w-[44px] flex items-center justify-center text-red-500 hover:bg-red-50 active:bg-red-100 rounded touch-manipulation" title="Quitar repuesto" aria-label="Quitar repuesto">✕</button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-3 pt-4 border-t border-slate-200">
          <Link to="/ordenes-compra" className="min-h-[44px] px-5 py-2.5 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 font-medium inline-flex items-center touch-manipulation">Cancelar</Link>
          <button type="submit" disabled={enviando} className="min-h-[44px] px-5 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 font-medium touch-manipulation">{enviando ? 'Creando...' : 'Crear orden'}</button>
        </div>
      </form>

      <Modal titulo="Agregar vehículo al catálogo" abierto={modalVehiculo} onCerrar={() => setModalVehiculo(false)}>
        <form onSubmit={handleVehiculoSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Año *</label>
              <input type="number" min={1900} max={2030} value={formVehiculo.anio} onChange={(e) => setFormVehiculo({ ...formVehiculo, anio: e.target.value })} required placeholder="Ej: 2016" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Marca *</label>
              <input type="text" value={formVehiculo.marca} onChange={(e) => setFormVehiculo({ ...formVehiculo, marca: e.target.value })} required placeholder="Ej: Ford" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Modelo *</label>
              <input type="text" value={formVehiculo.modelo} onChange={(e) => setFormVehiculo({ ...formVehiculo, modelo: e.target.value })} required placeholder="Ej: Edge" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Versión (opcional)</label>
              <input type="text" value={formVehiculo.version_trim} onChange={(e) => setFormVehiculo({ ...formVehiculo, version_trim: e.target.value })} placeholder="Ej: SEL" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Motor (opcional)</label>
              <input type="text" value={formVehiculo.motor} onChange={(e) => setFormVehiculo({ ...formVehiculo, motor: e.target.value })} placeholder="Ej: 2.0" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">VIN (opcional)</label>
              <input type="text" value={formVehiculo.vin} onChange={(e) => setFormVehiculo({ ...formVehiculo, vin: e.target.value })} placeholder="Ej: 2FMPK4J95HBB19231" className="w-full px-4 py-2 min-h-[48px] text-base sm:text-sm border border-slate-300 rounded-lg touch-manipulation" />
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-2 pt-2">
            <button type="button" onClick={() => setModalVehiculo(false)} className="min-h-[44px] px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 touch-manipulation">Cancelar</button>
            <button type="submit" disabled={enviandoVehiculo} className="min-h-[44px] px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 touch-manipulation">{enviandoVehiculo ? 'Guardando...' : 'Agregar'}</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
