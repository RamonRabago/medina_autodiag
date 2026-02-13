import { useState, useEffect, useRef } from 'react'
import api from '../services/api'

const POLL_INTERVAL_MS = 5 * 60 * 1000 // 5 minutos

/**
 * Detecta cuando hay una nueva versión desplegada y muestra banner para recargar.
 * Evita que el usuario tenga que pulsar F5 manualmente tras un deploy.
 */
export default function VersionCheck() {
  const [showBanner, setShowBanner] = useState(false)
  const initialBuildRev = useRef(null)

  useEffect(() => {
    const check = async () => {
      try {
        const { data } = await api.get('/config', {
          params: { t: Date.now() },
          skipAuthRedirect: true,
        })
        const rev = data?.build_rev || 'unknown'

        if (initialBuildRev.current === null) {
          initialBuildRev.current = rev
        } else if (rev !== 'unknown' && rev !== initialBuildRev.current) {
          setShowBanner(true)
        }
      } catch {
        // Silenciar errores (red, 401, etc.)
      }
    }

    check()
    const id = setInterval(check, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  if (!showBanner) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-primary-600 text-white px-4 py-3 flex flex-wrap items-center justify-center gap-3 shadow-lg" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom, 0.75rem))' }}>
      <span className="text-sm font-medium">Nueva versión disponible. Recarga para ver los cambios.</span>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="px-4 py-2 bg-white text-primary-600 rounded-lg font-medium hover:bg-primary-50 active:bg-primary-100 min-h-[44px] touch-manipulation"
      >
        Recargar
      </button>
    </div>
  )
}
