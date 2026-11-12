import { useState } from 'react'
import RichText from '../../learning/RichText'
import CodeArea from '../../learning/CodeArea'
import { CODE_CAP, ItemActions } from './shared'

export default function WriteCodeView({ item, onSubmit, disabled }) {
  const [code, setCode] = useState(item.body.starter_code || '')

  return (
    <div>
      <RichText text={item.body.statement} className="mb-5 text-[15px] text-ink" />
      <CodeArea value={code} onChange={setCode} disabled={disabled} maxLength={CODE_CAP}
        label="Your code" language={item.language} minHeight="300px" />
      <ItemActions canSubmit={!!code.trim()} disabled={disabled} busyLabel="Running your code…"
        onSubmit={() => onSubmit({ code })} onSkip={() => onSubmit({ code: '' })} />
    </div>
  )
}
