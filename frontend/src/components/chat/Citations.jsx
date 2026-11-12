import { BookOpen, ExternalLink } from 'lucide-react'

function citationLabel(citation) {
  return [citation.title, citation.chapter, citation.section].filter(Boolean).join(' › ')
}

export default function Citations({ citations, messageId, active }) {
  if (!citations?.length) return null
  return (
    <div className="mt-3 rounded-2xl border border-line bg-tile-2 px-3 py-2.5">
      <p className="eyebrow mb-1.5 flex items-center gap-1.5 text-[10px]">
        <BookOpen size={11} /> Sources
      </p>
      <ol className="space-y-0.5">
        {citations.map((citation, i) => {
          const n = i + 1
          const [title, ...rest] = [citation.title, citation.chapter, citation.section].filter(Boolean)
          const body = (
            <>
              <span className="font-medium text-ink-muted">{title || 'Untitled source'}</span>
              {rest.map((part, j) => (
                <span key={j} className="text-ink-subtle"> › {part}</span>
              ))}
            </>
          )
          return (
            <li
              key={n}
              id={`cite-${messageId}-${n}`}
              className={`flex items-start gap-2 rounded-lg px-1.5 py-1 text-xs leading-snug transition-colors duration-300 ${active === n ? 'bg-brand-500/15 ring-1 ring-brand-400/30' : ''}`}
            >
              <span className="mt-px inline-flex h-4 min-w-[1rem] shrink-0 items-center justify-center rounded bg-brand-500/15 px-1 font-mono text-[10px] font-bold text-brand-300">
                {n}
              </span>
              {citation.url ? (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group min-w-0 flex-1 hover:underline decoration-white/20 underline-offset-2"
                  title={citationLabel(citation)}
                >
                  {body}
                  <ExternalLink size={10} className="ml-1 inline -translate-y-px text-ink-faint group-hover:text-brand-300" />
                </a>
              ) : (
                <span className="min-w-0 flex-1">{body}</span>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
