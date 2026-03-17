import { useState, useRef, useEffect } from 'react'
import {
  Send, Code2, X, ChevronDown, Zap,
  MessageSquare, Brain, Puzzle, HelpCircle, BookOpen
} from 'lucide-react'

const MODES = [
  { value: 'qa',          label: 'Q&A',         icon: MessageSquare, color: 'text-brand-400',  desc: 'Ask anything' },
  { value: 'code_help',   label: 'Code Help',   icon: Code2,          color: 'text-green-400',  desc: 'Debug & explain' },
  { value: 'brainstorm',  label: 'Brainstorm',  icon: Brain,          color: 'text-purple-400', desc: 'Explore ideas' },
  { value: 'quiz',        label: 'Quiz Me',     icon: Puzzle,         color: 'text-yellow-400', desc: 'Test yourself' },
  { value: 'walkthrough', label: 'Walkthrough', icon: BookOpen,       color: 'text-pink-400',   desc: 'Step by step' },
]

export default function ChatInput({ onSend, sending, sessionMode, onModeChange, disabled }) {
  const [message, setMessage]         = useState('')
  const [showCode, setShowCode]       = useState(false)
  const [codeSnippet, setCodeSnippet] = useState('')
  const [codeLanguage, setCodeLang]   = useState('python')
  const [errorMessage, setError]      = useState('')
  const [showModes, setShowModes]     = useState(false)

  const textareaRef = useRef(null)
  const codeRef     = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'
  }, [message])

  const currentMode = MODES.find(m => m.value === sessionMode) || MODES[0]
  const ModeIcon    = currentMode.icon

  const handleSend = () => {
    if (!message.trim() || sending || disabled) return
    onSend({
      message:       message.trim(),
      codeSnippet:   codeSnippet.trim() || null,
      codeLanguage:  codeSnippet.trim() ? codeLanguage : null,
      errorMessage:  errorMessage.trim() || null,
    })
    setMessage('')
    setCodeSnippet('')
    setError('')
    setShowCode(false)
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-white/[0.06] bg-surface-900/95 backdrop-blur-xl px-4 py-4">

      {/* Code snippet panel */}
      {showCode && (
        <div className="mb-3 rounded-xl border border-white/[0.08] bg-surface-800/60 overflow-hidden animate-slide-up">
          <div className="flex items-center justify-between px-4 py-2.5 bg-surface-700/50 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
              <Code2 size={14} className="text-green-400" />
              <span className="text-xs font-mono text-white/50">Code Snippet</span>
              <select
                value={codeLanguage}
                onChange={e => setCodeLang(e.target.value)}
                className="bg-surface-600/80 border border-white/10 rounded-lg px-2 py-1 text-xs text-white/70 font-mono focus:outline-none"
              >
                {['python','javascript','java','c++','c','typescript','go','rust','sql'].map(l => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <button onClick={() => { setShowCode(false); setCodeSnippet(''); setError('') }}
              className="text-white/30 hover:text-white/70 transition-colors p-1">
              <X size={14} />
            </button>
          </div>
          <textarea
            ref={codeRef}
            value={codeSnippet}
            onChange={e => setCodeSnippet(e.target.value)}
            placeholder="Paste your code here..."
            rows={6}
            className="w-full bg-transparent px-4 py-3 text-sm font-mono text-green-300/80 placeholder-white/20 resize-none focus:outline-none"
          />
          <div className="px-4 pb-3">
            <input
              value={errorMessage}
              onChange={e => setError(e.target.value)}
              placeholder="Error / output (optional)"
              className="w-full bg-surface-700/40 border border-white/[0.06] rounded-lg px-3 py-2 text-xs font-mono text-red-300/70 placeholder-white/20 focus:outline-none focus:border-red-500/30"
            />
          </div>
        </div>
      )}

      {/* Main input row */}
      <div className="flex items-end gap-3">

        {/* Mode picker */}
        <div className="relative shrink-0">
          <button
            onClick={() => setShowModes(v => !v)}
            className="flex items-center gap-1.5 px-3 py-3 rounded-xl bg-surface-700/60 hover:bg-surface-600/80 border border-white/10 transition-all"
            title="Change mode"
          >
            <ModeIcon size={16} className={currentMode.color} />
            <ChevronDown size={12} className="text-white/30" />
          </button>

          {showModes && (
            <div className="absolute bottom-full left-0 mb-2 w-52 glass-card rounded-xl overflow-hidden shadow-2xl z-50 animate-slide-up">
              {MODES.map(m => {
                const Icon = m.icon
                return (
                  <button key={m.value}
                    onClick={() => { onModeChange(m.value); setShowModes(false) }}
                    className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-600/60 transition-colors text-left ${sessionMode === m.value ? 'bg-brand-600/10' : ''}`}
                  >
                    <Icon size={15} className={m.color} />
                    <div>
                      <p className="text-xs font-display font-600 text-white">{m.label}</p>
                      <p className="text-xs text-white/30">{m.desc}</p>
                    </div>
                    {sessionMode === m.value && <Zap size={12} className="text-brand-400 ml-auto" />}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Text area */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || sending}
            placeholder={
              sessionMode === 'code_help'   ? 'Describe your problem or paste code below...' :
              sessionMode === 'quiz'        ? 'Type your answer or ask for the next question...' :
              sessionMode === 'walkthrough' ? 'Tell me which concept to walk through...' :
              sessionMode === 'brainstorm'  ? 'Describe the problem you want to brainstorm...' :
              'Ask anything about programming...'
            }
            rows={1}
            className="w-full bg-surface-700/60 border border-white/10 rounded-xl px-4 py-3 pr-12 text-sm text-white placeholder-white/25 font-body resize-none focus:outline-none focus:border-brand-500/40 focus:ring-1 focus:ring-brand-500/20 transition-all disabled:opacity-40"
            style={{ minHeight: '48px', maxHeight: '180px' }}
          />
          {/* Code toggle button inside textarea */}
          <button
            onClick={() => { setShowCode(v => !v); setTimeout(() => codeRef.current?.focus(), 50) }}
            className={`absolute right-3 bottom-3 p-1.5 rounded-lg transition-all ${showCode ? 'text-green-400 bg-green-500/10' : 'text-white/20 hover:text-white/50'}`}
            title="Attach code (Ctrl+K)"
          >
            <Code2 size={15} />
          </button>
        </div>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!message.trim() || sending || disabled}
          className="shrink-0 w-12 h-12 flex items-center justify-center rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
        >
          {sending
            ? <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            : <Send size={18} className="text-white" />}
        </button>
      </div>

      {/* Hints */}
      <div className="flex items-center gap-4 mt-2 px-1">
        <span className="text-white/15 text-xs">Enter to send · Shift+Enter for new line</span>
        {codeSnippet && (
          <span className="flex items-center gap-1 text-green-400/50 text-xs">
            <Code2 size={11} /> Code attached
          </span>
        )}
      </div>
    </div>
  )
}