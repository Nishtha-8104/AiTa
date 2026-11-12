import { useState } from 'react'
import { AlertTriangle, ArrowRight, BookOpen, Brain, CheckCircle2, ChevronDown, Clock, Lightbulb, Star, Target } from 'lucide-react'
import Chip from '../ui/Chip'
import ConceptMap from './ConceptMap'
import AgentSteps from './AgentSteps'

const TYPE = {
  code_review:    { label: 'Code review', tone: 'sun' },
  learning_recap: { label: 'Learning recap', tone: 'aqua' },
  combined:       { label: 'Full report', tone: 'pink' },
}
const TONE = {
  encouraging:  'Encouraging',
  constructive: 'Constructive',
  challenging:  'Challenging',
}

function Section({ icon: Icon, title, tone, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className="tile">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="flex min-h-[52px] w-full items-center justify-between gap-3 px-5 text-left"
      >
        <span className="flex items-center gap-2.5 text-[15px] font-semibold text-ink">
          <Icon size={16} className={tone} /> {title}
        </span>
        <ChevronDown size={15} className={`text-ink-subtle transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="border-t border-line px-5 py-4">{children}</div>}
    </section>
  )
}

function Points({ items = [], dot }) {
  if (!items.length) return <p className="text-xs italic text-ink-faint">None found.</p>
  return (
    <ul className="space-y-2.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2.5 text-sm leading-relaxed text-ink-muted">
          <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
          {item}
        </li>
      ))}
    </ul>
  )
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const m = Math.floor((Date.now() - new Date(dateStr)) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} h ago`
  return `${Math.floor(h / 24)} d ago`
}

export default function FeedbackCard({ report }) {
  if (!report) return null
  const type = TYPE[report.feedback_type] || TYPE.code_review

  return (
    <div className="space-y-4">
      <section className="tile p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={type.tone}>{type.label}</Chip>
          {TONE[report.tone] && <Chip>{TONE[report.tone]}</Chip>}
          {report.pattern_only && (
            <Chip tone="sun" icon={AlertTriangle}>Built from your mistake patterns only</Chip>
          )}
          <span className="ml-auto flex items-center gap-1 font-mono text-xs text-ink-subtle">
            <Clock size={11} /> {timeAgo(report.created_at)}
          </span>
        </div>

        <h2 className="mt-4 text-xl font-semibold leading-snug tracking-tight text-ink sm:text-2xl">{report.headline || 'Feedback report'}</h2>
        {report.summary && <p className="mt-3 max-w-[70ch] text-[15px] leading-relaxed text-ink-muted">{report.summary}</p>}

        {report.motivational && (
          <div className="mt-5 flex items-start gap-3 rounded-[18px] border border-pop-pink/20 bg-pop-pink/[0.06] px-4 py-3">
            <Star size={15} className="mt-0.5 shrink-0 text-pop-pink" fill="currentColor" />
            <p className="text-sm italic leading-relaxed text-ink-muted">{report.motivational}</p>
          </div>
        )}

        {report.evaluation_id && (
          <p className="mt-5 border-t border-line pt-3 text-xs text-ink-subtle">
            Based on Code workspace attempt <span className="font-mono text-ink-muted">#{report.evaluation_id}</span>
          </p>
        )}
      </section>

      <Section icon={Target} title="Do these next" tone="text-pop-pink">
        {report.action_items?.length > 0 ? (
          <ol className="space-y-3">
            {report.action_items.map((item, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-pop-pink font-mono text-xs font-semibold text-canvas">{i + 1}</span>
                <span className="pt-0.5 text-sm leading-relaxed text-ink-muted">{item}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-xs italic text-ink-faint">Nothing to do right now.</p>
        )}
      </Section>

      <div className={`grid grid-cols-1 gap-4 ${report.errors?.length > 0 ? 'lg:grid-cols-2' : ''}`}>
        <Section icon={CheckCircle2} title="What you did well" tone="text-pop-mint">
          <Points items={report.strengths} dot="bg-pop-mint" />
        </Section>
        {report.errors?.length > 0 && (
          <Section icon={AlertTriangle} title="Mistakes found" tone="text-pop-coral">
            <Points items={report.errors} dot="bg-pop-coral" />
          </Section>
        )}
      </div>

      {report.misconceptions?.length > 0 && (
        <Section icon={Brain} title="Ideas that got mixed up" tone="text-pop-sun">
          <Points items={report.misconceptions} dot="bg-pop-sun" />
        </Section>
      )}

      {Object.keys(report.concept_map || {}).length > 0 && (
        <Section icon={BookOpen} title="Concept map for this report" tone="text-pop-aqua" defaultOpen={false}>
          <p className="mb-4 text-xs leading-relaxed text-ink-subtle">
            An estimate for this report only. Your measured topic levels, from graded answers, are on Home.
          </p>
          <ConceptMap conceptMap={report.concept_map} />
        </Section>
      )}

      {report.next_topics?.length > 0 && (
        <Section icon={Lightbulb} title="Study these next" tone="text-pop-aqua" defaultOpen={false}>
          <ul className="flex flex-wrap gap-2">
            {report.next_topics.map((t, i) => (
              <li key={i}><Chip tone="aqua" icon={ArrowRight}>{t}</Chip></li>
            ))}
          </ul>
        </Section>
      )}

      <AgentSteps steps={report.agent_steps || []} />
    </div>
  )
}
