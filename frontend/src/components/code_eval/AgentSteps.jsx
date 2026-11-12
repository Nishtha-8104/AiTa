import { useState } from 'react'
import { ChevronDown, CircleCheck, CircleX } from 'lucide-react'
import BusyNote from '../ui/BusyNote'

// The backend runs the whole check in one call, so there is no live progress to
// stream. These approximate the real stages by elapsed time.
const STAGES = [
  { after: 0, text: 'Reading the problem…' },
  { after: 3, text: 'Checking your code…' },
  { after: 8, text: 'Getting test cases ready…' },
  { after: 18, text: 'Running your code against the tests…' },
  { after: 30, text: 'Writing your feedback…' },
  { after: 60, text: 'Taking longer than usual. Please keep this page open…' },
]

export default function AgentSteps({ steps = [], evaluating }) {
  const [open, setOpen] = useState(false)
  if (evaluating) return <BusyNote active steps={STAGES} note="This usually takes 20 to 60 seconds." />
  if (steps.length === 0) return null

  const lines = steps.map(step =>
    typeof step === 'string' ? step
      : step && typeof step === 'object' ? (step.msg || step.message || JSON.stringify(step))
      : String(step ?? ''))

  return (
    <div className="rounded-[20px] border border-line bg-tile-2">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="flex h-11 w-full items-center justify-between gap-3 px-4 text-left text-sm text-ink-muted hover:text-ink"
      >
        What we checked ({lines.length} steps)
        <ChevronDown size={15} className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ul className="max-h-56 space-y-2 overflow-y-auto border-t border-line px-4 py-3">
          {lines.map((line, i) => {
            const failed = /fail|unavailable|cannot/i.test(line)
            return (
              <li key={i} className="flex items-start gap-2 text-xs leading-relaxed">
                {failed
                  ? <CircleX size={14} className="mt-px shrink-0 text-pop-coral" />
                  : <CircleCheck size={14} className="mt-px shrink-0 text-pop-mint" />}
                <span className={failed ? 'text-pop-coral' : 'text-ink-subtle'}>{line.replace(/^[^\w(]+/u, '')}</span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
