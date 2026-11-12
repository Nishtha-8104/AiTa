// Question stems and statements mix prose with ```fenced``` code and `inline` code.
// Rendered as plain elements: no HTML from the model is ever injected.
export default function RichText({ text, className = '' }) {
  const parts = (text || '').split(/```[^\n]*\n([\s\S]*?)```/g)
  return (
    <div className={className}>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <pre key={i} className="my-3 overflow-x-auto whitespace-pre rounded-2xl border border-line bg-canvas p-4 font-mono text-[13px] leading-relaxed text-ink-muted">
            {part}
          </pre>
        ) : (
          <p key={i} className="whitespace-pre-wrap leading-relaxed">
            {part.split(/(`[^`\n]+`)/g).map((chunk, j) =>
              chunk.startsWith('`') && chunk.endsWith('`') && chunk.length > 2
                ? <code key={j} className="rounded-md bg-white/[0.07] px-1.5 py-0.5 font-mono text-[0.88em] text-pop-sun">{chunk.slice(1, -1)}</code>
                : chunk
            )}
          </p>
        )
      )}
    </div>
  )
}
