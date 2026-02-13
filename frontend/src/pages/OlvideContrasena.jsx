import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { normalizeDetail } from '../utils/toast'

export default function OlvideContrasena() {
  const [email, setEmail] = useState('')
  const [enviado, setEnviado] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/olvide-contrasena', { email: email.trim() }, { skipAuthRedirect: true })
      setEnviado(true)
    } catch (err) {
      setError(normalizeDetail(err.response?.data?.detail) || 'Error al enviar. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-slate-200 p-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
      style={{ minHeight: '100dvh' }}
    >
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6 sm:p-8">
        <h1 className="text-2xl font-bold text-slate-800 text-center mb-2">Recuperar contraseña</h1>
        <p className="text-slate-500 text-center mb-6">Ingresa tu email y te enviaremos un enlace para restablecer tu contraseña.</p>

        {enviado ? (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 text-green-800 rounded-lg text-sm">
              Si el email está registrado, recibirás un enlace en los próximos minutos. Revisa también la carpeta de spam.
            </div>
            <Link
              to="/login"
              className="block w-full min-h-[48px] py-3 text-center border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 active:bg-slate-100 font-medium touch-manipulation"
            >
              Volver al inicio de sesión
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full px-4 py-3 text-base border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 min-h-[48px]"
                placeholder="tu@email.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full min-h-[48px] py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 font-medium touch-manipulation"
            >
              {loading ? 'Enviando...' : 'Enviar enlace'}
            </button>
            <p className="mt-4 text-center text-sm text-slate-500">
              <Link
                to="/login"
                className="text-primary-600 hover:underline min-h-[44px] leading-normal touch-manipulation inline-block"
              >
                Volver al inicio de sesión
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
