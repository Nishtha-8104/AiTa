import { useState } from 'react'
import {
  CheckCircle2, AlertTriangle, Lightbulb, Target, ChevronDown,
  ChevronUp, BookOpen, Star, Brain, ArrowRight, Clock, Cpu
} from 'lucide-react'
import ConceptMap from './ConceptMap'
import AgentSteps from './AgentSteps'

const TYPE_CONFIG = {
  code_review:    { label: 'Code Review',      color: 'text-orange-400 bg-orange-600/10 border-orange-500/20' },
  learning_recap: { label: 'Learning Recap',   color: 'text-teal-400   bg-teal-600/10   border-teal-500/20'   },
  combined:       { label: 'Combined Report',  color: 'text-pink-400   bg-pink-600/10   border-pink-500/20'   },
}
const TONE_CONFIG = {
  encouraging:  { label: '🌱 Encouraging',  color: 'text-green-400'  },
  constructive: { label: '🔧 Constructive', color: 'text-yellow-400' },
  challenging:  { label: '⚡ Challenging',  color: 'text-purple-400' },
}

function Section({ icon: Icon, title, color, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-surface-700/20 transition-colors border-b border-white/[0.05]"
      >
        <div className="flex items-center gap-2.5">
          <Icon size={15} className={color} />
          <span className="font-display font-700 text-sm text-white">{title}</span>
        </div>
        {open ? <ChevronUp size={13} className="text-white/25" /> : <ChevronDown size={13} className="text-white/25" />}
      </button>
      {open && <div className="px-5 py-4">{children}</div>}
    </div>
  )
}

function TagList({ items = [], color = 'text-white/60', bg = 'bg-surface-600/60', border = 'border-white/[0.06]' }) {
  if (!items.length) return <p className="text-white/25 text-xs italic">None detected</p>
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2.5">
          <span className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${bg.replace('bg-', 'bg-').replace('/60','')}`} />
          <span className={`text-sm leading-relaxed ${color}`}>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function FeedbackCard({ report }) {
  if (!report) return null

  const typeConfig = TYPE_CONFIG[report.feedback_type] || TYPE_CONFIG.code_review
  const toneConfig = TONE_CONFIG[report.tone]          || TONE_CONFIG.encouraging

  return (
    <div className="space-y-4">

      {/* ── Header ── */}
      <div className="glass-card p-5 border-pink-500/15">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className={`px-2.5 py-1 rounded-lg border text-xs font-display font-600 ${typeConfig.color}`}>
            {typeConfig.label}
          </span>
          <span className={`text-xs font-mono ${toneConfig.color}`}>{toneConfig.label}</span>
          <span className="flex items-center gap-1 text-white/25 text-xs font-mono ml-auto">
            <Clock size={11} /> {timeAgo(report.created_at)}
          </span>
        </div>

        {/* Headline */}
        <h2 className="font-display font-700 text-white text-lg leading-snug mb-3">
          {report.headline || 'Feedback Report'}
        </h2>

        {/* Summary */}
        <p className="text-white/65 text-sm leading-relaxed mb-4">
          {report.summary}
        </p>

        {/* Motivational */}
        {report.motivational && (
          <div className="flex items-start gap-3 bg-pink-600/5 border border-pink-500/15 rounded-xl px-4 py-3">
            <Star size={15} className="text-pink-400 shrink-0 mt-0.5" fill="currentColor" />
            <p className="text-pink-200/70 text-sm italic leading-relaxed">{report.motivational}</p>
          </div>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-4 mt-4 pt-3 border-t border-white/[0.05] text-xs font-mono text-white/25">
          {report.tokens_used > 0 && <span><Cpu size={10} className="inline mr-1" />{report.tokens_used} tokens</span>}
          {report.latency_ms  > 0 && <span>⏱ {(report.latency_ms/1000).toFixed(1)}s</span>}
          {report.evaluation_id  && <span className="text-orange-400/60">Code Eval #{report.evaluation_id}</span>}
          {report.cp_session_id  && <span className="text-teal-400/60">Session #{report.cp_session_id}</span>}
        </div>
      </div>

      {/* ── Strengths ── */}
      <Section icon={CheckCircle2} title="What You Did Well" color="text-green-400">
        <TagList
          items={report.strengths}
          color="text-green-300/80"
          bg="bg-green-500"
        />
      </Section>

      {/* ── Errors ── */}
      {report.errors?.length > 0 && (
        <Section icon={AlertTriangle} title="Errors & Issues Found" color="text-red-400">
          <TagList
            items={report.errors}
            color="text-red-300/80"
            bg="bg-red-500"
          />
        </Section>
      )}

      {/* ── Misconceptions ── */}
      {report.misconceptions?.length > 0 && (
        <Section icon={Brain} title="Conceptual Misunderstandings" color="text-yellow-400">
          <TagList
            items={report.misconceptions}
            color="text-yellow-200/75"
            bg="bg-yellow-500"
          />
        </Section>
      )}

      {/* ── Action Items ── */}
      <Section icon={Target} title="Action Items — Do These Next" color="text-pink-400">
        {report.action_items?.length > 0 ? (
          <ol className="space-y-2.5">
            {report.action_items.map((item, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-md bg-pink-600/20 border border-pink-500/25 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-pink-300 text-xs font-mono font-700">{i + 1}</span>
                </span>
                <span className="text-white/70 text-sm leading-relaxed">{item}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-white/25 text-xs italic">No action items</p>
        )}
      </Section>

      {/* ── Concept Map ── */}
      {Object.keys(report.concept_map || {}).length > 0 && (
        <Section icon={BookOpen} title="Concept Understanding Map" color="text-brand-400">
          <p className="text-white/30 text-xs mb-4">
            Agent-estimated understanding level for each concept covered (0% = gap, 100% = mastered).
          </p>
          <ConceptMap conceptMap={report.concept_map} />
        </Section>
      )}

      {/* ── Next Topics ── */}
      {report.next_topics?.length > 0 && (
        <Section icon={Lightbulb} title="Study These Next" color="text-purple-400" defaultOpen={false}>
          <div className="flex flex-wrap gap-2">
            {report.next_topics.map((t, i) => (
              <span key={i}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600/10 border border-purple-500/20 rounded-xl text-purple-300 text-xs font-mono">
                <ArrowRight size={11} /> {t}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* ── Agent Steps ── */}
      {report.agent_steps?.length > 0 && (
        <AgentSteps steps={report.agent_steps} />
      )}
    </div>
  )
}