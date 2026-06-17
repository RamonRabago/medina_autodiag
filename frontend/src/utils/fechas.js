/**
 * Utilidades de fechas en hora local.
 * Evita desfases por zona horaria al usar toISOString() o new Date("YYYY-MM-DD").
 */

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
 * Parsea ISO naive de fecha_ingreso OT (hora local del taller, sin Z) como wall-clock local.
 */
function _parseFechaIngresoOtLocal(iso) {
  if (iso == null || iso === '') return null
  const s = String(iso).trim()
  if (!s) return null
  const base = s.replace(/\.\d+$/, '').replace(' ', 'T')
  const m = base.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/)
  if (!m) return null
  const [, y, mo, d, h, mi, se] = m
  return new Date(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(se || 0))
}

/**
 * Muestra fecha_ingreso OT como hora local del taller (naive, sin conversión UTC).
 * Convención TZ-1: el backend envía ISO sin Z; los dígitos son hora de America/Mexico_City.
 */
export function formatearFechaIngresoOtLocal(iso, locale = 'es-MX') {
  const d = _parseFechaIngresoOtLocal(iso)
  if (!d || isNaN(d.getTime())) return '-'
  const out = d.toLocaleString(locale, { dateStyle: 'short', timeStyle: 'short' })
  return out === 'Invalid Date' ? '-' : out
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
  let d
  if (/^\d{4}-\d{2}-\d{2}$/.test(fechaSolo)) {
    d = new Date(fechaSolo + 'T12:00:00')
  } else {
    d = new Date(_normalizarIso(s))
  }
  if (isNaN(d.getTime())) return '-'
  const out = d.toLocaleDateString(locale)
  return out === 'Invalid Date' ? '-' : out
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
 * Formatea string de fecha (YYYY-MM-DD o ISO) para mostrar fecha+hora.
 * Usa T12:00:00 para fecha-solo y evita desfase en zonas negativas.
 */
export function formatearFechaHora(str, locale = 'es-MX') {
  if (str == null || str === '') return '-'
  const s = String(str).trim()
  if (!s) return '-'
  let d
  /* Solo fecha (YYYY-MM-DD) usa T12:00:00; si incluye hora (ISO) parsear como datetime */
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    d = new Date(s + 'T12:00:00')
  } else {
    d = new Date(_normalizarIso(s))
  }
  if (isNaN(d.getTime())) return '-'
  const out = d.toLocaleString(locale)
  return out === 'Invalid Date' ? '-' : out
}
