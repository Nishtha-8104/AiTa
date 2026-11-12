import { useState } from 'react'
import { AlertTriangle, BookOpen, Box, ChevronDown, Clock, Lightbulb, Sparkles, Target, ThumbsUp } from 'lucide-react'

function Section({ icon: Icon, title, tone = 'text-ink-subtle', children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className="rounded-[20px] border border-line bg-tile-2">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="flex min-h-[48px] w-full items-center justify-between gap-3 px-4 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Icon size={15} className={tone} /> {title}
        </span>
        <ChevronDown size={15} className={`text-ink-subtle transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="border-t border-line px-4 py-4">{children}</div>}
    </section>
  )
}

function MarkdownText({ text }) {
  if (!text) return null
  const parts = text.split(/(```[\s\S]*?```)/g)
  return (
    <div className="space-y-2 text-sm leading-relaxed text-ink-muted">
      {parts.map((part, i) => {
        if (part.startsWith('```')) {
          return (
            <pre key={i} className="overflow-x-auto rounded-2xl border border-line bg-canvas px-4 py-3 font-mono text-[13px] text-ink-muted">
              {part.replace(/^```\w*\n?/, '').replace(/```$/, '')}
            </pre>
          )
        }
        return part.split('\n').map((line, j) => {
          if (line.startsWith('## ')) return <p key={`${i}-${j}`} className="pt-2 text-[15px] font-semibold text-ink">{line.slice(3)}</p>
          if (line.startsWith('### ')) return <p key={`${i}-${j}`} className="pt-1 text-sm font-semibold text-ink">{line.slice(4)}</p>
          if (line.startsWith('- ') || line.startsWith('* ')) {
            return (
              <p key={`${i}-${j}`} className="flex items-start gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-pop-aqua" aria-hidden="true" />
                <span>{line.slice(2).replace(/\*\*(.+?)\*\*/g, '$1')}</span>
              </p>
            )
          }
          if (!line.trim()) return <div key={`${i}-${j}`} className="h-1" />
          return (
            <p key={`${i}-${j}`}>
              {line.split(/(\*\*[^*]+\*\*)/).map((s, k) =>
                s.startsWith('**') ? <strong key={k} className="font-semibold text-ink">{s.slice(2, -2)}</strong> : s)}
            </p>
          )
        })
      })}
    </div>
  )
}

const asText = item => (typeof item === 'string' ? item
  : typeof item === 'object' && item !== null ? (item.msg || item.message || JSON.stringify(item))
  : String(item ?? ''))

function Points({ items, dot = 'bg-pop-aqua' }) {
  if (!items?.length) return <p className="text-xs italic text-ink-faint">None found.</p>
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-ink-muted">
          <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
          {asText(item)}
        </li>
      ))}
    </ul>
  )
}

export default function FeedbackPanel({ evaluation }) {
  if (!evaluation) return null

  const {
    summary, detailed_feedback, key_improvements, learning_points, best_practices_used,
    anti_patterns, suggested_resources, complexity,
  } = evaluation

  return (
    <div className="space-y-3">
      {summary && (
        <div className="flex items-start gap-3 rounded-[20px] border border-line-strong bg-tile-3 p-4">
          <Sparkles size={16} className="mt-0.5 shrink-0 text-pop-mint" />
          <p className="text-sm leading-relaxed text-ink">{summary}</p>
        </div>
      )}

      {(complexity?.time_complexity || complexity?.space_complexity) && (
        <div className="flex flex-wrap gap-x-5 gap-y-2 rounded-[20px] border border-line bg-tile-2 px-4 py-3 text-xs">
          {complexity.time_complexity && (
            <span className="flex items-center gap-1.5 text-ink-subtle"><Clock size={13} className="text-pop-sun" /> Time <code className="font-mono text-sm text-pop-sun">{complexity.time_complexity}</code></span>
          )}
          {complexity.space_complexity && (
            <span className="flex items-center gap-1.5 text-ink-subtle"><Box size={13} className="text-pop-pink" /> Memory <code className="font-mono text-sm text-pop-pink">{complexity.space_complexity}</code></span>
          )}
          {complexity.cyclomatic_complexity && (
            <span className="text-ink-subtle">Branches <code className="font-mono text-sm text-ink">{complexity.cyclomatic_complexity}</code></span>
          )}
          {complexity.lines_of_code && (
            <span className="text-ink-subtle">Lines <code className="font-mono text-sm text-ink">{complexity.lines_of_code}</code></span>
          )}
        </div>
      )}

      <Section icon={ThumbsUp} title="What you did well" tone="text-pop-mint">
        <Points items={best_practices_used} dot="bg-pop-mint" />
      </Section>
      <Section icon={Lightbulb} title="What to improve" tone="text-pop-sun">
        <Points items={key_improvements} dot="bg-pop-sun" />
      </Section>
      {anti_patterns?.length > 0 && (
        <Section icon={AlertTriangle} title="Habits to avoid" tone="text-pop-coral" defaultOpen={false}>
          <Points items={anti_patterns} dot="bg-pop-coral" />
        </Section>
      )}
      {detailed_feedback && (
        <Section icon={Sparkles} title="Detailed feedback" tone="text-pop-aqua" defaultOpen={false}>
          <MarkdownText text={detailed_feedback} />
        </Section>
      )}
      {learning_points?.length > 0 && (
        <Section icon={Target} title="Ideas to revisit" tone="text-pop-pink">
          <Points items={learning_points} dot="bg-pop-pink" />
        </Section>
      )}
      {suggested_resources?.length > 0 && (
        <Section icon={BookOpen} title="Topics to study" tone="text-pop-aqua">
          <Points items={suggested_resources} />
        </Section>
      )}
    </div>
  )
}
