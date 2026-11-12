import { useEffect, useRef, useState } from 'react'
import { ChevronDown, History, MessageSquare } from 'lucide-react'

function ago(iso) {
  const t = new Date(iso).getTime()
  if (!t) return ''
  const s = (Date.now() - t) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`
  return new Date(t).toLocaleDateString()
}

export default function ThreadPicker({ threads, currentId, onSelect }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const current = threads.find(t => t.id === currentId)
  const label = currentId ? (current?.title || 'Untitled chat') : 'New conversation'

  return (
    <div ref={ref} className="min-w-0">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex max-w-full items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink"
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Switch conversation"
      >
        <History size={12} className="shrink-0" />
        <span className="truncate">{label}</span>
        <ChevronDown size={12} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute inset-x-3 top-full z-30 mt-1 animate-fade-in rounded-2xl border border-line-strong bg-tile-2 p-1.5 shadow-[0_24px_48px_-12px_rgba(0,0,0,0.7)]">
          <p className="eyebrow px-2.5 pb-1 pt-1.5 text-[10px]">Recent chats</p>
          {threads.length === 0 ? (
            <p className="px-2.5 py-3 text-xs text-ink-subtle">No saved chats yet.</p>
          ) : (
            <ul className="max-h-72 overflow-y-auto" role="listbox">
              {threads.map(t => {
                const selected = t.id === currentId
                return (
                  <li key={t.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={selected}
                      onClick={() => { setOpen(false); if (!selected) onSelect(t.id) }}
                      className={`flex w-full items-start gap-2 rounded-xl px-2.5 py-2 text-left transition-colors ${selected ? 'bg-white/[0.08] text-ink' : 'text-ink-muted hover:bg-white/[0.05] hover:text-ink'}`}
                    >
                      <MessageSquare size={13} className={`mt-0.5 shrink-0 ${selected ? 'text-pop-mint' : 'text-ink-faint'}`} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13px]">{t.title || 'Untitled chat'}</span>
                        <span className="block font-mono text-[10px] text-ink-faint">{ago(t.updated_at || t.created_at)}</span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
