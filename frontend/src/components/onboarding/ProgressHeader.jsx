import Stepper from '../ui/Stepper'
import { STEPS } from './options'

export default function ProgressHeader({ step, question, remaining }) {
  const current = STEPS.findIndex(s => s.key === step)
  const total = question ? question + (remaining || 0) : 0

  return (
    <div className="mb-6">
      <Stepper steps={STEPS} current={current} label="Onboarding steps" />

      {question ? (
        <div className="mt-6 flex items-center gap-4">
          <p className="shrink-0 text-sm text-ink-muted">
            <span className="font-mono text-ink">Question {question}</span>
            <span className="text-ink-subtle"> · {remaining ? `about ${remaining} left` : 'Last question'}</span>
          </p>
          <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/10" aria-hidden="true">
            <div className="h-full rounded-full bg-pop-mint transition-[width] duration-500" style={{ width: `${Math.min(100, (question / total) * 100)}%` }} />
          </div>
        </div>
      ) : null}
    </div>
  )
}
