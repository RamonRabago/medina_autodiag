import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const params = new URLSearchParams({ username: email, password })
      const res = await api.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      const token = res.data.access_token
      const payload = JSON.parse(atob(token.split('.')[1]))
      const userData = {
        id_usuario: parseInt(payload.sub),
        email: email,
        nombre: email.split('@')[0],
        rol: payload.rol || 'EMPLEADO',
      }
      login(token, userData)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Credenciales inválidas')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="h-full min-h-screen flex items-center justify-center bg-slate-200 p-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] overflow-y-auto"
      style={{ minHeight: '100dvh' }}
    >
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6 sm:p-8">
        <h1 className="text-2xl font-bold text-slate-800 text-center mb-2">MedinaAutoDiag</h1>
        <p className="text-slate-500 text-center mb-6">Taller mecánico</p>
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
              placeholder="admin@ejemplo.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full px-4 py-3 text-base border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 min-h-[48px]"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full min-h-[48px] py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 font-medium touch-manipulation"
          >
            {loading ? 'Entrando...' : 'Iniciar sesión'}
          </button>
          <p className="mt-4 text-center text-sm text-slate-500 space-y-1">
            <Link
              to="/olvide-contrasena"
              className="block text-primary-600 hover:underline min-h-[44px] leading-normal touch-manipulation"
            >
              ¿Olvidaste tu contraseña?
            </Link>
            <Link
              to="/registro"
              className="block text-primary-600 hover:underline min-h-[44px] leading-normal touch-manipulation"
            >
              ¿Primera vez? Crear cuenta
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
