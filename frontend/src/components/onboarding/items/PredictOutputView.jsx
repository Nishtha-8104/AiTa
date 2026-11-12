import { useState } from 'react'
import { TextArea } from '../../ui/Field'
import { CODE_CAP, CodeBlock, ItemActions } from './shared'

export default function PredictOutputView({ item, onSubmit, disabled }) {
  const [text, setText] = useState('')

  return (
    <div>
      <CodeBlock language={item.language}>{item.body.code}</CodeBlock>
      <TextArea
        className="mt-5"
        label="What does this print?"
        helper="Type the exact output, one line per line."
        value={text}
        onChange={e => setText(e.target.value)}
        rows={4}
        maxLength={CODE_CAP}
        spellCheck={false}
        disabled={disabled}
        placeholder="Type the exact output"
        mono
      />
      <ItemActions canSubmit={!!text.trim()} disabled={disabled}
        onSubmit={() => onSubmit({ text })} onSkip={() => onSubmit({ text: '' })} />
    </div>
  )
}
