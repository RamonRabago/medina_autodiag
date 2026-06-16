import { Link } from 'react-router-dom'

/**
 * Tarjeta contador reutilizable para dashboard ADMIN (P5.1).
 */
export default function KPIWidget({ label, value, to, hint, valueClassName = 'text-slate-800' }) {
  const content = (
    <>
      <h3 className="text-slate-500 text-sm font-medium">{label}</h3>
      <p className={`text-2xl font-bold mt-1 ${valueClassName}`}>{value ?? 0}</p>
      {hint && <p className="text-xs text-slate-400 mt-2">{hint}</p>}
    </>
  )

  const baseClass =
    'bg-white rounded-lg shadow p-4 sm:p-6 border-2 border-transparent transition-all touch-manipulation min-h-[88px] flex flex-col justify-center'

  if (to) {
    return (
      <Link to={to} className={`${baseClass} block hover:border-primary-200 hover:shadow-md`}>
        {content}
      </Link>
    )
  }

  return <div className={baseClass}>{content}</div>
}
