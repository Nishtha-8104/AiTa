import { useRef } from 'react'

export default function Tabs({ tabs, value, onChange, label, className = '', size = 'md' }) {
  const refs = useRef([])
  const index = tabs.findIndex(t => t.value === value)

  const onKeyDown = e => {
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    e.preventDefault()
    const enabled = tabs.map((t, i) => (t.disabled ? null : i)).filter(i => i !== null)
    const pos = enabled.indexOf(index)
    const next = enabled[(pos + step + enabled.length) % enabled.length]
    onChange(tabs[next].value)
    refs.current[next]?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={`flex max-w-full gap-1 overflow-x-auto rounded-full border border-line bg-tile p-1 [scrollbar-width:none] ${className}`}
    >
      {tabs.map((t, i) => {
        const Icon = t.icon
        const active = t.value === value
        return (
          <button
            key={t.value}
            ref={el => { refs.current[i] = el }}
            type="button"
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            disabled={t.disabled}
            onClick={() => onChange(t.value)}
            className={`flex shrink-0 items-center gap-1.5 rounded-full font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${
              size === 'sm' ? 'h-8 px-3 text-xs' : 'h-9 px-4 text-[13px]'
            } ${active ? 'bg-ink text-canvas' : 'text-ink-subtle hover:text-ink'}`}
          >
            {Icon && <Icon size={14} className="hidden sm:block" />}
            {t.label}
            {t.badge != null && (
              <span className={`rounded-full px-1.5 font-mono text-[10px] ${active ? 'bg-canvas/15' : 'bg-white/10'}`}>{t.badge}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
