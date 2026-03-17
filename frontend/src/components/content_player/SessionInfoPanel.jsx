import {
  Brain, Target, AlertTriangle, CheckCircle2,
  BookOpen, Zap, BarChart2, X
} from 'lucide-react'

const MODE_DESCRIPTIONS = {
  qa:          { label: 'Q&A Mode',          desc: 'Concept explanation with Socratic follow-ups',    color: 'text-brand-400' },
  code_help:   { label: 'Code Help Mode',    desc: 'Debug & fix code with guided hints',              color: 'text-green-400' },
  brainstorm:  { label: 'Brainstorm Mode',   desc: 'Explore approaches and design solutions',         color: 'text-purple-400' },
  quiz:        { label: 'Quiz Mode',         desc: 'Adaptive questions to test understanding',        color: 'text-yellow-400' },
  walkthrough: { label: 'Walkthrough Mode',  desc: 'Step-by-step guided concept learning',            color: 'text-pink-400' },
}

function Tag({ text, color = 'text-white/50 bg-surface-600/60' }) {
  return (
    <span className={`px-2.5 py-1 rounded-lg text-xs font-mono ${color}`}>{text}</span>
  )
}

export default function SessionInfoPanel({ session, onClose }) {
  if (!session) return null

  const modeInfo = MODE_DESCRIPTIONS[session.mode] || MODE_DESCRIPTIONS.qa
  const completionPct = session.total_messages > 0
    ? Math.min(Math.round((session.concepts_covered?.length || 0) * 10), 100)
    : 0

  return (
    <div className="flex flex-col h-full border-l border-white/[0.06] bg-surface-900/30 w-72">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <BarChart2 size={15} className="text-white/40" />
          <span className="font-display font-600 text-sm text-white/70">Session Info</span>
        </div>
        <button onClick={onClose}
          className="p-1.5 text-white/20 hover:text-white/60 rounded-lg hover:bg-surface-700 transition-colors">
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">

        {/* Mode */}
        <div>
          <p className="label">Mode</p>
          <p className={`font-display font-600 text-sm ${modeInfo.color}`}>{modeInfo.label}</p>
          <p className="text-white/30 text-xs mt-0.5">{modeInfo.desc}</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: 'Messages', value: session.total_messages || 0, icon: Brain },
            { label: 'Tokens',   value: session.total_tokens_used || 0, icon: Zap },
          ].map(s => (
            <div key={s.label} className="bg-surface-700/40 rounded-xl p-3 text-center">
              <p className="font-display font-700 text-lg text-white">{s.value}</p>
              <p className="text-white/30 text-xs">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        {session.total_messages > 0 && (
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <p className="label mb-0">Concepts Covered</p>
              <span className="text-brand-400 text-xs font-mono">{session.concepts_covered?.length || 0}</span>
            </div>
            <div className="h-1.5 bg-surface-600 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-700"
                style={{ width: `${completionPct}%` }} />
            </div>
          </div>
        )}

        {/* Concepts */}
        {session.concepts_covered?.length > 0 && (
          <div>
            <p className="label">Topics Covered</p>
            <div className="flex flex-wrap gap-1.5">
              {session.concepts_covered.map(c => (
                <Tag key={c} text={c} color="text-brand-300 bg-brand-600/10 border border-brand-500/20" />
              ))}
            </div>
          </div>
        )}

        {/* Mastery signals */}
        {session.mastery_signals?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={13} className="text-green-400" />
              <p className="label mb-0">Understood Well</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {session.mastery_signals.map(s => (
                <Tag key={s} text={s} color="text-green-300 bg-green-600/10 border border-green-500/20" />
              ))}
            </div>
          </div>
        )}

        {/* Weak signals */}
        {session.weak_signals?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Target size={13} className="text-yellow-400" />
              <p className="label mb-0">Needs Practice</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {session.weak_signals.map(s => (
                <Tag key={s} text={s} color="text-yellow-300 bg-yellow-600/10 border border-yellow-500/20" />
              ))}
            </div>
          </div>
        )}

        {/* Confusion flag */}
        {session.confusion_detected && (
          <div className="flex items-start gap-2 bg-yellow-500/5 border border-yellow-500/15 rounded-xl p-3">
            <AlertTriangle size={14} className="text-yellow-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-yellow-300 text-xs font-display font-600">Confusion detected</p>
              <p className="text-yellow-300/50 text-xs mt-0.5">The agent noticed you may need more explanation on some topics in this session.</p>
            </div>
          </div>
        )}

        {/* Language */}
        {session.language && (
          <div>
            <p className="label">Language Context</p>
            <Tag text={session.language} color="text-white/60 bg-surface-600/60" />
          </div>
        )}

        {/* Model */}
        <div>
          <p className="label">AI Model</p>
          <p className="text-white/30 text-xs font-mono">{session.agent_model || 'llama-3.3-70b-versatile'}</p>
          <p className="text-white/15 text-xs mt-0.5">via Groq</p>
        </div>
      </div>
    </div>
  )
}