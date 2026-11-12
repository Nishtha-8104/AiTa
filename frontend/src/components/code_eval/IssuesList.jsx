import { useState } from 'react'
import { AlertOctagon, AlertTriangle, CircleCheck, Info, XCircle } from 'lucide-react'
import EmptyState from '../ui/EmptyState'

const SEVERITY = {
  critical: { icon: AlertOctagon,  text: 'text-pop-coral', on: 'border-pop-coral/40 bg-pop-coral/10 text-pop-coral', label: 'Critical' },
  error:    { icon: XCircle,       text: 'text-pop-coral', on: 'border-pop-coral/40 bg-pop-coral/10 text-pop-coral', label: 'Error' },
  warning:  { icon: AlertTriangle, text: 'text-pop-sun',   on: 'border-pop-sun/40 bg-pop-sun/10 text-pop-sun',       label: 'Warning' },
  info:     { icon: Info,          text: 'text-pop-aqua',  on: 'border-pop-aqua/40 bg-pop-aqua/10 text-pop-aqua',    label: 'Info' },
}
const ORDER = ['critical', 'error', 'warning', 'info']

export default function IssuesList({ issues = [] }) {
  const [filter, setFilter] = useState('all')

  if (issues.length === 0) {
    return <EmptyState icon={CircleCheck} title="No issues found" body="The code checker found nothing to flag." />
  }

  const counts = Object.fromEntries(ORDER.map(s => [s, issues.filter(i => i.severity === s).length]))
  const visible = filter === 'all' ? issues : issues.filter(i => i.severity === filter)

  return (
    <div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter issues">
        <button
          type="button"
          aria-pressed={filter === 'all'}
          onClick={() => setFilter('all')}
          className={`h-8 rounded-full border px-3 text-xs font-medium ${filter === 'all' ? 'border-ink bg-ink text-canvas' : 'border-line-strong text-ink-subtle hover:text-ink'}`}
        >
          All {issues.length}
        </button>
        {ORDER.map(s => counts[s] > 0 && (
          <button
            key={s}
            type="button"
            aria-pressed={filter === s}
            onClick={() => setFilter(s)}
            className={`h-8 rounded-full border px-3 text-xs font-medium ${filter === s ? SEVERITY[s].on : 'border-line-strong text-ink-subtle hover:text-ink'}`}
          >
            {counts[s]} {SEVERITY[s].label}
          </button>
        ))}
      </div>

      <ul className="mt-4 divide-y divide-line">
        {visible.map(issue => {
          const cfg = SEVERITY[issue.severity] || SEVERITY.info
          const Icon = cfg.icon
          return (
            <li key={issue.id} className="flex items-start gap-3 py-3.5">
              <Icon size={16} className={`mt-0.5 shrink-0 ${cfg.text}`} aria-label={cfg.label} />
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                  {issue.line && <span className="font-mono text-ink-subtle">Line {issue.line}</span>}
                  <span className="rounded-full bg-tile-3 px-2 py-0.5 capitalize text-ink-muted">{issue.category}</span>
                </div>
                <p className="text-sm leading-relaxed text-ink">{issue.message}</p>
                {issue.suggestion && <p className="mt-1 text-xs leading-relaxed text-ink-subtle">Try: {issue.suggestion}</p>}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
