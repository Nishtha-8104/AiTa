import { useState } from 'react'
import toast from 'react-hot-toast'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { onboardingAPI, getErrorMessage } from '../../utils/api'
import Button from '../ui/Button'

export function useSaveStep(step, onSaved, onConflict) {
  const [saving, setSaving] = useState(false)
  const save = async (data) => {
    setSaving(true)
    try {
      const { data: state } = await onboardingAPI.saveStep(step, data)
      onSaved(state)
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not save this step. Please try again.'))
      if (err?.response?.status === 409) onConflict?.()
    } finally {
      setSaving(false)
    }
  }
  return { saving, save }
}

export function StepTitle({ title, subtitle, eyebrow }) {
  return (
    <div className="mb-7">
      {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
      <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-[28px]">{title}</h2>
      {subtitle && <p className="mt-2 max-w-[60ch] text-[15px] leading-relaxed text-ink-subtle">{subtitle}</p>}
    </div>
  )
}

const COLS = {
  2: 'grid-cols-2',
  3: 'grid-cols-2 sm:grid-cols-3',
  4: 'grid-cols-2 sm:grid-cols-4',
  5: 'grid-cols-2 sm:grid-cols-5',
  6: 'grid-cols-3 sm:grid-cols-6',
}

export function ChoiceGroup({ label, options, value, onChange, columns = 2, clearable = false }) {
  return (
    <div role="radiogroup" aria-label={label}>
      <span className="mb-2.5 block text-[13px] font-medium text-ink-muted">{label}</span>
      <div className={`grid gap-2 ${COLS[columns] || COLS[2]}`}>
        {options.map(o => {
          const selected = value === o.value
          return (
            <button
              key={o.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(selected && clearable ? null : o.value)}
              className={`min-h-[44px] rounded-2xl border px-3 py-2 text-sm font-medium transition-colors duration-200 ${
                selected ? 'border-ink bg-ink text-canvas' : 'border-line-strong bg-tile-2 text-ink-muted hover:border-ink-faint hover:text-ink'
              }`}
            >
              {o.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function StepNav({ onBack, onNext, canNext = true, saving, nextLabel = 'Next' }) {
  return (
    <div className="mt-10 flex items-center justify-between gap-3 border-t border-line pt-6">
      {onBack ? (
        <Button variant="ghost" icon={ChevronLeft} onClick={onBack} disabled={saving}>Back</Button>
      ) : <span />}
      <Button size="lg" iconRight={ChevronRight} onClick={onNext} disabled={!canNext} busy={saving}>
        {saving ? 'Saving…' : nextLabel}
      </Button>
    </div>
  )
}
