/**
 * Utilidades para parsear y validar números en formularios.
 * Evita enviar NaN al API por entradas no numéricas.
 */

/**
 * Parsea valor a número. Retorna valor por defecto si es inválido.
 * Acepta coma como separador decimal.
 */
export function aNumero(val, def = 0) {
  if (val === '' || val === null || val === undefined) return def
  const s = String(val).trim().replace(',', '.')
  const n = parseFloat(s)
  return Number.isFinite(n) ? n : def
}

/**
 * Parsea a entero. Retorna valor por defecto si es inválido.
 */
export function aEntero(val, def = 0) {
  if (val === '' || val === null || val === undefined) return def
  const n = parseInt(String(val).trim(), 10)
  return Number.isFinite(n) ? n : def
}

/**
 * Devuelve true si el valor es un número finito válido.
 */
export function esNumeroValido(val) {
  if (val === '' || val === null || val === undefined) return false
  const n = parseFloat(String(val).trim().replace(',', '.'))
  return Number.isFinite(n)
}
