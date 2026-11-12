import { BAND_STYLE } from '../learning/labels'
import { palette } from '../../styles/palette'

const INNER = 38
const MAX_LEN = 50
const MIN_LEN = 5

export default function TopicRing({ topics }) {
  const practised = topics.filter(t => t.evidence_count > 0)
  const counts = ['mastered', 'developing', 'weak'].map(b => ({ band: b, n: practised.filter(t => t.band === b).length }))
  const summary = counts.map(c => `${c.n} ${BAND_STYLE[c.band].label.toLowerCase()}`).join(', ')
  const step = 360 / topics.length

  return (
    <section className="tile flex h-full flex-col p-6">
      <p className="eyebrow">At a glance</p>
      <div className="flex flex-1 flex-col">
      <div className="relative mx-auto mt-6 aspect-square w-full max-w-[220px]">
        <svg viewBox="0 0 200 200" className="h-full w-full" role="img" aria-label={`${practised.length} of ${topics.length} topics practised: ${summary}`}>
          <g className="origin-center [transform-box:fill-box] motion-safe:animate-spin-slow">
            <circle cx="100" cy="100" r="96" fill="none" stroke={palette.pop.sun} strokeOpacity="0.55" strokeWidth="1.5" strokeDasharray="5 6" />
          </g>
          {topics.map((t, i) => {
            const seen = t.evidence_count > 0
            const len = seen ? MIN_LEN + t.mastery * MAX_LEN : MIN_LEN
            const color = seen ? (BAND_STYLE[t.band] || BAND_STYLE.unseen).hex : 'rgba(255,255,255,0.1)'
            return (
              <line
                key={t.topic}
                x1="100" y1={100 - INNER} x2="100" y2={100 - INNER - len}
                transform={`rotate(${i * step} 100 100)`}
                stroke={color}
                strokeOpacity={t.unlocked ? 1 : 0.4}
                strokeWidth="11"
                strokeLinecap="round"
              >
                <title>{`${t.label}: ${seen ? `${Math.round(t.mastery * 100)}%` : 'not yet practised'}`}</title>
              </line>
            )
          })}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-semibold text-ink">{practised.length}<span className="text-ink-faint">/{topics.length}</span></span>
          <span className="text-[11px] text-ink-subtle">practised</span>
        </div>
      </div>
      <ul className="mb-5 mt-5 flex flex-wrap justify-center gap-x-4 gap-y-1.5">
        {counts.map(({ band, n }) => (
          <li key={band} className="flex items-center gap-1.5 text-xs text-ink-subtle">
            <span className={`h-2 w-2 rounded-full ${BAND_STYLE[band].bar}`} aria-hidden="true" />
            <span className="font-mono text-ink">{n}</span> {BAND_STYLE[band].label}
          </li>
        ))}
      </ul>
      <p className="mt-auto border-t border-line pt-4 text-xs leading-relaxed text-ink-subtle">
        Each spoke is one topic. A longer spoke means a higher topic level. Grey stubs are topics you haven't practised yet.
      </p>
      </div>
    </section>
  )
}
