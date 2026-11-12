import { useEffect, useState } from 'react'

export function useElapsed(active) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!active) { setSeconds(0); return }
    const start = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [active])
  return seconds
}

// steps: [{ after: 0, text: '...' }, { after: 8, text: '...' }]
export default function BusyNote({ active, steps, note, className = '' }) {
  const seconds = useElapsed(active)
  if (!active) return null
  const current = [...steps].reverse().find(s => seconds >= s.after) || steps[0]
  return (
    <div className={`overflow-hidden rounded-[20px] border border-line-strong bg-tile-2 ${className}`} role="status" aria-live="polite">
      <div className="relative h-1 overflow-hidden bg-white/[0.04]">
        <span className="absolute inset-y-0 left-0 w-1/3 rounded-full bg-gradient-to-r from-transparent via-pop-mint to-transparent motion-safe:animate-shimmer" />
      </div>
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">{current.text}</p>
          {note && <p className="mt-0.5 text-xs text-ink-subtle">{note}</p>}
        </div>
        <span className="shrink-0 font-mono text-xs text-ink-subtle">{seconds}s</span>
      </div>
    </div>
  )
}
