export default function Workbench({ problem, editor }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start lg:gap-5">
      <div className="min-w-0 lg:sticky lg:top-8 lg:max-h-[calc(100dvh-4rem)] lg:overflow-y-auto lg:rounded-tile">
        {problem}
      </div>
      <div className="flex min-w-0 flex-col gap-4">{editor}</div>
    </div>
  )
}

export function EditorTile({ toolbar, children, footer }) {
  return (
    <section className="tile overflow-hidden">
      {toolbar && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">{toolbar}</div>
      )}
      <div className="p-3">{children}</div>
      {footer && <div className="flex flex-wrap items-center gap-3 border-t border-line px-4 py-3">{footer}</div>}
    </section>
  )
}

export function LanguagePicker({ languages, value, onChange, disabled }) {
  return (
    <div className="inline-flex w-fit items-center rounded-full border border-line bg-canvas/60 p-0.5" role="radiogroup" aria-label="Language">
      {languages.map(l => (
        <button
          key={l.value}
          type="button"
          role="radio"
          aria-checked={value === l.value}
          disabled={disabled}
          onClick={() => onChange(l.value)}
          className={`h-8 rounded-full px-3.5 font-mono text-xs font-medium transition-colors disabled:cursor-not-allowed ${
            value === l.value ? 'bg-ink text-canvas' : 'text-ink-subtle hover:text-ink'
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  )
}
