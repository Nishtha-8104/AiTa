import { TIERS } from './options'
import { topicLabel } from '../learning/labels'

const STATES = {
  asking:     { label: 'Asking now',  chip: 'border-ink bg-ink text-canvas motion-safe:animate-pulse', dot: 'bg-ink' },
  strong:     { label: 'Strong',      chip: 'border-pop-mint/40 bg-pop-mint/10 text-pop-mint', dot: 'bg-pop-mint' },
  ok:         { label: 'Passed',      chip: 'border-pop-sun/40 bg-pop-sun/10 text-pop-sun', dot: 'bg-pop-sun' },
  needs_work: { label: 'Needs work',  chip: 'border-pop-coral/40 bg-pop-coral/10 text-pop-coral', dot: 'bg-pop-coral' },
  inferred:   { label: 'Inferred',    chip: 'border-dashed border-pop-aqua/50 bg-transparent text-pop-aqua', dot: 'border border-dashed border-pop-aqua' },
  skipped:    { label: 'Skipped',     chip: 'border-line-strong bg-transparent italic text-ink-faint', dot: 'bg-ink-faint' },
  unknown:    { label: 'Not checked', chip: 'border-line bg-tile-2 text-ink-subtle', dot: 'bg-white/15' },
}

export default function TopicMap({ states = {}, note }) {
  return (
    <section aria-label="Topic map" className="tile p-5">
      <p className="eyebrow">Topic map</p>
      {note && <p className="mt-2 text-xs leading-relaxed text-ink-subtle">{note}</p>}
      <ol className="mt-4 space-y-2.5">
        {TIERS.map((tier, i) => (
          <li key={i} className="flex items-start gap-2.5">
            <span className="w-6 shrink-0 pt-1 font-mono text-[10px] text-ink-faint">T{i + 1}</span>
            <ul className="flex flex-wrap gap-1.5">
              {tier.map(topic => {
                const s = STATES[states[topic]] || STATES.unknown
                return (
                  <li key={topic} className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium leading-tight transition-colors duration-500 ${s.chip}`} title={s.label}>
                    {topicLabel(topic)}<span className="sr-only">: {s.label}</span>
                  </li>
                )
              })}
            </ul>
          </li>
        ))}
      </ol>
      <ul aria-hidden="true" className="mt-5 flex flex-wrap gap-x-3 gap-y-2 border-t border-line pt-4">
        {Object.entries(STATES).map(([key, s]) => (
          <li key={key} className="flex items-center gap-1.5 text-[11px] text-ink-subtle">
            <span className={`h-2 w-2 rounded-full ${s.dot}`} />
            {s.label}
          </li>
        ))}
      </ul>
    </section>
  )
}
