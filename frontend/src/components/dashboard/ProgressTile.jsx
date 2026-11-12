import { Award, Eye } from 'lucide-react'
import { BAND_STYLE } from '../learning/labels'
import Button from '../ui/Button'
import Chip from '../ui/Chip'

function Compare({ label, now, before }) {
  const max = Math.max(now, before, 1)
  const diff = now - before
  return (
    <li>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="text-ink-muted">{label}</span>
        <span className="font-mono text-xs text-ink-subtle">
          <span className="text-sm text-ink">{now}</span> vs {before}
          {diff !== 0 && (
            <span className={`ml-2 ${diff > 0 ? 'text-pop-mint' : 'text-ink-subtle'}`}>{diff > 0 ? `+${diff}` : diff}</span>
          )}
        </span>
      </div>
      <div className="mt-2 space-y-1" aria-hidden="true">
        <div className="h-1.5 rounded-full bg-pop-mint" style={{ width: `${(now / max) * 100}%`, minWidth: '6px' }} />
        <div className="h-1.5 rounded-full bg-white/15" style={{ width: `${(before / max) * 100}%`, minWidth: '6px' }} />
      </div>
    </li>
  )
}

function Stat({ value, label }) {
  return (
    <div>
      <div className="font-mono text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{value}</div>
      <div className="mt-1 text-xs text-ink-subtle">{label}</div>
    </div>
  )
}

function NextSteps({ topics }) {
  const close = topics
    .filter(t => t.band !== 'unseen' && t.next_band)
    .sort((a, b) => a.gap_to_next - b.gap_to_next)
    .slice(0, 3)
  if (close.length === 0) return null
  return (
    <div className="mt-6 border-t border-line pt-5">
      <p className="eyebrow">Closest to the next level</p>
      <ul className="mt-3 space-y-2">
        {close.map(t => (
          <li key={t.topic} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate text-ink">{t.label}</span>
            <span className={`shrink-0 font-mono text-xs ${BAND_STYLE[t.next_band]?.text || 'text-ink-subtle'}`}>
              {Math.max(1, Math.round(t.gap_to_next * 100))}% to {BAND_STYLE[t.next_band]?.label || t.next_band}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ProgressTile({ data, revealed, onReveal }) {
  if (!data || data.mode === 'off') return null

  if (data.mode === 'silent' && !revealed) {
    return (
      <section className="tile flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="eyebrow">Progress recap</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Your progress recap is ready.</h2>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-subtle">Points, level and badges stay hidden until you open them.</p>
        </div>
        <Button icon={Eye} onClick={onReveal} className="self-start sm:self-auto">Reveal my progress</Button>
      </section>
    )
  }

  const { last_7: now, prev_7: before } = data.self_board

  return (
    <section className="tile h-full p-6">
      <p className="eyebrow">Your progress</p>
      <div className="mt-4 grid grid-cols-3 gap-4">
        <Stat value={data.points.toLocaleString('en-IN')} label="Points" />
        <Stat value={data.level} label="Level" />
        <Stat value={now.solved} label="Solved this week" />
      </div>

      <div className="mt-6 border-t border-line pt-5">
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <p className="eyebrow">You vs past you</p>
          <span className="flex items-center gap-3 text-[11px] text-ink-subtle">
            <span className="flex items-center gap-1.5"><span className="h-1.5 w-3 rounded-full bg-pop-mint" aria-hidden="true" />Last 7 days</span>
            <span className="flex items-center gap-1.5"><span className="h-1.5 w-3 rounded-full bg-white/15" aria-hidden="true" />7 days before</span>
          </span>
        </div>
        <ul className="mt-4 space-y-4">
          <Compare label="Points" now={now.points} before={before.points} />
          <Compare label="Items solved" now={now.solved} before={before.solved} />
          <Compare label="Topics levelled up" now={now.level_ups} before={before.level_ups} />
        </ul>
      </div>

      <NextSteps topics={data.topics} />

      <div className="mt-6 border-t border-line pt-5">
        <p className="eyebrow">Badges</p>
        {data.badges.length === 0 ? (
          <p className="mt-3 text-[13px] text-ink-subtle">None yet. They show up when you earn them.</p>
        ) : (
          <ul className="mt-3 flex flex-wrap gap-2">
            {data.badges.map(b => (
              <li key={b.code} title={b.message}>
                <Chip tone="sun" icon={Award}>{b.title}</Chip>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
