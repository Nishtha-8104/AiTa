// ConceptMap — renders concept_map {topic: score} as a horizontal bar chart
export default function ConceptMap({ conceptMap = {} }) {
  const entries = Object.entries(conceptMap).sort((a, b) => a[1] - b[1])
  if (!entries.length) return null

  function scoreColor(s) {
    if (s >= 0.75) return { bar: 'bg-green-500',  text: 'text-green-400',  label: 'Strong'  }
    if (s >= 0.50) return { bar: 'bg-yellow-500', text: 'text-yellow-400', label: 'Developing' }
    if (s >= 0.25) return { bar: 'bg-orange-500', text: 'text-orange-400', label: 'Weak' }
    return           { bar: 'bg-red-500',    text: 'text-red-400',    label: 'Gap'    }
  }

  return (
    <div className="space-y-2.5">
      {entries.map(([topic, score]) => {
        const c = scoreColor(score)
        const pct = Math.round(score * 100)
        return (
          <div key={topic}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-white/70 text-xs font-mono capitalize">{topic}</span>
              <span className={`text-xs font-mono font-600 ${c.text}`}>{pct}% · {c.label}</span>
            </div>
            <div className="h-1.5 bg-surface-600 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${c.bar}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}