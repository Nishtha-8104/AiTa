import { useCallback, useState } from 'react'
import { Wand2 } from 'lucide-react'
import { LANGUAGES, TEMPLATES } from '../code/templates'
import CodeEditorBox from '../ui/CodeEditor'
import { LanguagePicker } from '../practice/Workbench'

export { LANGUAGES, TEMPLATES }

// Normalise indentation, trim trailing whitespace and collapse extra blank lines.
function formatCode(code, language) {
  if (!code.trim()) return code
  const collapsed = []
  let blank = 0
  for (const line of code.split('\n').map(l => l.trimEnd())) {
    blank = line.trim() === '' ? blank + 1 : 0
    if (blank <= 2) collapsed.push(line)
  }
  return language === 'python' ? formatPython(collapsed) : formatBraces(collapsed)
}

function formatPython(lines) {
  const out = []
  let level = 0
  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) { out.push(''); continue }
    if (trimmed.startsWith('#')) { out.push('    '.repeat(level) + trimmed); continue }
    if (/^(else|elif|except|finally)\b/.test(trimmed)) level = Math.max(0, level - 1)
    out.push('    '.repeat(level) + trimmed)
    if (/:\s*$/.test(trimmed)) level++
    if (/^(return|pass|break|continue|raise)\b/.test(trimmed)) level = Math.max(0, level - 1)
  }
  return out.join('\n')
}

function formatBraces(lines) {
  const out = []
  let level = 0
  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) { out.push(''); continue }
    if (/^[}\])]/.test(trimmed)) level = Math.max(0, level - 1)
    out.push('    '.repeat(level) + trimmed)
    const opens = (trimmed.match(/[{[(]/g) || []).length
    const closes = (trimmed.match(/[}\])]/g) || []).length
    level = Math.max(0, level + opens - closes + (/^[}\])]/.test(trimmed) ? 1 : 0))
  }
  return out.join('\n')
}

export default function CodeEditor({ code, setCode, language, setLanguage, title, setTitle, evaluating, disabled }) {
  const [formatting, setFormatting] = useState(false)
  const lineCount = (code || '').split('\n').length

  const handleFormat = useCallback(() => {
    if (!code.trim()) return
    setFormatting(true)
    try { setCode(formatCode(code, language)) } catch { /* keep original */ }
    setFormatting(false)
  }, [code, language, setCode])

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <LanguagePicker languages={LANGUAGES} value={language} onChange={setLanguage} disabled={evaluating} />
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Name this attempt (optional)"
          aria-label="Submission name"
          className="order-last h-9 w-full min-w-0 rounded-full sm:order-none sm:w-auto sm:flex-1 border border-line bg-canvas/60 px-4 text-sm text-ink placeholder:text-ink-faint focus:border-brand-400/70 focus:outline-none"
        />
        <button
          type="button"
          onClick={handleFormat}
          disabled={formatting || !code.trim() || evaluating}
          className="flex h-9 items-center gap-1.5 rounded-full border border-line-strong px-3 text-xs font-medium text-ink-muted transition-colors hover:bg-white/[0.06] hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
          title="Tidy up indentation and blank lines"
        >
          <Wand2 size={13} /> Tidy
        </button>
      </div>
      <CodeEditorBox
        value={code}
        onChange={setCode}
        language={language}
        readOnly={evaluating || disabled}
        minHeight="380px"
        maxHeight="680px"
        label="Your code"
      />
      <div className="flex items-center gap-4 px-1 font-mono text-[11px] text-ink-faint">
        <span>{LANGUAGES.find(l => l.value === language)?.label}</span>
        <span>{lineCount} lines</span>
        <span>{code.length} characters</span>
      </div>
    </div>
  )
}
