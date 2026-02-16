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
  if (/^\d{4}-\d{2}-\d{2}$/.test(s.slice(0, 10))) {
    d = new Date(s + 'T12:00:00')
  } else {
    d = new Date(_normalizarIso(s))
  }
  if (isNaN(d.getTime())) return '-'
  const out = d.toLocaleString(locale)
  return out === 'Invalid Date' ? '-' : out
}
