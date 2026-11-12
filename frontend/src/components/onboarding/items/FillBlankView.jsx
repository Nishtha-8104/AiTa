import { useState } from 'react'
import { TextField } from '../../ui/Field'
import { CodeBlock, ItemActions } from './shared'

const BLANK_CAP = 300

export default function FillBlankView({ item, onSubmit, disabled }) {
  const [text, setText] = useState('')
  const { code_with_blank: code, blank_marker: marker = '____' } = item.body
  const parts = code.split(marker)
  const canSubmit = !!text.trim() && !disabled

  return (
    <div>
      <CodeBlock language={item.language}>
        {parts.map((part, i) => (
          <span key={i}>
            {part}
            {i < parts.length - 1 && (
              <mark className="rounded-md bg-pop-sun/20 px-1 text-pop-sun ring-1 ring-pop-sun/50">{text.trim() ? text : marker}</mark>
            )}
          </span>
        ))}
      </CodeBlock>
      <TextField
        className="mt-5"
        label="What goes in the blank?"
        helper="Your answer is shown in the code above as you type."
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && canSubmit) onSubmit({ text }) }}
        maxLength={BLANK_CAP}
        spellCheck={false}
        autoComplete="off"
        disabled={disabled}
        placeholder="The missing code"
        inputClassName="font-mono text-sm"
      />
      <ItemActions canSubmit={!!text.trim()} disabled={disabled}
        onSubmit={() => onSubmit({ text })} onSkip={() => onSubmit({ text: '' })} />
    </div>
  )
}
