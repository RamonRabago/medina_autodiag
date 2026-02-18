import { Component } from 'react'

/** Detecta fallos de carga de chunks (deploy nuevo, cache desactualizado). */
function esErrorChunkLoad(error) {
  const msg = (error?.message || '').toLowerCase()
  return (
    msg.includes('dynamically imported') ||
    msg.includes('failed to fetch') ||
    msg.includes('loading chunk') ||
    msg.includes('import()')
  )
}

export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  handleReintentar = () => {
    if (esErrorChunkLoad(this.state.error)) {
      window.location.reload()
      return
    }
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      const esChunk = esErrorChunkLoad(this.state.error)
      return (
        <div className="p-6 bg-white rounded-lg shadow">
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Error al cargar</h2>
          <p className="text-slate-600 text-sm mb-4">{this.state.error?.message || 'Ocurrió un error inesperado.'}</p>
          {esChunk && (
            <p className="text-slate-500 text-xs mb-3">
              Suele ocurrir tras una actualización. Actualizar la página cargará la versión más reciente.
            </p>
          )}
          <button
            onClick={this.handleReintentar}
            className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 text-sm"
          >
            {esChunk ? 'Actualizar página' : 'Reintentar'}
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
