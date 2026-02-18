/**
 * Skeleton para tablas. Muestra filas con celdas animadas durante la carga.
 * @param {number} rows - Número de filas
 * @param {number} cols - Número de columnas
 */
export default function TableSkeleton({ rows = 8, cols = 10 }) {
  const getWidth = (colIdx) => {
    if (colIdx === 0) return 'w-10' // Foto
    if (colIdx === 1) return 'w-16' // Código
    if (colIdx === 2) return 'w-32' // Nombre (más largo)
    if (colIdx < 6) return 'w-20'   // Categoría, Bodega, Ubicación
    if (colIdx < 9) return 'w-12'   // Stock, Stock mín, Precio
    return 'w-16'                   // Estado, Kardex, Acciones
  }
  return (
    <>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <tr key={rowIdx} className="animate-pulse">
          {Array.from({ length: cols }).map((_, colIdx) => (
            <td
              key={colIdx}
              className={`px-4 py-3 ${colIdx === 0 ? 'text-center' : colIdx >= 6 && colIdx <= 8 ? 'text-right' : ''}`}
            >
              <div
                className={`h-4 bg-slate-200 rounded ${colIdx === 0 ? 'w-10 h-10 mx-auto' : getWidth(colIdx)}`}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}
