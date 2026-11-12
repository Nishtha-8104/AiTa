import { useCallback, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  AlertCircle, ChevronDown, Clock, FileText, HeartHandshake,
  RotateCcw, ShieldAlert, ThumbsDown, ThumbsUp,
} from 'lucide-react'
import LogoMark from '../ui/LogoMark'
import CodeBlock from './CodeBlock'
import ToolChips from './ToolChips'
import Citations from './Citations'
import { splitProblem } from './problemContext'

const MODERATED = {
  abuse: 'abusive language',
  slur: 'a slur',
  sexual: 'sexual content',
  self_harm: 'self-harm',
}

const NOTICES = {
  busy:  { icon: Clock,       tone: 'text-pop-sun' },
  error: { icon: AlertCircle, tone: 'text-pop-coral' },
}

const LIVE_LABELS = {
  thinking: 'Thinking',
  waiting: 'PET is still working on your last message',
  reconnecting: 'Connection dropped — fetching the saved reply',
}

const NO_CITATIONS = []

// The character before "[" is captured so indexing like arr[1] or grid[0][2] in prose is
// not taken for a ref; a lookbehind would break the whole module on Safari < 16.4.
const REF = /(^|[^\w\])])\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]/

const citationLabel = (c) => (c ? [c.title, c.chapter, c.section].filter(Boolean).join(' › ') : '')

function refNode(n) {
  return { type: 'element', tagName: 'sup', properties: { dataCite: n }, children: [{ type: 'text', value: String(n) }] }
}

// Turns "[2]" or "[1, 3]" in the answer text into clickable refs, leaving code alone.
function linkRefs(node, count) {
  if (!node.children || ['code', 'pre', 'a'].includes(node.tagName)) return
  const next = []
  for (const child of node.children) {
    if (child.type !== 'text') {
      linkRefs(child, count)
      next.push(child)
      continue
    }
    const parts = child.value.split(REF)
    if (parts.length === 1) {
      next.push(child)
      continue
    }
    // split() with two groups yields text, the character before "[", the ref list, text...
    for (let i = 0; i < parts.length; i += 3) {
      if (parts[i]) next.push({ type: 'text', value: parts[i] })
      if (i + 2 >= parts.length) break
      if (parts[i + 1]) next.push({ type: 'text', value: parts[i + 1] })
      const refs = parts[i + 2].split(',').map(s => Number(s.trim()))
      if (refs.every(n => n >= 1 && n <= count)) refs.forEach(n => next.push(refNode(n)))
      else next.push({ type: 'text', value: `[${parts[i + 2]}]` })
    }
  }
  node.children = next
}

function rehypeCiteRefs({ count }) {
  return (tree) => {
    if (count) linkRefs(tree, count)
  }
}

function hastText(node) {
  if (!node) return ''
  if (node.type === 'text') return node.value
  return (node.children || []).map(hastText).join('')
}

function FencedCode({ node }) {
  const code = node?.children?.find(c => c.tagName === 'code')
  const classes = (code?.properties?.className || []).map(String)
  const language = classes.find(c => c.startsWith('language-'))?.slice('language-'.length) || ''
  return <CodeBlock code={hastText(code || node).replace(/\n$/, '')} language={language} />
}

