import { CircleCheck, CircleDashed, CircleX, Info } from 'lucide-react'

const TONES = {
  correct: { icon: CircleCheck, box: 'border-pop-mint/25 bg-pop-mint/[0.06]', text: 'text-pop-mint' },
  partial: { icon: CircleDashed, box: 'border-pop-sun/25 bg-pop-sun/[0.06]', text: 'text-pop-sun' },
  wrong:   { icon: CircleX, box: 'border-pop-coral/25 bg-pop-coral/[0.06]', text: 'text-pop-coral' },
  neutral: { icon: Info, box: 'border-line-strong bg-tile-2', text: 'text-ink' },
}

export function toneFor(passed, total) {
  if (total > 0 && passed === total) return 'correct'
  if (passed > 0) return 'partial'
  return 'wrong'
}

export default function Verdict({ tone = 'neutral', title, meta, children, className = '' }) {
  const t = TONES[tone]
  const Icon = t.icon
  return (
    <section className={`rounded-[20px] border p-5 motion-safe:animate-rise ${t.box} ${className}`} aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className={`flex items-center gap-2 text-[15px] font-semibold ${t.text}`}>
          <Icon size={18} strokeWidth={2.2} /> {title}
        </h3>
        {meta && <div className="font-mono text-xs text-ink-subtle">{meta}</div>}
      </div>
      {children && <div className="mt-3 text-sm leading-relaxed text-ink-muted">{children}</div>}
    </section>
  )
}
