/**
 * Interpreta el texto del buscador para precargar nombre o teléfono en alta rápida.
 */
export function parseTextoBusquedaCliente(texto) {
  const t = (texto || '').trim()
  if (!t) return { nombre: '', telefono: '' }

  const limpio = t.replace(/[\s\-\(\)]/g, '')
  let digitos = limpio.replace(/\D/g, '')
  if (digitos.startsWith('52') && digitos.length > 10) {
    digitos = digitos.slice(2)
  }

  const pareceTelefono =
    /^\d{7,15}$/.test(digitos) ||
    (digitos.length >= 7 && digitos.length >= limpio.replace(/\+/g, '').length * 0.8)

  if (pareceTelefono) {
    return { nombre: '', telefono: t }
  }
  return { nombre: t, telefono: '' }
}

export function textoCliente(cliente) {
  if (!cliente) return ''
  const tel = cliente.telefono ? ` (${cliente.telefono})` : ''
  return `${cliente.nombre || ''}${tel}`.trim()
}
