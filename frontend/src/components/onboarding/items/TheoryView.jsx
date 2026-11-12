import { useState } from 'react'
import RichText from '../../learning/RichText'
import { TextArea } from '../../ui/Field'
import { ItemActions } from './shared'

const THEORY_CAP = 2000

export default function TheoryView({ item, onSubmit, disabled }) {
  const [text, setText] = useState('')

  return (
    <div>
      <RichText text={item.body.question} className="mb-5 text-[15px] text-ink" />
      <TextArea
        label="Your answer, in 1 to 3 sentences"
        value={text}
        onChange={e => setText(e.target.value)}
        rows={5}
        maxLength={THEORY_CAP}
        disabled={disabled}
      />
      <p className={`mt-1.5 text-right font-mono text-xs ${text.length >= THEORY_CAP ? 'text-pop-sun' : 'text-ink-faint'}`} aria-live="polite">
        {text.length} / {THEORY_CAP}
      </p>
      <ItemActions canSubmit={!!text.trim()} disabled={disabled} label="Save answer" busyLabel="Saving…"
        onSubmit={() => onSubmit({ text })} onSkip={() => onSubmit({ text: '' })} />
    </div>
  )
}
