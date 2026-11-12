import { useEffect, useState } from 'react'
import { Cpu } from 'lucide-react'
import { modelAPI } from '../../utils/api'
import { OPEN_MODEL_EVENT } from './notifyModelError'

const DOT = { default: 'bg-pop-mint', none: 'bg-pop-coral' }

function sourceLine(s) {
  if (s.source === 'none') return 'Choose a model to start'
  if (s.source === 'default') return 'PET default'
  if (s.source === 'local') return `Local · ${s.provider_label}`
  return `Your ${s.provider_label} key${s.key_hint ? ` ··${s.key_hint}` : ''}`
}

export function useModelSettings() {
  const [settings, setSettings] = useState(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    modelAPI.get().then(({ data }) => setSettings(data)).catch(() => {})
    const show = () => setOpen(true)
    window.addEventListener(OPEN_MODEL_EVENT, show)
    return () => window.removeEventListener(OPEN_MODEL_EVENT, show)
  }, [])

  return { settings, setSettings, open, setOpen }
}

export default function ModelCard({ settings, onOpen }) {
  if (!settings) return null
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3 rounded-md border border-line bg-tile px-3 py-2.5 text-left transition-colors hover:border-line-strong hover:bg-tile-2"
    >
      <Cpu size={16} className="shrink-0 text-ink-subtle" aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block text-[11px] font-medium uppercase tracking-[0.08em] text-ink-faint">Model</span>
        <span className="block truncate font-mono text-[12px] text-ink">{settings.model || 'No model yet'}</span>
        <span className="block truncate text-[11px] text-ink-subtle">{sourceLine(settings)}</span>
      </span>
      <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[settings.source] || 'bg-pop-aqua'}`} aria-hidden="true" />
    </button>
  )
}
