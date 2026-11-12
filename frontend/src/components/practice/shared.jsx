import toast from 'react-hot-toast'
import { TrendingUp } from 'lucide-react'

// Empty unless GAMIFICATION_MODE is live.
export function toastAwards(data) {
  (data.awards || []).forEach(a => toast.success(a.points ? `+${a.points} · ${a.title}` : a.title))
}

export function LevelNote({ after }) {
  if (after == null) return null
  return (
    <span className="inline-flex items-center gap-1.5 text-ink-muted">
      <TrendingUp size={13} className="text-pop-mint" /> Topic level now {Math.round(after * 100)}%
    </span>
  )
}

export function Panel({ title, eyebrow, children, className = '', actions }) {
  return (
    <section className={`tile p-5 sm:p-6 ${className}`}>
      {(title || eyebrow || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <h2 className="mt-1.5 text-lg font-semibold tracking-tight text-ink">{title}</h2>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  )
}
