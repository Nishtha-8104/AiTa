import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, Lock, Target } from 'lucide-react'
import { BAND_STYLE } from '../learning/labels'
import LevelBar from '../ui/LevelBar'
import Button from '../ui/Button'

const ORDER = { weak: 0, developing: 1, unseen: 2, mastered: 3 }
const COLLAPSED = 6

function sortTopics(topics) {
  return [...topics].sort((a, b) => {
    if (a.unlocked !== b.unlocked) return a.unlocked ? -1 : 1
    const band = t => (t.evidence_count === 0 ? 'unseen' : t.band)
    return (ORDER[band(a)] - ORDER[band(b)]) || (a.mastery - b.mastery)
  })
}

function TopicRow({ topic, current }) {
  const seen = topic.evidence_count > 0
  const band = seen ? topic.band : 'unseen'
  const style = BAND_STYLE[band] || BAND_STYLE.unseen
  const note = !topic.unlocked ? 'Opens when earlier topics reach 40%'
    : seen ? `${topic.evidence_count} ${topic.evidence_count === 1 ? 'answer' : 'answers'}` : 'Not yet practised'
  return (
    <li className={`grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-x-4 gap-y-2 sm:grid-cols-[minmax(0,150px)_1fr_auto_auto] rounded-lg px-2.5 py-2 ${current ? 'bg-pop-sun/10' : ''} ${topic.unlocked ? '' : 'opacity-50'}`}>
      <div className="min-w-0">
        <p className="flex min-w-0 items-center gap-1.5 text-sm font-semibold text-ink">
          <span className="truncate">{topic.label}</span>
          {current && <span className="shrink-0 rounded-full bg-ink px-2 py-px text-[10px] font-semibold text-canvas">This question</span>}
        </p>
        <p className="mt-0.5 truncate text-[11.5px] text-ink-subtle">{note}</p>
      </div>
      <LevelBar value={seen ? topic.mastery : 0} band={band} className="order-last col-span-3 sm:order-none sm:col-span-1" />
      <span className="min-w-[3ch] text-right text-lg font-bold tabular-nums text-ink">
        {seen ? `${Math.round(topic.mastery * 100)}%` : ''}
      </span>
      {!topic.unlocked ? (
        <span className="flex items-center gap-1 rounded-full border border-line-strong px-2.5 py-0.5 text-xs font-semibold text-ink-subtle">
          <Lock size={11} aria-hidden="true" /> Locked
        </span>
      ) : seen ? (
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold text-canvas ${style.bar}`}>{style.label}</span>
      ) : (
        <span className="rounded-full border border-line-strong px-2.5 py-0.5 text-xs font-semibold text-ink-subtle">New</span>
      )}
    </li>
  )
}

export default function TopicLevelsTile({ topics, highlight }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const sorted = sortTopics(topics)
  const practised = topics.filter(t => t.evidence_count > 0).length
  const shown = open ? sorted : sorted.slice(0, COLLAPSED)

  return (
    <section className="tile flex h-full flex-col p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Topic levels</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Where you stand</h2>
        </div>
        <span className="rounded-full bg-ink px-3 py-1 font-mono text-xs font-medium text-canvas">
          {practised} of {topics.length} practised
        </span>
      </div>
      <p className="mt-2 max-w-[60ch] text-[13px] leading-relaxed text-ink-subtle">
        A topic level is how sure we are that you know a topic. It moves with every graded answer. Weakest topics are listed first.
      </p>

      {practised === 0 ? (
        <div className="mt-6 flex flex-1 flex-col items-start justify-center gap-4 rounded-2xl border border-dashed border-line-strong p-6">
          <p className="text-sm text-ink-muted">No topic levels yet. Answer your first practice question and they start filling in.</p>
          <Button size="sm" icon={Target} onClick={() => navigate('/practice')}>Start practice</Button>
        </div>
      ) : (
        <>
          <ul className="mt-3 divide-y divide-line">
            {shown.map(t => <TopicRow key={t.topic} topic={t} current={t.topic === highlight} />)}
          </ul>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
            <p className="flex items-center gap-1.5 text-xs text-ink-subtle">
              <Lock size={12} /> Locked topics open when the topics before them reach 40%.
            </p>
            {sorted.length > COLLAPSED && (
              <button
                type="button"
                onClick={() => setOpen(v => !v)}
                aria-expanded={open}
                className="flex h-9 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium text-ink-muted hover:bg-white/[0.06] hover:text-ink"
              >
                {open ? 'Show fewer' : `Show all ${sorted.length}`}
                <ChevronDown size={14} className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
              </button>
            )}
          </div>
        </>
      )}
    </section>
  )
}