function AnswerMarkdown({ content, citations, onCite }) {
  const count = citations?.length || 0
  const rehypePlugins = useMemo(() => [[rehypeCiteRefs, { count }]], [count])
  const components = useMemo(() => ({
    pre: ({ node }) => <FencedCode node={node} />,
    code: ({ children }) => (
      <code className="rounded-md bg-white/[0.07] px-1.5 py-0.5 font-mono text-[0.85em] text-pop-sun">{children}</code>
    ),
    sup: ({ node, children }) => {
      const n = Number(node?.properties?.dataCite)
      if (!n) return <sup>{children}</sup>
      return (
        <button
          type="button"
          onClick={() => onCite(n)}
          title={citationLabel(citations[n - 1])}
          aria-label={`Source ${n}: ${citationLabel(citations[n - 1])}`}
          className="mx-0.5 inline-flex h-[1.05rem] min-w-[1.05rem] -translate-y-[2px] items-center justify-center rounded bg-brand-500/15 px-1 align-middle font-mono text-[10px] font-bold text-brand-300 transition-colors hover:bg-brand-500/30 hover:text-ink"
        >
          {n}
        </button>
      )
    },
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer" className="text-brand-300 underline decoration-brand-400/40 underline-offset-2 hover:text-brand-200">{children}</a>
    ),
    p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
    ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5 marker:text-brand-400/70">{children}</ul>,
    ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5 marker:text-ink-subtle">{children}</ol>,
    li: ({ children }) => <li className="pl-0.5">{children}</li>,
    h1: ({ children }) => <h3 className="mb-2 mt-4 font-display text-base font-bold text-ink first:mt-0">{children}</h3>,
    h2: ({ children }) => <h3 className="mb-2 mt-4 font-display text-[15px] font-bold text-ink first:mt-0">{children}</h3>,
    h3: ({ children }) => <h4 className="mb-1.5 mt-3 font-display text-sm font-semibold text-ink first:mt-0">{children}</h4>,
    h4: ({ children }) => <h4 className="mb-1 mt-3 text-sm font-semibold text-ink first:mt-0">{children}</h4>,
    strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
    blockquote: ({ children }) => <blockquote className="my-2 border-l-2 border-pop-aqua/40 pl-3 text-ink-subtle">{children}</blockquote>,
    hr: () => <hr className="my-4 border-line" />,
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto rounded-xl border border-line">
        <table className="w-full border-collapse text-xs">{children}</table>
      </div>
    ),
    th: ({ children }) => <th className="border-b border-line bg-tile-2 px-2.5 py-1.5 text-left font-semibold text-ink">{children}</th>,
    td: ({ children }) => <td className="border-t border-white/[0.06] px-2.5 py-1.5 align-top">{children}</td>,
  }), [citations, onCite])

  return (
    <div className="break-words text-sm leading-relaxed text-ink-muted">
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={rehypePlugins}
        components={components}
        disallowedElements={['img']}
        unwrapDisallowed
      >
        {content}
      </Markdown>
    </div>
  )
}

function UserText({ text }) {
  const parts = text.split(/```([^\n`]*)\n([\s\S]*?)```/)
  const out = []
  for (let i = 0; i < parts.length; i += 3) {
    const prose = parts[i].replace(/^\n+|\n+$/g, '')
    if (prose) out.push(<p key={i} className="whitespace-pre-wrap break-words">{prose}</p>)
    if (i + 2 < parts.length) {
      out.push(
        <pre key={`code-${i}`} className="my-2 overflow-x-auto rounded-xl bg-canvas px-3 py-2 font-mono text-xs leading-6 text-pop-mint/90">
          {parts[i + 2]}
        </pre>
      )
    }
  }
  return out
}

function ProblemContext({ text }) {
  const [open, setOpen] = useState(false)
  const title = text.split('\n')[0].replace(/\s*\(problem_id \d+\)$/, '')
  return (
    <div className="mb-2 overflow-hidden rounded-lg border border-brand-400/20 bg-brand-500/[0.07]">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-left text-[11px] text-brand-200/90"
      >
        <FileText size={12} className="shrink-0" />
        <span className="truncate">Problem attached · {title}</span>
        <ChevronDown size={12} className={`ml-auto shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="max-h-48 overflow-y-auto whitespace-pre-wrap border-t border-brand-400/15 px-2.5 py-2 text-[11px] leading-relaxed text-ink-subtle">
          {text}
        </div>
      )}
    </div>
  )
}

function Avatar() {
  return <LogoMark className="mt-0.5 h-7 w-7" />
}

const DOT_DELAYS = ['', '[animation-delay:150ms]', '[animation-delay:300ms]']

