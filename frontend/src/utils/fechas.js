/**
 * Utilidades de fechas — zona operativa del taller (America/Matamoros).
 * Ver docs/TIMEZONE_POLICY.md.
 *
 * - Eventos de sistema (caja, pagos, ventas): API envía ISO con Z (UTC) → mostrar en Matamoros.
 * - fecha_ingreso OT (TZ-1): API envía ISO sin Z (wall-clock taller) → formatearFechaIngresoOtLocal.
 * - Citas fecha_hora: local naive Matamoros → formatearFechaHoraLocalNaive / formatearHoraLocalNaive.
 * Evita mezclar timezone del navegador con timezone del negocio.
 */

/** Zona horaria oficial del negocio (Matamoros, Tamaulipas). */
export const TALLER_TIMEZONE = 'America/Matamoros'

/** Parsea "YYYY-MM-DD" en fecha local (evita que se interprete como UTC). Si str es vacío o inválido retorna Invalid Date. */
export function parseFechaLocal(str) {
  if (!str || typeof str !== 'string') return new Date(NaN)
  const parts = str.split('-').map(Number)
  if (parts.length !== 3 || parts.some(isNaN)) return new Date(NaN)
  const [y, m, d] = parts
  return new Date(y, m - 1, d)
}

/** Formatea Date a "YYYY-MM-DD" en hora local (evita desfase de toISOString/UTC). */
export function fechaAStr(d) {
  if (!d || !(d instanceof Date) || isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Retorna la fecha de hoy en formato "YYYY-MM-DD" (hora local). */
export function hoyStr() {
  return fechaAStr(new Date())
}

/**
 * Convierte ISO UTC naive del backend (sin Z) a valor YYYY-MM-DDTHH:mm para input datetime-local.
 * Usar para fecha_ingreso almacenada en UTC en el servidor.
 */
export function isoUtcNaiveToDatetimeLocalValue(iso) {
  if (iso == null || iso === '') return ''
  const s = String(iso).trim()
  if (!s) return ''
  const withTz = s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s) ? s : `${s.replace(/\.\d+$/, '')}Z`
  const d = new Date(withTz)
  if (isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day}T${h}:${min}`
}

/**
 * Valor datetime-local desde ISO local naive (fecha_promesa guardada sin offset).
 */
export function isoLocalNaiveToDatetimeLocalValue(iso) {
  if (iso == null || iso === '') return ''
  const s = String(iso).trim()
  if (!s) return ''
  const base = s.replace(/\.\d+$/, '').slice(0, 16)
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(base) ? base : ''
}

/**
 * Parsea ISO local naive del taller (sin Z): los dígitos son wall-clock (America/Matamoros).
 * Usado por fecha_ingreso OT (TZ-1) y citas fecha_hora.
 */
function _parseLocalNaiveTaller(iso) {
  if (iso == null || iso === '') return null
  const s = String(iso).trim()
  if (!s) return null
  const base = s.replace(/\.\d+$/, '').replace(' ', 'T')
  const m = base.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/)
  if (!m) return null
  const [, y, mo, d, h, mi, se] = m
  return new Date(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(se || 0))
}

/** @deprecated alias interno — usar _parseLocalNaiveTaller */
function _parseFechaIngresoOtLocal(iso) {
  return _parseLocalNaiveTaller(iso)
}

/**
 * Muestra fecha_ingreso OT como hora local del taller (naive, sin conversión UTC).
 * Convención TZ-1: el backend envía ISO sin Z; los dígitos son hora local del taller (America/Matamoros).
 */
export function formatearFechaIngresoOtLocal(iso, locale = 'es-MX') {
  return formatearFechaHoraLocalNaive(iso, locale)
}

/**
 * Muestra fecha_hora de cita (local naive Matamoros, sin Z) como wall-clock — sin conversión UTC.
 * Ej: "2026-06-30T08:30:00" → 08:30, no 03:30 ni 13:30.
 */
export function formatearFechaHoraLocalNaive(iso, locale = 'es-MX') {
  const d = _parseLocalNaiveTaller(iso)
  if (!d || isNaN(d.getTime())) return '-'
  const out = d.toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' })
  return out === 'Invalid Date' ? '-' : out
}

/**
 * Solo hora de un ISO local naive (citas fecha_hora).
 */
export function formatearHoraLocalNaive(iso, locale = 'es-MX') {
  const d = _parseLocalNaiveTaller(iso)
  if (!d || isNaN(d.getTime())) return '-'
  const out = d.toLocaleTimeString(locale, { timeStyle: 'short' })
  return out === 'Invalid Date' ? '-' : out
}

/**
 * Separa ISO local naive en { fecha: YYYY-MM-DD, hora: HH:mm } para formularios de cita.
 */
export function localNaiveAFechaHoraForm(iso) {
  const dt = isoLocalNaiveToDatetimeLocalValue(iso)
  if (!dt) return { fecha: '', hora: '' }
  const [fecha, hora] = dt.split('T')
  return { fecha: fecha || '', hora: hora || '' }
}

/**
 * @deprecated TZ-1: usar formatearFechaIngresoOtLocal. Conservado por compatibilidad temporal.
 * Muestra fecha_ingreso asumiendo UTC naive legacy (pre-TZ-1).
 */
export function formatearFechaIngresoOtUtc(iso, locale = 'es-MX') {
  if (iso == null || iso === '') return '-'
  const s = String(iso).trim()
  if (!s) return '-'
  const withTz = s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s) ? s : `${s.replace(/\.\d+$/, '')}Z`
  return formatearFechaHora(withTz, locale)
}

/**
 * Formatea string de fecha (YYYY-MM-DD o ISO) para mostrar solo día.
 * Usa T12:00:00 para fecha-solo y evita desfase en zonas negativas.
 */
export function formatearFechaSolo(str, locale = 'es-MX') {
  if (str == null || str === '') return '-'
  const s = String(str).trim()
  if (!s) return '-'
  const fechaSolo = s.slice(0, 10)
  if (/^\d{4}-\d{2}-\d{2}$/.test(fechaSolo) && s.length <= 10) {
    const d = _parseIsoEventoUtc(fechaSolo)
    return _formatearEnTaller(d, locale, { dateStyle: 'short', timeStyle: undefined })
  }
  const d = _parseIsoEventoUtc(s)
  if (!d) return '-'
  return _formatearEnTaller(d, locale, { dateStyle: 'short', timeStyle: undefined })
}

/**
 * Normaliza string ISO para parsing en JS.
 * Python isoformat() devuelve .123456; algunos navegadores fallan. Truncamos a 3 decimales.
 */
function _normalizarIso(s) {
  const t = s.replace(/\s+/, 'T')
  const m = t.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{1,3})\d*(Z|[-+]\d{2}:?\d{2})?$/)
  if (m) return m[1] + m[2] + (m[3] || '')
  return t
}

/**
 * Parsea ISO de evento de sistema: con Z/offset como instante; naive con hora → UTC (convención BD).
 */
function _parseIsoEventoUtc(iso) {
  if (iso == null || iso === '') return null
  const s = String(iso).trim()
  if (!s) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split('-').map(Number)
    return new Date(Date.UTC(y, m - 1, d, 12, 0, 0))
  }
  const tieneTz = s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s)
  const normalizado = tieneTz ? _normalizarIso(s) : `${_normalizarIso(s).replace(/\.\d+$/, '')}Z`
  const d = new Date(normalizado)
  return isNaN(d.getTime()) ? null : d
}

/** Formatea Date (instante) en hora del taller, no en timezone del navegador. */
function _formatearEnTaller(d, locale, options = {}) {
  if (!d || isNaN(d.getTime())) return '-'
  const out = d.toLocaleString(locale, { timeZone: TALLER_TIMEZONE, ...options })
  return out === 'Invalid Date' ? '-' : out
}

/**
 * Formatea timestamp de evento de sistema (UTC en API con Z) para mostrar en America/Matamoros.
 * Para fecha_ingreso OT usar formatearFechaIngresoOtLocal.
 * Para citas fecha_hora usar formatearFechaHoraLocalNaive.
 */
export function formatearFechaHora(str, locale = 'es-MX') {
  if (str == null || str === '') return '-'
  const d = _parseIsoEventoUtc(str)
  if (!d) return '-'
  return _formatearEnTaller(d, locale)
}
