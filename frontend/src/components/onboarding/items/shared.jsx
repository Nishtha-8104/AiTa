import { Send } from 'lucide-react'
import { LANGUAGES } from '../options'
import Button from '../../ui/Button'

export const CODE_CAP = 4000

export function CodeFrame({ language, children }) {
  const label = LANGUAGES.find(l => l.value === language)?.label || language
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-code-bg">
      <div className="flex items-center gap-2 border-b border-line bg-tile-2 px-4 py-2">
        <span className="h-2 w-2 rounded-full bg-pop-aqua" aria-hidden="true" />
        <span className="font-mono text-[11px] font-semibold tracking-wide text-ink-muted">{label}</span>
      </div>
      {children}
    </div>
  )
}

export function CodeBlock({ language, children }) {
  return (
    <CodeFrame language={language}>
      <pre className="overflow-x-auto whitespace-pre p-4 font-mono text-[13.5px] leading-relaxed text-ink">{children}</pre>
    </CodeFrame>
  )
}

export function ItemActions({ canSubmit, disabled, onSubmit, onSkip, label = 'Submit', busyLabel = 'Checking…' }) {
  return (
    <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
      <Button variant="ghost" onClick={onSkip} disabled={disabled}>I don't know</Button>
      <Button size="lg" icon={Send} onClick={onSubmit} disabled={!canSubmit} busy={disabled}>
        {disabled ? busyLabel : label}
      </Button>
    </div>
  )
}
