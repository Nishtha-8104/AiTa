import { Check } from 'lucide-react'

export default function Stepper({ steps, current, label = 'Progress' }) {
  const active = steps[current]
  return (
    <nav aria-label={label}>
      <p className="mb-3 text-xs text-ink-subtle sm:hidden">
        Step {current + 1} of {steps.length} · <span className="font-medium text-ink">{active?.label}</span>
      </p>
      <ol className="grid gap-2" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((s, i) => {
          const done = i < current
          const now = i === current
          return (
            <li key={s.key} aria-current={now ? 'step' : undefined} className="min-w-0">
              <span className={`block h-1.5 rounded-full transition-colors duration-500 ${done ? 'bg-pop-mint' : now ? 'bg-ink' : 'bg-white/10'}`} />
              <span className={`mt-2 hidden items-center gap-1 truncate text-xs sm:flex ${now ? 'font-medium text-ink' : done ? 'text-ink-muted' : 'text-ink-faint'}`}>
                {done && <Check size={12} className="shrink-0 text-pop-mint" />}
                {s.label}
              </span>
              <span className="sr-only">{done ? ' (done)' : now ? ' (current)' : ''}</span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
