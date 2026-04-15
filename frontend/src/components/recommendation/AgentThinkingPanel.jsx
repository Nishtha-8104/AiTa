import { useEffect, useRef } from 'react'
import { Brain, Cpu, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

function ThoughtStep({ text, index, isLast, generating }) {
  // Safely coerce any value to a display string
  let str
  if (typeof text === 'string') {
    str = text
  } else if (Array.isArray(text)) {
    str = text.map(e => (typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e))).join(', ')
  } else if (text && typeof text === 'object') {
    str = text.msg || text.message || JSON.stringify(text)
  } else {
    str = String(text ?? '')
  }
  const isError   = str.startsWith('❌')
  const isDone    = str.startsWith('✅') || str.includes('Done!')
  const isThinking= isLast && generating

  return (
    <div
      className="flex items-start gap-3 animate-slide-up"
      style={{ animationDelay: `${index * 40}ms`, animationFillMode: 'both' }}
    >
      {/* Icon */}
      <div className="mt-0.5 shrink-0">
        {isThinking ? (
          <Loader2 size={14} className="text-brand-400 animate-spin" />
        ) : isError ? (
          <XCircle size={14} className="text-red-400" />
        ) : isDone ? (
          <CheckCircle2 size={14} className="text-green-400" />
        ) : (
          <div className="w-3.5 h-3.5 rounded-full border border-white/20 bg-surface-600" />
        )}
      </div>
      {/* Text */}
      <p className={`text-xs font-mono leading-relaxed ${
        isError ? 'text-red-300' : isDone ? 'text-green-300' : 'text-white/60'
      }`}>
        {str}
      </p>
    </div>
  )
}

export default function AgentThinkingPanel({ steps = [], generating }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps.length])

  if (steps.length === 0 && !generating) return null

  return (
    <div className="glass-card border-brand-500/20 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.06]">
        <div className="w-8 h-8 rounded-lg bg-brand-600/20 flex items-center justify-center">
          {generating
            ? <Cpu size={16} className="text-brand-400 animate-pulse" />
            : <Brain size={16} className="text-brand-400" />}
        </div>
        <div>
          <p className="font-display font-600 text-sm text-white">
            {generating ? 'Agent is thinking...' : 'Agent Thought Log'}
          </p>
          <p className="text-white/30 text-xs font-mono">{steps.length} steps completed</p>
        </div>
        {generating && (
          <div className="ml-auto flex gap-1">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse"
                style={{ animationDelay: `${i * 200}ms` }} />
            ))}
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="p-5 space-y-3 max-h-72 overflow-y-auto">
        {steps.filter(s => s != null).map((step, i) => (
          <ThoughtStep
            key={i}
            text={step}
            index={i}
            isLast={i === steps.length - 1}
            generating={generating}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}