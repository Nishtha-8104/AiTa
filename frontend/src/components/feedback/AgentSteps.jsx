import { useState } from 'react'
import { ChevronDown, ChevronUp, Cpu } from 'lucide-react'

export default function AgentSteps({ steps = [], generating = false }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="glass-card overflow-hidden border-pink-500/15">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-700/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Cpu size={14} className={`${generating ? 'text-pink-400 animate-pulse' : 'text-white/30'}`} />
          <span className="text-xs font-mono text-white/40">
            {generating ? 'Agent running…' : `Agent log · ${steps.length} steps`}
          </span>
        </div>
        {open ? <ChevronUp size={13} className="text-white/25" /> : <ChevronDown size={13} className="text-white/25" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-1.5 border-t border-white/[0.05] pt-3">
        {steps.map((step, i) => {
            const str = typeof step === 'string' ? step
              : Array.isArray(step) ? step.map(e => typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e)).join(', ')
              : step && typeof step === 'object' ? (step.msg || step.message || JSON.stringify(step))
              : String(step ?? '')
            return (
              <p key={i} className="text-white/45 text-xs font-mono leading-relaxed">{str}</p>
            )
          })}
          {generating && (
            <div className="flex items-center gap-2 text-pink-400 text-xs font-mono">
              <div className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-pulse" />
              Processing…
            </div>
          )}
        </div>
      )}
    </div>
  )
}