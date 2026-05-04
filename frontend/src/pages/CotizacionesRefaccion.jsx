import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import PageHeader, { IconPlus, btnNuevo } from '../components/PageHeader'
import PageLoading from '../components/PageLoading'
import { normalizeDetail, showError } from '../utils/toast'
import { useApiQuery, useInvalidateQueries } from '../hooks/useApi'

const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'BORRADOR', label: 'Borrador' },
  { value: 'ENVIADA', label: 'Enviada' },
  { value: 'ACEPTADA_CLIENTE', label: 'Aceptada' },
  { value: 'EN_COMPRA', label: 'En compra' },
  { value: 'RECIBIDA', label: 'Recibida' },
  { value: 'ENTREGADA', label: 'Entregada' },
  { value: 'CANCELADA', label: 'Cancelada' },
]

export default function CotizacionesRefaccion() {
  const navigate = useNavigate()
  const invalidate = useInvalidateQueries()
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [pagina, setPagina] = useState(1)
  const limite = 25

  const [modalNuevo, setModalNuevo] = useState(false)
  const [clientes, setClientes] = useState([])
  const [formNuevo, setFormNuevo] = useState({
    id_cliente: '',
    tc_referencia_usd_mxn: '',
    margen_objetivo_pct: '',
    notas_generales: '',
  })
  const [enviando, setEnviando] = useState(false)
  const [errorModal, setErrorModal] = useState('')

  const { data, isLoading } = useApiQuery(
    ['cotizaciones-refaccion', pagina, buscar.trim(), estado],
    () =>
      api
        .get('/cotizaciones-refaccion/', {
          params: {
            pagina,
            limite,
            buscar: buscar.trim() || undefined,
            estado: estado || undefined,
          },
        })
        .then((r) => r.data),
    { staleTime: 30 * 1000 }
  )

  const abrirNuevo = async () => {
    setErrorModal('')
    setFormNuevo({
      id_cliente: '',
      tc_referencia_usd_mxn: '',
      margen_objetivo_pct: '',
      notas_generales: '',
    })
    try {
      const r = await api.get('/clientes/', { params: { limit: 500, skip: 0 } })
      const arr = r.data?.clientes ?? r.data ?? []
      setClientes(Array.isArray(arr) ? arr : [])
    } catch (e) {
      showError(normalizeDetail(e.response?.data?.detail) || 'No se pudieron cargar clientes')
      setClientes([])
    }
    setModalNuevo(true)
  }

  const crear = async (e) => {
    e.preventDefault()
    setErrorModal('')
    const id = parseInt(formNuevo.id_cliente, 10)
    if (!id) {
      setErrorModal('Seleccione un cliente')
      return
    }
    setEnviando(true)
    try {
      const payload = {
        id_cliente: id,
        tc_referencia_usd_mxn: formNuevo.tc_referencia_usd_mxn
          ? parseFloat(formNuevo.tc_referencia_usd_mxn)
          : null,
        margen_objetivo_pct: formNuevo.margen_objetivo_pct
          ? parseFloat(formNuevo.margen_objetivo_pct)
          : null,
        notas_generales: formNuevo.notas_generales?.trim() || null,
      }
      const r = await api.post('/cotizaciones-refaccion/', payload)
      setModalNuevo(false)
      invalidate(['cotizaciones-refaccion'])
      navigate(`/cotizaciones-refaccion/${r.data.id}`)
    } catch (err) {
      setErrorModal(normalizeDetail(err.response?.data?.detail) || 'Error al crear')
    } finally {
      setEnviando(false)
    }
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPaginas = data?.total_paginas ?? 1

  if (isLoading && !data) return <PageLoading mensaje="Cargando cotizaciones..." />

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <PageHeader
        title="Cotizaciones refacción (especial)"
        subtitle="Importación y piezas fuera de stock local"
      >
        <button type="button" className={btnNuevo} onClick={abrirNuevo}>
          <IconPlus /> Nueva cotización
        </button>
      </PageHeader>

      <div className="flex flex-wrap gap-3 mb-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-slate-500 mb-1">Buscar</label>
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Folio o cliente..."
            value={buscar}
            onChange={(e) => {
              setPagina(1)
              setBuscar(e.target.value)
            }}
          />
        </div>
        <div className="w-44">
          <label className="block text-xs text-slate-500 mb-1">Estado</label>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={estado}
            onChange={(e) => {
              setPagina(1)
              setEstado(e.target.value)
            }}
          >
            {ESTADOS.map((o) => (
              <option key={o.value || 'all'} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left p-3">Folio</th>
              <th className="text-left p-3">Cliente</th>
              <th className="text-left p-3">Estado</th>
              <th className="text-left p-3">Creado</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-8 text-center text-slate-500">
                  Sin cotizaciones
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr key={row.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="p-3">
                    <Link className="text-orange-600 font-medium hover:underline" to={`/cotizaciones-refaccion/${row.id}`}>
                      {row.numero}
                    </Link>
                  </td>
                  <td className="p-3">{row.cliente_nombre || `Cliente #${row.id_cliente}`}</td>
                  <td className="p-3">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100">{row.estado}</span>
                  </td>
                  <td className="p-3 text-slate-600">
                    {row.creado_en ? new Date(row.creado_en).toLocaleString() : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPaginas > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            type="button"
            disabled={pagina <= 1}
            className="px-3 py-1 rounded border text-sm disabled:opacity-40"
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
          >
            Anterior
          </button>
          <span className="text-sm py-1 text-slate-600">
            Página {pagina} de {totalPaginas} ({total})
          </span>
          <button
            type="button"
            disabled={pagina >= totalPaginas}
            className="px-3 py-1 rounded border text-sm disabled:opacity-40"
            onClick={() => setPagina((p) => p + 1)}
          >
            Siguiente
          </button>
        </div>
      )}

      {modalNuevo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Nueva cotización</h3>
            <form onSubmit={crear} className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Cliente *</label>
                <select
                  required
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={formNuevo.id_cliente}
                  onChange={(e) => setFormNuevo((f) => ({ ...f, id_cliente: e.target.value }))}
                >
                  <option value="">— Seleccione —</option>
                  {clientes.map((c) => (
                    <option key={c.id_cliente} value={c.id_cliente}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">TC USD→MXN (referencia)</label>
                <input
                  type="number"
                  step="0.0001"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={formNuevo.tc_referencia_usd_mxn}
                  onChange={(e) => setFormNuevo((f) => ({ ...f, tc_referencia_usd_mxn: e.target.value }))}
                  placeholder="Ej. 18.50"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Margen % (opcional, default config)</label>
                <input
                  type="number"
                  step="0.1"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  value={formNuevo.margen_objetivo_pct}
                  onChange={(e) => setFormNuevo((f) => ({ ...f, margen_objetivo_pct: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Notas</label>
                <textarea
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  rows={2}
                  value={formNuevo.notas_generales}
                  onChange={(e) => setFormNuevo((f) => ({ ...f, notas_generales: e.target.value }))}
                />
              </div>
              {errorModal && <p className="text-sm text-red-600">{errorModal}</p>}
              <div className="flex gap-2 justify-end pt-2">
                <button type="button" className="px-4 py-2 rounded-lg border text-sm" onClick={() => setModalNuevo(false)}>
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={enviando}
                  className="px-4 py-2 rounded-lg bg-orange-500 text-white text-sm disabled:opacity-50"
                >
                  {enviando ? 'Creando...' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
