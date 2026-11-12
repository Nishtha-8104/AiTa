function level(s) {
  if (s >= 0.75) return { bar: 'bg-pop-mint', text: 'text-pop-mint', label: 'Strong' }
  if (s >= 0.5) return { bar: 'bg-pop-sun', text: 'text-pop-sun', label: 'Developing' }
  if (s >= 0.25) return { bar: 'bg-pop-coral', text: 'text-pop-coral', label: 'Weak' }
  return { bar: 'bg-pop-coral', text: 'text-pop-coral', label: 'Gap' }
}

export default function ConceptMap({ conceptMap = {} }) {
  const entries = Object.entries(conceptMap).sort((a, b) => a[1] - b[1])
  if (!entries.length) return null

  return (
    <ul className="space-y-3">
      {entries.map(([topic, score]) => {
        const c = level(score)
        const pct = Math.round(score * 100)
        return (
          <li key={topic}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="capitalize text-ink-muted">{topic.replace(/_/g, ' ')}</span>
              <span className={`font-mono text-xs ${c.text}`}>{pct}% · {c.label}</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
              <div className={`h-full rounded-full ${c.bar}`} style={{ width: `${pct}%` }} />
            </div>
          </li>
        )
      })}
    </ul>
  )
}
