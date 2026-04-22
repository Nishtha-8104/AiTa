import { useState } from 'react'
import {
  Sparkles, Copy, CheckCheck, Lightbulb, Target,
  BookOpen, ThumbsUp, AlertTriangle, ExternalLink,
  ChevronDown, ChevronUp, Clock, Box
} from 'lucide-react'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy}
      className="flex items-center gap-1.5 px-2.5 py-1.5 text-white/30 hover:text-white/70 hover:bg-surface-600 rounded-lg transition-all text-xs">
      {copied ? <CheckCheck size={13} className="text-green-400" /> : <Copy size={13} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function Section({ icon: Icon, title, color = 'text-white/50', children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="glass-card overflow-hidden animate-fade-in">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 border-b border-white/[0.06] hover:bg-surface-700/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon size={15} className={color} />
          <span className="font-display font-600 text-sm text-white">{title}</span>
        </div>
        {open ? <ChevronUp size={14} className="text-white/30" /> : <ChevronDown size={14} className="text-white/30" />}
      </button>
      {open && <div className="px-5 py-4">{children}</div>}
    </div>
  )
}

// Simple inline-markdown renderer for feedback text
function MarkdownText({ text }) {
  if (!text) return null
  // Split on code blocks first
  const parts = text.split(/(```[\s\S]*?```)/g)
  return (
    <div className="space-y-2 text-sm text-white/70 leading-relaxed font-body">
      {parts.map((part, i) => {
        if (part.startsWith('```')) {
          const lines = part.replace(/^```\w*\n?/, '').replace(/```$/, '')
          return (
            <pre key={i} className="bg-[#0d1117] border border-white/[0.06] rounded-xl px-4 py-3 overflow-x-auto text-xs text-green-300/80 font-mono">
              {lines}
            </pre>
          )
        }
        // Handle ## headings and **bold**
        return part.split('\n').map((line, j) => {
          if (line.startsWith('## ')) return <p key={j} className="font-display font-700 text-white text-base mt-3 mb-1">{line.slice(3)}</p>
          if (line.startsWith('### ')) return <p key={j} className="font-display font-600 text-white text-sm mt-2 mb-1">{line.slice(4)}</p>
          if (line.startsWith('- ') || line.startsWith('* ')) return (
            <p key={j} className="flex items-start gap-2">
              <span className="text-brand-400 shrink-0 mt-1">▸</span>
              <span>{line.slice(2).replace(/\*\*(.+?)\*\*/g, '$1')}</span>
            </p>
          )
          if (!line.trim()) return <div key={j} className="h-1" />
          const withBold = line.split(/(\*\*[^*]+\*\*)/).map((s, k) =>
            s.startsWith('**') ? <strong key={k} className="text-white font-600">{s.slice(2,-2)}</strong> : s
          )
          return <p key={j}>{withBold}</p>
        })
      })}
    </div>
  )
}

function TagList({ items, color = 'text-brand-300 bg-brand-600/10 border-brand-500/20' }) {
  if (!items?.length) return <p className="text-white/20 text-xs italic">None identified.</p>
  return (
    <div className="flex flex-col gap-2">
      {items.map((item, i) => {
        // Safely coerce any value to string — guards against Pydantic error objects
        const text = typeof item === 'string' ? item
          : typeof item === 'object' && item !== null ? (item.msg || item.message || JSON.stringify(item))
          : String(item ?? '')
        return (
          <div key={i} className="flex items-start gap-2">
            <span className="text-brand-400 shrink-0 mt-0.5 text-sm">•</span>
            <p className="text-white/65 text-sm">{text}</p>
          </div>
        )
      })}
    </div>
  )
}

export default function FeedbackPanel({ evaluation }) {
  if (!evaluation) return null

  const {
    summary, detailed_feedback, corrected_code,
    key_improvements, learning_points, best_practices_used,
    anti_patterns, suggested_resources,
    complexity, tokens_used, latency_ms,
  } = evaluation

  return (
    <div className="space-y-4">

      {/* Summary card */}
      {summary && (
        <div className="glass-card px-5 py-4 border-brand-500/15 animate-fade-in">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-600/20 flex items-center justify-center shrink-0">
              <Sparkles size={15} className="text-brand-400" />
            </div>
            <div>
              <p className="font-display font-600 text-sm text-brand-300 mb-1">Agent Verdict</p>
              <p className="text-white/70 text-sm leading-relaxed">{summary}</p>
            </div>
          </div>
        </div>
      )}

      {/* Complexity metrics */}
      {(complexity?.time_complexity || complexity?.space_complexity) && (
        <div className="glass-card px-5 py-4 animate-fade-in">
          <p className="label mb-3">Complexity Analysis</p>
          <div className="flex flex-wrap gap-4">
            {complexity.time_complexity && (
              <div className="flex items-center gap-2">
                <Clock size={14} className="text-yellow-400" />
                <span className="text-white/40 text-xs">Time:</span>
                <code className="text-yellow-300 text-sm font-mono font-600">{complexity.time_complexity}</code>
              </div>
            )}
            {complexity.space_complexity && (
              <div className="flex items-center gap-2">
                <Box size={14} className="text-purple-400" />
                <span className="text-white/40 text-xs">Space:</span>
                <code className="text-purple-300 text-sm font-mono font-600">{complexity.space_complexity}</code>
              </div>
            )}
            {complexity.cyclomatic_complexity && (
              <div className="flex items-center gap-2">
                <span className="text-white/40 text-xs">Cyclomatic:</span>
                <code className="text-brand-300 text-sm font-mono">{complexity.cyclomatic_complexity}</code>
              </div>
            )}
            {complexity.lines_of_code && (
              <div className="flex items-center gap-2">
                <span className="text-white/40 text-xs">LOC:</span>
                <code className="text-white/60 text-sm font-mono">{complexity.lines_of_code}</code>
              </div>
            )}
          </div>
        </div>
      )}

      {/* What the student did well */}
      <Section icon={ThumbsUp} title="What You Did Well" color="text-green-400" defaultOpen={true}>
        <TagList items={best_practices_used} color="text-green-300" />
      </Section>

      {/* Key improvements */}
      <Section icon={Lightbulb} title="Key Improvements" color="text-yellow-400" defaultOpen={true}>
        <TagList items={key_improvements} />
      </Section>

      {/* Anti-patterns */}
      {anti_patterns?.length > 0 && (
        <Section icon={AlertTriangle} title="Anti-Patterns Detected" color="text-orange-400" defaultOpen={false}>
          <TagList items={anti_patterns} color="text-orange-300" />
        </Section>
      )}

      {/* Detailed feedback */}
      {detailed_feedback && (
        <Section icon={Sparkles} title="Detailed Feedback" color="text-brand-400" defaultOpen={false}>
          <MarkdownText text={detailed_feedback} />
        </Section>
      )}

      {/* Corrected code */}
      {corrected_code && (
        <div className="glass-card overflow-hidden animate-fade-in">
          <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-green-400" />
              <span className="font-display font-600 text-sm text-white">Improved Code</span>
              <span className="text-white/20 text-xs">(with agent comments)</span>
            </div>
            <CopyButton text={corrected_code} />
          </div>
          <pre className="overflow-x-auto p-5 text-xs font-mono text-green-300/85 leading-6 bg-[#0d1117] max-h-80">
            <code>{corrected_code}</code>
          </pre>
        </div>
      )}

      {/* Learning points */}
      {learning_points?.length > 0 && (
        <Section icon={Target} title="Concepts to Revisit" color="text-purple-400" defaultOpen={true}>
          <TagList items={learning_points} color="text-purple-300" />
        </Section>
      )}

      {/* Suggested resources */}
      {suggested_resources?.length > 0 && (
        <Section icon={BookOpen} title="Suggested Topics to Study" color="text-pink-400" defaultOpen={true}>
          <div className="flex flex-col gap-2">
            {suggested_resources.map((r, i) => (
              <div key={i} className="flex items-center gap-2">
                <ExternalLink size={12} className="text-pink-400 shrink-0" />
                <p className="text-white/65 text-sm">{r}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Footer metadata */}
      <div className="flex items-center gap-4 px-1 text-white/20 text-xs font-mono">
        <span>Groq · llama-3.3-70b</span>
        {tokens_used > 0 && <span>{tokens_used} tokens</span>}
        {latency_ms  > 0 && <span>{(latency_ms/1000).toFixed(1)}s</span>}
      </div>
    </div>
  )
}