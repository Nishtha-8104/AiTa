import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Copy, CheckCheck, Lightbulb, AlertTriangle } from 'lucide-react'

// ─── Simple Markdown renderer (no deps) ──────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return []

  // Split into lines for block-level parsing
  const lines = text.split('\n')
  const elements = []
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block
    if (line.trimStart().startsWith('```')) {
      const lang = line.replace(/^```/, '').trim() || 'text'
      const codeLines = []
      i++
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      elements.push(
        <CodeBlock key={key++} code={codeLines.join('\n')} language={lang} />
      )
      i++
      continue
    }

    // Heading
    if (/^#{1,3} /.test(line)) {
      const level = line.match(/^(#+)/)[1].length
      const content = line.replace(/^#+\s/, '')
      const sizes = ['text-base', 'text-sm', 'text-xs']
      elements.push(
        <p key={key++} className={`font-display font-700 text-white mt-3 mb-1 ${sizes[level-1] || 'text-sm'}`}>
          {inlineMarkdown(content)}
        </p>
      )
      i++
      continue
    }

    // Bullet list
    if (/^[-*•] /.test(line.trimStart())) {
      const items = []
      while (i < lines.length && /^[-*•] /.test(lines[i].trimStart())) {
        items.push(lines[i].replace(/^[\s]*[-*•] /, ''))
        i++
      }
      elements.push(
        <ul key={key++} className="space-y-1.5 my-2 ml-1">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-white/75 text-sm">
              <span className="text-brand-400 mt-1 shrink-0">▸</span>
              <span className="leading-relaxed">{inlineMarkdown(item)}</span>
            </li>
          ))}
        </ul>
      )
      continue
    }

    // Numbered list
    if (/^\d+\. /.test(line.trimStart())) {
      const items = []
      let num = 1
      while (i < lines.length && /^\d+\. /.test(lines[i].trimStart())) {
        items.push(lines[i].replace(/^[\s]*\d+\. /, ''))
        i++
      }
      elements.push(
        <ol key={key++} className="space-y-1.5 my-2 ml-1">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-white/75 text-sm">
              <span className="text-brand-400 font-mono font-600 text-xs mt-0.5 shrink-0 w-4">{idx+1}.</span>
              <span className="leading-relaxed">{inlineMarkdown(item)}</span>
            </li>
          ))}
        </ol>
      )
      continue
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={key++} className="border-white/10 my-3" />)
      i++
      continue
    }

    // Empty line → spacing
    if (line.trim() === '') {
      elements.push(<div key={key++} className="h-2" />)
      i++
      continue
    }

    // Normal paragraph line
    elements.push(
      <p key={key++} className="text-white/80 text-sm leading-relaxed">
        {inlineMarkdown(line)}
      </p>
    )
    i++
  }

  return elements
}

function inlineMarkdown(text) {
  // Handle inline code, bold, italic
  const parts = []
  let remaining = text
  let key = 0

  // Process inline patterns
  const patterns = [
    { re: /`([^`]+)`/g,        render: (m, g) => <code key={key++} className="px-1.5 py-0.5 bg-surface-600 text-brand-300 rounded font-mono text-xs">{g}</code> },
    { re: /\*\*([^*]+)\*\*/g,  render: (m, g) => <strong key={key++} className="font-700 text-white">{g}</strong> },
    { re: /\*([^*]+)\*/g,      render: (m, g) => <em key={key++} className="italic text-white/90">{g}</em> },
  ]

  // Build a combined regex to split on all patterns at once
  const combined = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g
  const tokens = text.split(combined)

  return tokens.map((token, i) => {
    if (!token) return null
    if (/^`[^`]+`$/.test(token)) {
      return <code key={i} className="px-1.5 py-0.5 bg-surface-600 text-brand-300 rounded font-mono text-xs">{token.slice(1,-1)}</code>
    }
    if (/^\*\*[^*]+\*\*$/.test(token)) {
      return <strong key={i} className="font-700 text-white">{token.slice(2,-2)}</strong>
    }
    if (/^\*[^*]+\*$/.test(token)) {
      return <em key={i} className="italic text-white/90">{token.slice(1,-1)}</em>
    }
    return <span key={i}>{token}</span>
  })
}

// ─── Code block component ─────────────────────────────────────────────────────
function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-white/[0.08] bg-[#0d1117]">
      <div className="flex items-center justify-between px-4 py-2 bg-surface-700/50 border-b border-white/[0.06]">
        <span className="text-xs font-mono text-white/30 uppercase tracking-wider">{language}</span>
        <button onClick={copy}
          className="flex items-center gap-1.5 text-white/30 hover:text-white/70 text-xs transition-colors">
          {copied ? <CheckCheck size={13} className="text-green-400" /> : <Copy size={13} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-sm font-mono text-green-300/90 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  )
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 px-4 py-3">
      <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-500/30 flex items-center justify-center shrink-0">
        <span className="text-brand-400 text-xs font-mono font-700">AI</span>
      </div>
      <div className="glass-card px-4 py-3">
        <div className="flex gap-1.5 items-center h-5">
          {[0, 1, 2].map(i => (
            <div key={i} className="w-2 h-2 rounded-full bg-brand-400 animate-bounce"
              style={{ animationDelay: `${i * 150}ms` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Main MessageBubble ───────────────────────────────────────────────────────
export default function MessageBubble({ message, onRate }) {
  const isUser      = message.role === 'user'
  const isTyping    = message._typing
  const isPending   = message._pending

  if (isTyping) return <TypingIndicator />

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2 animate-slide-up">
        <div className="max-w-[80%]">
          {/* Code context shown above the message */}
          {message.code_snippet && (
            <div className="mb-2">
              <CodeBlock code={message.code_snippet} language={message.code_language || 'python'} />
            </div>
          )}
          {message.error_message && (
            <div className="mb-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle size={12} className="text-red-400" />
                <span className="text-xs font-mono text-red-400">Error</span>
              </div>
              <pre className="text-xs text-red-300/80 font-mono overflow-x-auto whitespace-pre-wrap">
                {message.error_message}
              </pre>
            </div>
          )}
          <div className={`px-4 py-3 rounded-2xl rounded-tr-sm bg-brand-600/20 border border-brand-500/25 ${isPending ? 'opacity-60' : ''}`}>
            <p className="text-white/90 text-sm leading-relaxed">{message.content}</p>
          </div>
          <p className="text-white/20 text-xs text-right mt-1 font-mono">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    )
  }

  // ── Assistant message ──────────────────────────────────────────────────────
  return (
    <div className="flex items-start gap-3 px-4 py-2 animate-slide-up">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-500/30 flex items-center justify-center shrink-0 mt-1">
        <span className="text-brand-400 text-xs font-mono font-700">AI</span>
      </div>

      <div className="flex-1 min-w-0 max-w-[88%]">
        {/* Message content */}
        <div className="glass-card px-5 py-4 rounded-2xl rounded-tl-sm">
          <div className="space-y-0.5">
            {renderMarkdown(message.content)}
          </div>

          {/* Concepts detected */}
          {message._concepts?.length > 0 && (
            <div className="mt-4 pt-3 border-t border-white/[0.06]">
              <p className="text-white/20 text-xs font-mono uppercase tracking-wider mb-2">Topics covered</p>
              <div className="flex flex-wrap gap-1.5">
                {message._concepts.map(c => (
                  <span key={c} className="px-2 py-0.5 bg-brand-600/10 border border-brand-500/20 rounded-md text-xs text-brand-300 font-mono">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Confusion warning */}
          {message._confusion && (
            <div className="mt-3 flex items-start gap-2 bg-yellow-500/5 border border-yellow-500/15 rounded-xl px-3 py-2">
              <AlertTriangle size={13} className="text-yellow-400 shrink-0 mt-0.5" />
              <p className="text-yellow-300/70 text-xs">I noticed some confusion. Let's slow down — feel free to ask me to explain differently.</p>
            </div>
          )}
        </div>

        {/* Suggestions */}
        {message._suggestions?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {message._suggestions.slice(0, 3).map((s, i) => (
              <button key={i}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-700/60 hover:bg-surface-600/80 border border-white/10 hover:border-white/20 rounded-xl text-xs text-white/50 hover:text-white/80 transition-all text-left max-w-[260px] truncate"
                title={s}>
                <Lightbulb size={11} className="text-yellow-400 shrink-0" />
                {s.length > 45 ? s.slice(0, 45) + '…' : s}
              </button>
            ))}
          </div>
        )}

        {/* Footer: timestamp + rating */}
        <div className="flex items-center gap-3 mt-1.5 px-1">
          <span className="text-white/20 text-xs font-mono">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {message.latency_ms > 0 && (
            <span className="text-white/15 text-xs font-mono">{message.latency_ms}ms</span>
          )}
          {!isNaN(message.id) && onRate && (
            <div className="ml-auto flex items-center gap-1">
              <button onClick={() => onRate(message.id, true)}
                className={`p-1.5 rounded-lg transition-all ${message.was_helpful === true ? 'text-green-400 bg-green-500/10' : 'text-white/20 hover:text-green-400 hover:bg-green-500/10'}`}>
                <ThumbsUp size={13} />
              </button>
              <button onClick={() => onRate(message.id, false)}
                className={`p-1.5 rounded-lg transition-all ${message.was_helpful === false ? 'text-red-400 bg-red-500/10' : 'text-white/20 hover:text-red-400 hover:bg-red-500/10'}`}>
                <ThumbsDown size={13} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}