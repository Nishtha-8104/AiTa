import { useState, useRef, useCallback } from 'react'
import { Code2, ChevronDown, Play, X, Plus, Wand2 } from 'lucide-react'

const LANGUAGES = [
  { value: 'python',     label: 'Python',     ext: '.py'   },
  { value: 'javascript', label: 'JavaScript', ext: '.js'   },
  { value: 'typescript', label: 'TypeScript', ext: '.ts'   },
  { value: 'java',       label: 'Java',       ext: '.java' },
  { value: 'cpp',        label: 'C++',        ext: '.cpp'  },
  { value: 'c',          label: 'C',          ext: '.c'    },
  { value: 'go',         label: 'Go',         ext: '.go'   },
  { value: 'rust',       label: 'Rust',       ext: '.rs'   },
  { value: 'sql',        label: 'SQL',        ext: '.sql'  },
]

const PLACEHOLDERS = {
  python:     '# Paste or type your Python code here\ndef solution():\n    pass\n',
  javascript: '// Paste or type your JavaScript code here\nfunction solution() {\n\n}\n',
  typescript: '// Paste or type your TypeScript code here\nfunction solution(): void {\n\n}\n',
  java:       '// Paste or type your Java code here\npublic class Solution {\n    public static void main(String[] args) {\n\n    }\n}\n',
  cpp:        '// Paste or type your C++ code here\n#include <iostream>\nusing namespace std;\n\nint main() {\n\n    return 0;\n}\n',
  c:          '// Paste or type your C code here\n#include <stdio.h>\n\nint main() {\n\n    return 0;\n}\n',
  go:         '// Paste or type your Go code here\npackage main\n\nimport "fmt"\n\nfunc main() {\n\n}\n',
  rust:       '// Paste or type your Rust code here\nfn main() {\n\n}\n',
  sql:        '-- Paste or type your SQL code here\nSELECT *\nFROM table_name\nWHERE condition;\n',
}


// ── Code Formatter ────────────────────────────────────────────────────────────
// LeetCode-style: normalise indentation, remove trailing whitespace,
// ensure consistent spacing around operators, collapse extra blank lines.

function formatCode(code, language) {
  if (!code.trim()) return code
  let lines = code.split('\n')

  // 1. Remove trailing whitespace from every line
  lines = lines.map(l => l.trimEnd())

  // 2. Collapse 3+ consecutive blank lines into 2
  const collapsed = []
  let blankCount = 0
  for (const line of lines) {
    if (line.trim() === '') {
      blankCount++
      if (blankCount <= 2) collapsed.push(line)
    } else {
      blankCount = 0
      collapsed.push(line)
    }
  }

  // 3. Language-specific normalisation
  if (language === 'python') {
    return formatPython(collapsed)
  }
  if (['javascript', 'typescript'].includes(language)) {
    return formatJSLike(collapsed)
  }
  if (['java', 'cpp', 'c', 'go', 'rust'].includes(language)) {
    return formatCLike(collapsed)
  }

  return collapsed.join('\n')
}

function formatPython(lines) {
  const out = []
  let indentLevel = 0
  const IND = '    '
  const OPENERS = /:\s*$/
  const DEDENT_KW = /^(return|pass|break|continue|raise)\b/

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]
    const trimmed = raw.trim()

    // Keep blank lines as-is
    if (!trimmed) { out.push(''); continue }

    // Comments keep current indent
    if (trimmed.startsWith('#')) {
      out.push(IND.repeat(indentLevel) + trimmed); continue
    }

    // Dedenting keywords (else, elif, except, finally, with) – drop one level
    if (/^(else|elif|except|finally)\b/.test(trimmed)) {
      indentLevel = Math.max(0, indentLevel - 1)
    }

    out.push(IND.repeat(indentLevel) + trimmed)

    // Increase indent after block openers
    if (OPENERS.test(trimmed) && !trimmed.startsWith('#')) {
      indentLevel++
    }
    // Decrease after single-line terminators
    if (DEDENT_KW.test(trimmed)) {
      indentLevel = Math.max(0, indentLevel - 1)
    }
  }
  return out.join('\n')
}

