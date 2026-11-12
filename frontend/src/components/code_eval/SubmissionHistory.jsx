import { Clock, RefreshCw, Trash2 } from 'lucide-react'
import { languageLabel } from '../learning/labels'
import Skeleton from '../ui/Skeleton'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const m = Math.floor((Date.now() - new Date(dateStr)) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} h ago`
  return `${Math.floor(h / 24)} d ago`
}

export default function SubmissionHistory({ submissions, activeId, loading, onSelect, onDelete, onReEval, disabled }) {
  if (loading && submissions.length === 0) {
    return <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-16 rounded-2xl" />)}</div>
  }
  if (submissions.length === 0) {
    return <p className="py-2 text-sm text-ink-subtle">No saved attempts yet. Evaluate some code and it shows up here.</p>
  }

  return (
    <ul className="space-y-2">
      {submissions.map(sub => {
        const active = sub.id === activeId
        const title = sub.title && sub.title !== `${sub.language} submission` ? sub.title : `${languageLabel(sub.language)} #${sub.id}`
        return (
          <li key={sub.id} className={`rounded-2xl border transition-colors ${active ? 'border-ink bg-tile-3' : 'border-line bg-tile-2'}`}>
            <button
              type="button"
              onClick={() => onSelect(sub.id)}
              disabled={disabled}
              className="flex w-full items-start gap-3 px-3.5 pb-1 pt-3 text-left disabled:cursor-not-allowed"
              title="Load this code into the editor"
            >
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${sub.problem_id ? 'bg-pop-mint' : 'bg-white/20'}`} aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ink">{title}</span>
                <span className="mt-1 flex items-center gap-2 text-[11px] text-ink-subtle">
                  <span className="rounded-md bg-tile-3 px-1.5 py-px font-mono text-ink-muted">{languageLabel(sub.language)}</span>
                  {sub.problem_id ? 'has tests' : 'no tests'}
                  <span className="flex items-center gap-1"><Clock size={10} /> {timeAgo(sub.created_at)}</span>
                </span>
              </span>
            </button>
            <div className="flex items-center gap-1 px-2 pb-2">
              <button
                type="button"
                onClick={() => onReEval(sub.id)}
                disabled={disabled}
                className="flex h-8 items-center gap-1 rounded-full px-2.5 text-xs text-ink-subtle hover:bg-white/[0.06] hover:text-ink disabled:opacity-40"
              >
                <RefreshCw size={12} /> Evaluate again
              </button>
              <button
                type="button"
                onClick={() => onDelete(sub.id)}
                disabled={disabled}
                className="ml-auto flex h-8 items-center gap-1 rounded-full px-2.5 text-xs text-ink-subtle hover:bg-pop-coral/10 hover:text-pop-coral disabled:opacity-40"
                aria-label={`Delete ${title}`}
              >
                <Trash2 size={12} /> Delete
              </button>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
