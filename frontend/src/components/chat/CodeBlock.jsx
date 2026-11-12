import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import toast from 'react-hot-toast'

const LANGUAGE_LABELS = {
  c: 'C', h: 'C',
  cpp: 'C++', 'c++': 'C++', cc: 'C++', cxx: 'C++', hpp: 'C++',
  python: 'Python', py: 'Python', python3: 'Python',
  sh: 'Shell', bash: 'Shell', shell: 'Shell', console: 'Shell',
  text: 'Text', txt: 'Text', plaintext: 'Text',
  json: 'JSON', java: 'Java', js: 'JavaScript', javascript: 'JavaScript',
}

const LANGUAGE_DOTS = {
  C: 'bg-pop-aqua',
  'C++': 'bg-pop-pink',
  Python: 'bg-pop-sun',
}

function languageLabel(language) {
  const key = (language || '').toLowerCase()
  return LANGUAGE_LABELS[key] || (key ? key.toUpperCase() : 'Code')
}

export default function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false)
  const label = languageLabel(language)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      toast.error('Could not copy the code')
    }
  }

  return (
    <div className="my-3 overflow-hidden rounded-2xl border border-line bg-canvas">
      <div className="flex items-center justify-between gap-2 border-b border-line bg-tile-2 px-3 py-1.5">
        <span className="flex items-center gap-1.5 font-mono text-[11px] font-semibold tracking-wide text-ink-muted">
          <span className={`h-2 w-2 rounded-full ${LANGUAGE_DOTS[label] || 'bg-white/40'}`} />
          {label}
        </span>
        <button
          type="button"
          onClick={copy}
          className="flex items-center gap-1 rounded-full px-2 py-1 font-mono text-[11px] text-ink-subtle transition-colors hover:bg-white/[0.06] hover:text-ink"
          aria-label="Copy code"
        >
          {copied ? <Check size={12} className="text-pop-mint" /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto px-4 py-3 font-mono text-[13px] leading-relaxed text-ink-muted">
        <code>{code}</code>
      </pre>
    </div>
  )
}
