import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../services/api'

export default function RestablecerContrasena() {
  const [searchParams] = useSearchParams()
  const tokenFromUrl = searchParams.get('token') || ''
  const [token, setToken] = useState(tokenFromUrl)
  const [password, setPassword] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [valido, setValido] = useState(null)
  const [exito, setExito] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (tokenFromUrl) setToken(tokenFromUrl)
  }, [tokenFromUrl])

  useEffect(() => {
    if (!token || token.length < 10) {
      setValido(false)
      return
    }
    api.get('/auth/validar-token-reset', { params: { token }, skipAuthRedirect: true })
      .then((r) => setValido(r.data?.valido ?? false))
      .catch(() => setValido(false))
  }, [token])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < 4) {
      setError('La contraseña debe tener al menos 4 caracteres')
      return
    }
    if (password !== confirmar) {
      setError('Las contraseñas no coinciden')
      return
    }
    setLoading(true)
    try {
      await api.post(
        '/auth/restablecer-contrasena',
        { token, nueva_password: password },
        { skipAuthRedirect: true }
      )
      setExito(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al restablecer. El enlace pudo haber caducado.')
    } finally {
      setLoading(false)
    }
  }

  if (valido === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-200 p-4" style={{ minHeight: '100dvh' }}>
        <div className="bg-white rounded-xl shadow-lg p-8 text-center text-slate-500">Verificando enlace...</div>
      </div>
    )
  }

  if (valido === false && !token) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-slate-200 p-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
        style={{ minHeight: '100dvh' }}
      >
        <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6 sm:p-8">
          <h1 className="text-2xl font-bold text-slate-800 text-center mb-2">Enlace no válido</h1>
          <p className="text-slate-500 text-center mb-6">
            No se detectó un token válido. Usa el enlace que recibiste por email o solicita uno nuevo.
          </p>
          <Link
            to="/olvide-contrasena"
            className="block w-full min-h-[48px] py-3 text-center bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation"
          >
            Solicitar nuevo enlace
          </Link>
          <p className="mt-4 text-center text-sm">
            <Link to="/login" className="text-primary-600 hover:underline">Volver al inicio de sesión</Link>
          </p>
        </div>
      </div>
    )
  }

  if (valido === false) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-slate-200 p-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
        style={{ minHeight: '100dvh' }}
      >
        <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6 sm:p-8">
          <h1 className="text-2xl font-bold text-slate-800 text-center mb-2">Enlace caducado</h1>
          <p className="text-slate-500 text-center mb-6">
            Este enlace ha caducado o ya fue usado. Los enlaces son válidos por 1 hora.
          </p>
          <Link
            to="/olvide-contrasena"
            className="block w-full min-h-[48px] py-3 text-center bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation"
          >
            Solicitar nuevo enlace
          </Link>
          <p className="mt-4 text-center text-sm">
            <Link to="/login" className="text-primary-600 hover:underline">Volver al inicio de sesión</Link>
          </p>
        </div>
      </div>
    )
  }

  if (exito) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-slate-200 p-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
        style={{ minHeight: '100dvh' }}
      >
        <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6 sm:p-8">
          <h1 className="text-2xl font-bold text-slate-800 text-center mb-2">Contraseña actualizada</h1>
          <p className="text-slate-500 text-center mb-6">Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión.</p>
          <Link
            to="/login"
            className="block w-full min-h-[48px] py-3 text-center bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 font-medium touch-manipulation"
          >
            Iniciar sesión
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-slate-200 p-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
      style={{ minHeight: '100dvh' }}
    >
      <div className="w-full max-w-sm bg-white rounded-xl shadow-lg p-6 sm:p-8">
        <h1 className="text-2xl font-bold text-slate-800 text-center mb-2">Nueva contraseña</h1>
        <p className="text-slate-500 text-center mb-6">Ingresa tu nueva contraseña (mínimo 4 caracteres).</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nueva contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
              autoComplete="new-password"
              className="w-full px-4 py-3 text-base border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 min-h-[48px]"
              placeholder="Mínimo 4 caracteres"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Confirmar contraseña</label>
            <input
              type="password"
              value={confirmar}
              onChange={(e) => setConfirmar(e.target.value)}
              required
              minLength={4}
              autoComplete="new-password"
              className="w-full px-4 py-3 text-base border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 min-h-[48px]"
              placeholder="Repite la contraseña"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full min-h-[48px] py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 font-medium touch-manipulation"
          >
            {loading ? 'Guardando...' : 'Restablecer contraseña'}
          </button>
          <p className="mt-4 text-center text-sm text-slate-500">
            <Link to="/login" className="text-primary-600 hover:underline">Volver al inicio de sesión</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
