import { TIERS } from './options'
import { topicLabel } from '../learning/labels'

const GROUPS = [
  { band: 'strong',      label: 'Strengths',       chip: 'border-pop-mint/40 bg-pop-mint/10 text-pop-mint', dot: 'bg-pop-mint' },
  { band: 'needs_work',  label: 'Next focus',      chip: 'border-pop-coral/40 bg-pop-coral/10 text-pop-coral', dot: 'bg-pop-coral' },
  { band: 'ok',          label: 'Doing fine',      chip: 'border-pop-sun/40 bg-pop-sun/10 text-pop-sun', dot: 'bg-pop-sun' },
  { band: 'not_checked', label: 'Not checked yet', chip: 'border-line-strong bg-tile-2 text-ink-subtle', dot: 'bg-white/20' },
]

const ORDER = TIERS.flat()
const rank = t => (ORDER.includes(t) ? ORDER.indexOf(t) : ORDER.length)

export const conceptLine = (card) => {
  if (card.theory_pending) return 'Theory answers being reviewed'
  if (card.concept_level === 'unknown') return 'How well you explain ideas: not checked yet'
  return `How well you explain ideas: ${card.concept_level}`
}

export default function BandSummary({ card, headingLevel = 3 }) {
  const Heading = `h${headingLevel}`
  const inferred = new Set(card.inferred || [])
  const topics = Object.keys(card.bands || {}).sort((a, b) => rank(a) - rank(b))

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {GROUPS.map(({ band, label, chip, dot }) => {
        const list = topics.filter(t => card.bands[t] === band)
        if (!list.length) return null
        return (
          <section key={band} className="rounded-[20px] border border-line bg-tile-2 p-4">
            <Heading className="flex items-center gap-2 text-[13px] font-medium text-ink-muted">
              <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" /> {label}
              <span className="font-mono text-xs text-ink-faint">{list.length}</span>
            </Heading>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {list.map(t => (
                <li key={t} className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${chip} ${inferred.has(t) ? 'border-dashed' : ''}`}>
                  {topicLabel(t)}
                  {inferred.has(t) && <span className="font-normal opacity-75">· inferred</span>}
                </li>
              ))}
            </ul>
          </section>
        )
      })}
      {inferred.size > 0 && (
        <p className="text-xs text-ink-subtle sm:col-span-2">Inferred topics weren't asked directly. They're estimated from your other answers.</p>
      )}
    </div>
  )
}
