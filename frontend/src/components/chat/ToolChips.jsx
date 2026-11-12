import { AlertTriangle, BarChart3, BookOpen, Lightbulb, Loader2, Play, Wrench } from 'lucide-react'

const TONES = {
  sky:     'text-pop-aqua bg-pop-aqua/10 border-pop-aqua/25',
  violet:  'text-pop-pink bg-pop-pink/10 border-pop-pink/25',
  emerald: 'text-pop-mint bg-pop-mint/10 border-pop-mint/25',
  amber:   'text-pop-sun bg-pop-sun/10 border-pop-sun/25',
  rose:    'text-pop-coral bg-pop-coral/10 border-pop-coral/25',
  muted:   'text-ink-subtle bg-white/[0.04] border-line-strong',
}

const TOOLS = {
  search_books:        { icon: BookOpen,  short: 'Books',    running: 'Searching the books',    tone: 'sky' },
  query_learning_data: { icon: BarChart3, short: 'Progress', running: 'Checking your progress', tone: 'violet' },
  evaluate_code:       { icon: Play,      short: 'Tests',    running: 'Running your code',      tone: 'emerald' },
  get_hint:            { icon: Lightbulb, short: 'Hint',     running: 'Preparing a hint',       tone: 'amber' },
}

const FALLBACK = { icon: Wrench, short: 'Tool', running: 'Working', tone: 'muted' }

function describe(trace) {
  const tool = TOOLS[trace.name] || FALLBACK
  const summary = (trace.summary || '').replace(/_/g, ' ')
  if (trace.ok === false) {
    return { icon: AlertTriangle, tone: 'rose', label: `${tool.short}: ${summary || 'failed'}` }
  }
  if (trace.name === 'search_books') {
    const n = parseInt(summary, 10)
    return { ...tool, label: n ? `${n} source${n === 1 ? '' : 's'}` : 'no sources found' }
  }
  if (trace.name === 'query_learning_data') {
    return { ...tool, label: `progress · ${summary || 'records'}` }
  }
  if (trace.name === 'evaluate_code') {
    const score = summary.match(/^(\d+)\/(\d+)/)
    if (score) {
      const [passed, total] = [Number(score[1]), Number(score[2])]
      return { ...tool, label: `${passed}/${total} tests`, tone: passed === total ? 'emerald' : 'amber' }
    }
    return { ...tool, label: summary || 'evaluated', tone: summary === 'compile error' ? 'rose' : 'muted' }
  }
  if (trace.name === 'get_hint') {
    const level = summary.match(/^hint L(\d)/)
    return { ...tool, label: level ? `hint L${level[1]}` : summary || 'hint' }
  }
  return { ...tool, label: summary || trace.name }
}

function timing(trace) {
  const name = trace.name || 'tool'
  return typeof trace.ms === 'number' ? `${name} · ${(trace.ms / 1000).toFixed(1)}s` : name
}

export default function ToolChips({ traces }) {
  if (!traces?.length) return null
  return (
    <div className="mb-2 flex flex-wrap gap-1.5">
      {traces.map((trace, i) => {
        if (trace.running) {
          const tool = TOOLS[trace.name] || FALLBACK
          return (
            <span key={i} className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${TONES[tool.tone]}`}>
              <Loader2 size={11} className="animate-spin" />
              {tool.running}…
            </span>
          )
        }
        const chip = describe(trace)
        const Icon = chip.icon
        return (
          <span key={i} title={timing(trace)} className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${TONES[chip.tone]}`}>
            <Icon size={11} />
            {chip.label}
          </span>
        )
      })}
    </div>
  )
}
