import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

export function CopyButton({ text, label = 'Copy' }) {
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text ?? '')
      setDone(true)
      setTimeout(() => setDone(false), 1500)
    } catch { /* clipboard blocked */ }
  }
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={`${label}: copy`}
      className="flex h-7 items-center gap-1 rounded-full px-2 text-[11px] text-ink-subtle transition-colors hover:bg-white/[0.06] hover:text-ink"
    >
      {done ? <Check size={12} className="text-pop-mint" /> : <Copy size={12} />}
      {done ? 'Copied' : 'Copy'}
    </button>
  )
}

const TONE = {
  aqua: 'text-pop-aqua',
  mint: 'text-pop-mint',
  coral: 'text-pop-coral',
  neutral: 'text-ink-muted',
}

export function OutputBlock({ label, value, tone = 'neutral', empty = '(nothing)' }) {
  const shown = value === '' || value == null ? empty : value
  return (
    <div className="min-w-0">
      <div className="flex items-center justify-between gap-2">
        <span className="eyebrow text-[10px]">{label}</span>
        {value ? <CopyButton text={value} label={label} /> : <span className="h-7" />}
      </div>
      <pre className={`mt-1 max-h-56 overflow-auto rounded-xl border border-line bg-canvas px-3 py-2.5 font-mono text-[13px] leading-relaxed ${value ? TONE[tone] : 'italic text-ink-faint'}`}>
        {shown}
      </pre>
    </div>
  )
}

export default function CaseBlock({ input, expected, actual, title = 'Failing case' }) {
  return (
    <div className="mt-4">
      {title && <p className="mb-2 text-sm font-medium text-ink">{title}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <OutputBlock label="Input" value={input} tone="aqua" />
        <OutputBlock label="Expected" value={expected} tone="mint" />
        <OutputBlock label="Your output" value={actual} tone="coral" />
      </div>
    </div>
  )
}