function Typing({ status }) {
  return (
    <div className="flex items-center gap-2 py-1 text-xs text-ink-subtle">
      <span className="flex gap-1">
        {DOT_DELAYS.map(delay => (
          <span key={delay} className={`h-1.5 w-1.5 animate-bounce rounded-full bg-pop-mint/80 ${delay}`} />
        ))}
      </span>
      {LIVE_LABELS[status] || LIVE_LABELS.thinking}…
    </div>
  )
}

function ThumbButton({ active, onClick, label, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      title={label}
      className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${active ? 'bg-white/[0.08] text-ink' : 'text-ink-faint hover:bg-white/[0.06] hover:text-ink-muted'}`}
    >
      {children}
    </button>
  )
}

export default function ChatMessage({ message, onThumbs, onRetry }) {
  const [activeCite, setActiveCite] = useState(null)
  const timer = useRef(null)

  const onCite = useCallback((n) => {
    setActiveCite(n)
    document.getElementById(`cite-${message.id}-${n}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setActiveCite(null), 2200)
  }, [message.id])

  if (message.role === 'user') {
    const { problem, question } = splitProblem(message.content || '')
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[85%] rounded-[20px] rounded-br-md bg-tile-3 px-4 py-2.5 text-sm leading-relaxed text-ink">
          {problem && <ProblemContext text={problem} />}
          <UserText text={question} />
        </div>
      </div>
    )
  }

  if (message.live) {
    return (
      <div className="flex gap-3">
        <Avatar />
        <div className="min-w-0 flex-1 pt-0.5">
          <ToolChips traces={message.tools} />
          {message.content
            ? <AnswerMarkdown content={message.content} citations={NO_CITATIONS} onCite={onCite} />
            : <Typing status={message.status} />}
        </div>
      </div>
    )
  }

  const notice = NOTICES[message.moderation_flag]
  const moderated = MODERATED[message.moderation_flag]

  if (notice) {
    const Icon = notice.icon
    return (
      <div className="flex gap-3 animate-fade-in">
        <Avatar />
        <div className="min-w-0 flex-1 pt-0.5">
          <ToolChips traces={message.tool_calls} />
          <div className="flex items-start gap-2.5 rounded-2xl border border-dashed border-line-strong bg-tile-2 px-3.5 py-2.5 text-sm text-ink-muted">
            <Icon size={15} className={`mt-0.5 shrink-0 ${notice.tone}`} />
            <div className="min-w-0">
              <p>{message.content}</p>
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-300 transition-colors hover:text-brand-200"
                >
                  <RotateCcw size={12} /> Try again
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="group flex gap-3 animate-fade-in">
      <Avatar />
      <div className="min-w-0 flex-1 pt-0.5">
        <ToolChips traces={message.tool_calls} />
        {moderated && (
          message.moderation_flag === 'self_harm' ? (
            <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-rose-400/25 bg-rose-500/10 px-2.5 py-0.5 text-[11px] text-rose-200/90">
              <HeartHandshake size={11} /> Support message
            </div>
          ) : (
            <div
              className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-amber-400/25 bg-amber-500/10 px-2.5 py-0.5 text-[11px] text-amber-200/90"
              title={`The safety filter flagged ${moderated} in this exchange`}
            >
              <ShieldAlert size={11} /> Safety reply
            </div>
          )
        )}
        <AnswerMarkdown content={message.content || ''} citations={message.citations || NO_CITATIONS} onCite={onCite} />
        <Citations citations={message.citations} messageId={message.id} active={activeCite} />
        {typeof message.id === 'number' && onThumbs && (
          <div className="mt-1.5 flex items-center gap-0.5 opacity-60 transition-opacity group-hover:opacity-100">
            <ThumbButton
              label="Helpful"
              active={message.thumbs === 'up'}
              onClick={() => onThumbs(message, message.thumbs === 'up' ? null : 'up')}
            >
              <ThumbsUp size={13} />
            </ThumbButton>
            <ThumbButton
              label="Not helpful"
              active={message.thumbs === 'down'}
              onClick={() => onThumbs(message, message.thumbs === 'down' ? null : 'down')}
            >
              <ThumbsDown size={13} />
            </ThumbButton>
          </div>
        )}
      </div>
    </div>
  )
}