function formatJSLike(lines) {
  const out = []
  let indentLevel = 0
  const IND = '  '   // JS commonly uses 2-space indent

  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) { out.push(''); continue }

    // Closing brace/bracket before printing
    if (/^[}\])]/.test(trimmed)) {
      indentLevel = Math.max(0, indentLevel - 1)
    }

    out.push(IND.repeat(indentLevel) + trimmed)

    // Opening brace increases indent
    const opens  = (trimmed.match(/[{[(]/g) || []).length
    const closes = (trimmed.match(/[}\])]/g) || []).length
    indentLevel  = Math.max(0, indentLevel + opens - closes)
    // Already handled leading close above
    if (/^[}\])]/.test(trimmed)) indentLevel = Math.max(0, indentLevel)
  }
  return out.join('\n')
}

function formatCLike(lines) {
  // Same brace-matching logic as JS
  return formatJSLike(lines)
}


// ── Component ─────────────────────────────────────────────────────────────────

export default function CodeEditor({
  code, setCode, language, setLanguage,
  title, setTitle, problemContext, setProblemContext,
  expectedOutput, setExpectedOutput,
  onEvaluate, evaluating, disabled, hideProblemPanel,
}) {
  const [showLangMenu, setShowLangMenu] = useState(false)
  const [showContext,  setShowContext]  = useState(false)
  const [formatting,   setFormatting]  = useState(false)
  const textareaRef                    = useRef(null)

  const currentLang = LANGUAGES.find(l => l.value === language) || LANGUAGES[0]
  const lineCount   = (code || '').split('\n').length

  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const ta     = textareaRef.current
      const start  = ta.selectionStart
      const end    = ta.selectionEnd
      const spaces = '    '
      setCode(code.slice(0, start) + spaces + code.slice(end))
      setTimeout(() => { ta.selectionStart = ta.selectionEnd = start + spaces.length }, 0)
    }
  }

  const handleFormat = useCallback(() => {
    if (!code.trim()) return
    setFormatting(true)
    setTimeout(() => {
      try {
        const formatted = formatCode(code, language)
        setCode(formatted)
      } catch { /* keep original on error */ }
      setFormatting(false)
    }, 120)   // short delay so the spinner is visible
  }, [code, language, setCode])

  return (
    <div className="flex flex-col h-full">

      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-surface-800/80 border-b border-white/[0.06] shrink-0">

        {/* Language picker */}
        <div className="relative">
          <button
            onClick={() => setShowLangMenu(v => !v)}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface-700/60 hover:bg-surface-600 border border-white/10 rounded-lg text-sm font-mono text-white/70 transition-colors"
          >
            <Code2 size={14} className="text-brand-400" />
            {currentLang.label}
            <ChevronDown size={12} className="text-white/30" />
          </button>
          {showLangMenu && (
            <div className="absolute top-full left-0 mt-1 z-50 glass-card w-40 rounded-xl overflow-hidden shadow-2xl animate-slide-up">
              {LANGUAGES.map(l => (
                <button key={l.value}
                  onClick={() => { setLanguage(l.value); setShowLangMenu(false) }}
                  className={`w-full flex items-center justify-between px-4 py-2.5 text-sm font-mono hover:bg-surface-600/60 transition-colors ${language === l.value ? 'text-brand-400 bg-brand-600/10' : 'text-white/60'}`}
                >
                  {l.label}
                  <span className="text-white/20 text-xs">{l.ext}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Title input */}
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Submission title (optional)"
          className="flex-1 bg-transparent border-none text-sm text-white/60 placeholder-white/20 focus:outline-none font-body min-w-0"
        />

        {/* ── FORMAT BUTTON ── */}
        <button
          onClick={handleFormat}
          disabled={formatting || !code.trim() || evaluating}
          title="Format code (LeetCode style)"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-display font-600 border border-white/10 bg-surface-700/40 hover:bg-surface-600/80 hover:border-purple-500/40 hover:text-purple-300 text-white/40 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {formatting
            ? <div className="w-3 h-3 border border-white/30 border-t-purple-400 rounded-full animate-spin" />
            : <Wand2 size={13} />}
          <span className="hidden sm:inline">{formatting ? 'Formatting…' : 'Format'}</span>
        </button>

        {/* Context toggle — hidden when parent handles problem statement */}
        {!hideProblemPanel && (
          <button
            onClick={() => setShowContext(v => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-display font-600 border transition-all ${showContext ? 'border-purple-500/40 bg-purple-600/10 text-purple-300' : 'border-white/10 text-white/30 hover:text-white/60'}`}
          >
            <Plus size={12} /> Context
          </button>
        )}

        {/* Evaluate */}
        <button
          onClick={onEvaluate}
          disabled={evaluating || !code.trim() || disabled}
          className="flex items-center gap-2 px-4 py-1.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-display font-600 rounded-lg transition-all active:scale-95"
        >
          {evaluating
            ? <><div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Evaluating…</>
            : <><Play size={14} /> Evaluate</>}
        </button>
      </div>

      {/* ── Context panel — only shown when not using parent's problem panel ── */}
      {!hideProblemPanel && showContext && (
        <div className="shrink-0 border-b border-white/[0.06] bg-surface-800/40 px-4 py-3 animate-slide-up grid grid-cols-2 gap-3">
          <div>
            <p className="label text-xs mb-1">Problem Statement</p>
            <textarea value={problemContext} onChange={e => setProblemContext(e.target.value)}
              placeholder="Describe the problem (optional)..." rows={3}
              className="w-full bg-surface-700/40 border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-white/60 placeholder-white/20 font-body resize-none focus:outline-none focus:border-brand-500/30" />
          </div>
          <div>
            <p className="label text-xs mb-1">Expected Output</p>
            <textarea value={expectedOutput} onChange={e => setExpectedOutput(e.target.value)}
              placeholder="Expected output (optional)..." rows={3}
              className="w-full bg-surface-700/40 border border-white/[0.06] rounded-xl px-3 py-2 text-xs font-mono text-white/60 placeholder-white/20 resize-none focus:outline-none focus:border-brand-500/30" />
          </div>
        </div>
      )}

      {/* ── Code area ── */}
      <div className="flex flex-1 overflow-hidden bg-[#0d1117]">
        {/* Line numbers */}
        <div className="select-none shrink-0 w-10 py-4 text-right pr-3 bg-[#0d1117] border-r border-white/[0.04]">
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i} className="text-white/15 text-xs font-mono leading-6">{i + 1}</div>
          ))}
        </div>
        {/* Editor textarea */}
        <textarea
          ref={textareaRef}
          value={code}
          onChange={e => setCode(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={evaluating || disabled}
          placeholder={PLACEHOLDERS[language] || '// Write your code here'}
          spellCheck={false}
          className="flex-1 bg-transparent px-4 py-4 text-sm font-mono text-green-200/80 placeholder-white/10 resize-none focus:outline-none leading-6 disabled:opacity-50"
          style={{ tabSize: 4 }}
        />
      </div>

      {/* ── Status bar ── */}
      <div className="shrink-0 flex items-center gap-4 px-4 py-1.5 bg-surface-800/60 border-t border-white/[0.04] text-xs font-mono text-white/20">
        <span>{currentLang.label} {currentLang.ext}</span>
        <span>{lineCount} lines</span>
        <span>{code.length} chars</span>
        {evaluating  && <span className="text-orange-400 animate-pulse ml-auto">● Running agent…</span>}
        {formatting  && <span className="text-purple-400 animate-pulse ml-auto">✦ Formatting…</span>}
      </div>
    </div>
  )
}