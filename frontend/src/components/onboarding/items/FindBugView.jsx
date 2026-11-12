import { useState } from 'react'
import RichText from '../../learning/RichText'
import CodeArea from '../../learning/CodeArea'
import { CODE_CAP, CodeFrame, ItemActions } from './shared'

export default function FindBugView({ item, onSubmit, disabled }) {
  const code = item.body.code
  const lines = code.replace(/\n$/, '').split('\n')
  const [line, setLine] = useState(null)
  const [fix, setFix] = useState(code)

  const submit = () => onSubmit({ line, fix_code: fix === code ? '' : fix })

  return (
    <div>
      {item.body.statement && (
        <RichText text={item.body.statement} className="mb-5 text-[15px] text-ink" />
      )}
      <p className="mb-2.5 text-[13px] font-medium text-ink-muted">Click the line with the bug</p>
      <CodeFrame language={item.language}>
        <div className="overflow-x-auto py-2">
          {lines.map((text, i) => {
            const n = i + 1
            const selected = line === n
            return (
              <button key={n} type="button" aria-pressed={selected}
                aria-label={`Line ${n}: ${text.trim() || 'blank'}`}
                onClick={() => setLine(n)} disabled={disabled}
                className={`flex w-full min-w-max border-l-2 text-left font-mono text-[13.5px] leading-7 transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-brand-400/70 ${
                  selected ? 'border-pop-sun bg-pop-sun/10 text-ink' : 'border-transparent text-ink-muted hover:bg-white/[0.04] hover:text-ink'
                }`}>
                <span className={`w-11 shrink-0 select-none pr-3 text-right ${selected ? 'text-pop-sun' : 'text-ink-faint'}`}>{n}</span>
                <span className="whitespace-pre pr-4">{text || ' '}</span>
              </button>
            )
          })}
        </div>
      </CodeFrame>

      {line && (
        <div className="mt-6 motion-safe:animate-rise">
          <p className="text-[13px] font-medium text-ink-muted">
            Fix it <span className="font-normal text-ink-faint">optional</span>
          </p>
          <p className="mb-2.5 mt-1 text-xs text-ink-subtle">You picked line {line}. Edit the code below if you can. The line alone earns half the credit.</p>
          <CodeArea value={fix} onChange={setFix} disabled={disabled} maxLength={CODE_CAP}
            minHeight="220px" label="Fixed code" language={item.language} />
        </div>
      )}

      <ItemActions canSubmit={line !== null} disabled={disabled}
        onSubmit={submit} onSkip={() => onSubmit({})} />
    </div>
  )
}
