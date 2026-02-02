import { Component } from 'react'

export default class ErrorBoundary extends Component {
  state = { hasError: false, error: null }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 bg-white rounded-lg shadow">
          <h2 className="text-lg font-semibold text-slate-800 mb-2">Error al cargar</h2>
          <p className="text-slate-600 text-sm mb-4">{this.state.error?.message || 'Ocurrió un error inesperado.'}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 text-sm"
          >
            Reintentar
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
