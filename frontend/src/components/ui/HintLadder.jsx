import { Lightbulb } from 'lucide-react'

export const RUNGS = [
  { level: 1, name: 'Failing case' },
  { level: 2, name: 'Concept' },
  { level: 3, name: 'Steps in words' },
  { level: 4, name: 'Line pointer' },
]

export default function HintLadder({ hints, note = true }) {
  const top = hints.length ? hints[hints.length - 1].level : 0
  return (
    <section className="rounded-[20px] border border-pop-sun/20 bg-pop-sun/[0.05] p-5" aria-label="Hints">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-pop-sun">
          <Lightbulb size={16} /> Hints used: {top} of 4
        </span>
        {note && <span className="text-xs text-ink-subtle">Hints lower this item's score a little.</span>}
      </div>
      <ol className="mt-4 grid grid-cols-4 gap-1.5">
        {RUNGS.map(r => (
          <li key={r.level} className="min-w-0">
            <span className={`block h-1.5 rounded-full ${r.level <= top ? 'bg-pop-sun' : 'bg-white/10'}`} aria-hidden="true" />
            <span className={`mt-1.5 block truncate text-[11px] ${r.level <= top ? 'text-ink-muted' : 'text-ink-faint'}`}>
              L{r.level} · {r.name}
            </span>
          </li>
        ))}
      </ol>
      {hints.length > 0 && (
        <div className="mt-4 space-y-3 border-t border-pop-sun/15 pt-4">
          {hints.map((h, i) => (
            <div key={i}>
              <span className="font-mono text-[11px] text-pop-sun/80">L{h.level} · {RUNGS[h.level - 1]?.name}</span>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">{h.text}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
