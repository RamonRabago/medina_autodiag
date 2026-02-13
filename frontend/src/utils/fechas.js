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
  if (!str) return '-'
  const s = String(str).trim().slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return new Date(str).toLocaleDateString(locale)
  return new Date(s + 'T12:00:00').toLocaleDateString(locale)
}

/**
 * Formatea string de fecha (YYYY-MM-DD o ISO) para mostrar fecha+hora.
 * Usa T12:00:00 para fecha-solo y evita desfase en zonas negativas.
 */
export function formatearFechaHora(str, locale = 'es-MX') {
  if (!str) return '-'
  const s = String(str).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(s.slice(0, 10))) return new Date(s + 'T12:00:00').toLocaleString(locale)
  return new Date(s).toLocaleString(locale)
}
