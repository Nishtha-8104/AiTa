import { forwardRef, useId } from 'react'
import { AlertCircle } from 'lucide-react'

const control = 'w-full rounded-2xl border bg-tile-2 px-4 text-[15px] text-ink placeholder:text-ink-faint transition-colors focus:border-brand-400/70 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60'

function Shell({ id, label, helper, error, optional, children, className = '' }) {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {label && (
        <label htmlFor={id} className="text-[13px] font-medium text-ink-muted">
          {label}
          {optional && <span className="ml-1.5 font-normal text-ink-faint">optional</span>}
        </label>
      )}
      {children}
      {error ? (
        <p id={`${id}-msg`} className="flex items-center gap-1.5 text-xs text-pop-coral" role="alert">
          <AlertCircle size={13} /> {error}
        </p>
      ) : helper ? (
        <p id={`${id}-msg`} className="text-xs text-ink-subtle">{helper}</p>
      ) : null}
    </div>
  )
}

export const TextField = forwardRef(function TextField({ label, helper, error, optional, className, inputClassName = '', icon: Icon, trailing, ...rest }, ref) {
  const id = useId()
  return (
    <Shell id={id} label={label} helper={helper} error={error} optional={optional} className={className}>
      <div className="relative">
        {Icon && <Icon size={17} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-subtle" />}
        <input
          ref={ref}
          id={id}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error || helper ? `${id}-msg` : undefined}
          className={`${control} h-12 ${Icon ? 'pl-11' : ''} ${trailing ? 'pr-12' : ''} ${error ? 'border-pop-coral/60' : 'border-line-strong'} ${inputClassName}`}
          {...rest}
        />
        {trailing && <div className="absolute right-2 top-1/2 -translate-y-1/2">{trailing}</div>}
      </div>
    </Shell>
  )
})

export function TextArea({ label, helper, error, optional, className, rows = 4, mono = false, ...rest }) {
  const id = useId()
  return (
    <Shell id={id} label={label} helper={helper} error={error} optional={optional} className={className}>
      <textarea
        id={id}
        rows={rows}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={error || helper ? `${id}-msg` : undefined}
        className={`${control} resize-y py-3 leading-relaxed ${mono ? 'font-mono text-[13px]' : ''} ${error ? 'border-pop-coral/60' : 'border-line-strong'}`}
        {...rest}
      />
    </Shell>
  )
}

export function SelectField({ label, helper, error, optional, className, children, ...rest }) {
  const id = useId()
  return (
    <Shell id={id} label={label} helper={helper} error={error} optional={optional} className={className}>
      <select
        id={id}
        aria-invalid={Boolean(error) || undefined}
        className={`${control} h-12 appearance-none bg-[url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%238e8e99' stroke-width='2' viewBox='0 0 24 24'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")] bg-[position:right_14px_center] bg-no-repeat pr-10 ${error ? 'border-pop-coral/60' : 'border-line-strong'}`}
        {...rest}
      >
        {children}
      </select>
    </Shell>
  )
}

export function ChoiceChips({ options, value, onChange, label, multiple = false, columns = '' }) {
  const isOn = v => (multiple ? (value || []).includes(v) : value === v)
  const toggle = v => {
    if (!multiple) return onChange(v)
    const list = value || []
    onChange(list.includes(v) ? list.filter(x => x !== v) : [...list, v])
  }
  return (
    <div role="group" aria-label={label} className={`flex flex-wrap gap-2 ${columns}`}>
      {options.map(o => (
        <button
          key={o.value}
          type="button"
          aria-pressed={isOn(o.value)}
          onClick={() => toggle(o.value)}
          className={`min-h-[40px] rounded-full border px-4 text-sm font-medium transition-colors ${
            isOn(o.value) ? 'border-ink bg-ink text-canvas' : 'border-line-strong text-ink-muted hover:border-ink-faint hover:text-ink'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
