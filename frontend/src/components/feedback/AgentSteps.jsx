import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const asText = step => (typeof step === 'string' ? step
  : Array.isArray(step) ? step.map(e => (typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e))).join(', ')
  : step && typeof step === 'object' ? (step.msg || step.message || JSON.stringify(step))
  : String(step ?? ''))

export default function AgentSteps({ steps = [] }) {
  const [open, setOpen] = useState(false)
  if (!steps.length) return null

  return (
    <div className="rounded-[20px] border border-line bg-tile-2">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="flex h-11 w-full items-center justify-between gap-3 px-4 text-left text-sm text-ink-subtle hover:text-ink"
      >
        How this report was made ({steps.length} steps)
        <ChevronDown size={15} className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ol className="space-y-1.5 border-t border-line px-4 py-3">
          {steps.map((step, i) => (
            <li key={i} className="font-mono text-xs leading-relaxed text-ink-subtle">{asText(step).replace(/^[^\w(]+/u, '')}</li>
          ))}
        </ol>
      )}
    </div>
  )
}
