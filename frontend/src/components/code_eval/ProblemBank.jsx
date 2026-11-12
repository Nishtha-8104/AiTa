import { useEffect, useState } from 'react'
import { Check, Search, X } from 'lucide-react'
import { codeEvalAPI } from '../../utils/api'
import Skeleton from '../ui/Skeleton'

const DIFF_TEXT = { easy: 'text-pop-mint', medium: 'text-pop-sun', hard: 'text-pop-coral' }

export default function ProblemBank({ selected, onPick, onClear }) {
  const [problems, setProblems] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')

  useEffect(() => {
    codeEvalAPI.getProblems()
      .then(({ data }) => setProblems(data))
      .catch(() => setProblems([]))
      .finally(() => setLoading(false))
  }, [])

  const term = query.trim().toLowerCase()
  const shown = term
    ? problems.filter(p => p.title.toLowerCase().includes(term) || (p.topic || '').toLowerCase().includes(term))
    : problems

  return (
    <div>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search size={15} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-subtle" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={`Search ${problems.length || ''} problems by name or topic`}
            aria-label="Search the problem bank"
            className="h-10 w-full rounded-full border border-line-strong bg-tile-2 pl-10 pr-4 text-sm text-ink placeholder:text-ink-faint focus:border-brand-400/70 focus:outline-none"
          />
        </div>
        {selected && (
          <button
            type="button"
            onClick={onClear}
            className="flex h-10 items-center gap-1.5 rounded-full border border-line-strong px-3.5 text-xs font-medium text-ink-muted hover:text-ink"
          >
            <X size={13} /> Clear
          </button>
        )}
      </div>

      {loading ? (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-11 rounded-2xl" />)}
        </div>
      ) : shown.length === 0 ? (
        <p className="py-4 text-sm text-ink-subtle">{problems.length ? 'No problems match.' : 'The problem bank is empty right now.'}</p>
      ) : (
        <div className="mt-3 grid max-h-56 grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          {shown.map(p => {
            const active = selected?.id === p.id
            return (
              <button
                key={p.id}
                type="button"
                aria-pressed={active}
                onClick={() => onPick(p)}
                className={`flex min-h-[44px] items-center gap-2 rounded-2xl border px-3.5 py-2 text-left transition-colors ${
                  active ? 'border-ink bg-tile-3' : 'border-line bg-tile-2 hover:border-ink-faint'
                }`}
              >
                {active && <Check size={14} className="shrink-0 text-pop-mint" />}
                <span className="flex-1 truncate text-sm text-ink">{p.title}</span>
                {p.difficulty && <span className={`shrink-0 text-[11px] ${DIFF_TEXT[p.difficulty] || 'text-ink-subtle'}`}>{p.difficulty}</span>}
                <span className="shrink-0 font-mono text-[11px] text-ink-faint">{p.test_count} tests</span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
