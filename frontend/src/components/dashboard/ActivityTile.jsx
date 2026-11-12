import { CircleCheck, CircleDashed, CircleX } from 'lucide-react'
import { EVENT_KIND_LABELS, misconceptionLabel, topicLabel } from '../learning/labels'
import Chip from '../ui/Chip'

function ago(iso) {
  const t = new Date(iso).getTime()
  if (!t) return ''
  const s = (Date.now() - t) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  if (s < 604800) return `${Math.floor(s / 86400)} d ago`
  return new Date(t).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

function outcome(score) {
  if (score >= 0.999) return { icon: CircleCheck, tone: 'bg-pop-mint/15 text-pop-mint', word: 'Correct' }
  if (score > 0) return { icon: CircleDashed, tone: 'bg-pop-sun/15 text-pop-sun', word: 'Partly right' }
  return { icon: CircleX, tone: 'bg-pop-coral/15 text-pop-coral', word: 'Not quite' }
}

function EventRow({ event }) {
  const { icon: Icon, tone, word } = outcome(event.score)
  const delta = event.mastery_before != null ? Math.round((event.mastery_after - event.mastery_before) * 100) : null
  const meta = [ago(event.created_at), event.hint_level_used > 0 && `hint L${event.hint_level_used}`].filter(Boolean).join(' · ')
  return (
    <li className="flex items-center gap-3 py-3">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${tone}`}>
        <Icon size={18} strokeWidth={2} aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">
          {EVENT_KIND_LABELS[event.kind] || event.kind} · {topicLabel(event.topic)}
        </p>
        <p className="mt-0.5 truncate text-xs text-ink-subtle">
          <span className="sr-only">{word}. </span>{Math.round(event.score * 100)}% score{meta && ` · ${meta}`}
        </p>
      </div>
      {delta !== null && (
        <span className={`shrink-0 text-right font-mono text-sm ${delta > 0 ? 'text-pop-mint' : delta < 0 ? 'text-pop-coral' : 'text-ink-subtle'}`}>
          {delta > 0 ? `+${delta}` : delta}
          <span className="block font-body text-[10px] text-ink-faint">level</span>
        </span>
      )}
    </li>
  )
}

export default function ActivityTile({ mastery, wide = false }) {
  const events = mastery.recent_events.slice(0, wide ? 6 : 5)
  const mistakes = mastery.top_misconceptions.slice(0, 5)

  return (
    <section className={`tile h-full p-6 ${wide ? 'md:grid md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] md:gap-8' : ''}`}>
      <div>
        <p className="eyebrow">Recent activity</p>
        {events.length === 0 ? (
          <p className="mt-4 text-[13px] text-ink-subtle">Nothing graded yet. Your answers show up here with how they moved your topic level.</p>
        ) : (
          <ul className="mt-2 divide-y divide-line">
            {events.map(e => <EventRow key={e.id} event={e} />)}
          </ul>
        )}
      </div>

      <div className={wide ? 'mt-6 border-t border-line pt-5 md:mt-0 md:border-l md:border-t-0 md:pl-8 md:pt-0' : 'mt-4 border-t border-line pt-5'}>
        <p className="eyebrow">Mistakes you repeat</p>
        {mistakes.length === 0 ? (
          <p className="mt-3 text-[13px] text-ink-subtle">None recorded yet.</p>
        ) : (
          <ul className="mt-3 flex flex-wrap gap-2">
            {mistakes.map(m => (
              <li key={m.tag}>
                <Chip tone="sun">{misconceptionLabel(m.tag)} <span className="font-mono opacity-80">×{m.count}</span></Chip>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs leading-relaxed text-ink-subtle">
          Average hint level on your last 10 coding tries:{' '}
          <span className="font-mono text-ink">{mastery.hint_reliance > 0 ? `${mastery.hint_reliance.toFixed(1)} of 4` : 'no hints'}</span>
        </p>
      </div>
    </section>
  )
}
