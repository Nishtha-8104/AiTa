import { BookOpenText, Bug, Code2, HelpCircle, ListChecks, Target } from 'lucide-react'
import { BAND_STYLE, ITEM_TYPE_LABELS, topicLabel } from '../learning/labels'
import Chip from '../ui/Chip'
import Skeleton from '../ui/Skeleton'
import BusyNote from '../ui/BusyNote'
import LevelBar from '../ui/LevelBar'
import McqView from './McqView'
import DebugView from './DebugView'
import CodingView from './CodingView'
import TheoryView from './TheoryView'

const TYPE = {
  diagnostic: { icon: ListChecks, tone: 'aqua' },
  mcq: { icon: HelpCircle, tone: 'aqua' },
  coding: { icon: Code2, tone: 'mint' },
  debug: { icon: Bug, tone: 'pink' },
  theory: { icon: BookOpenText, tone: 'sun' },
}
const DIFF_TONE = { easy: 'mint', medium: 'sun', hard: 'coral' }

export const VIEWS = { diagnostic: McqView, mcq: McqView, debug: DebugView, coding: CodingView, theory: TheoryView }
export const NARROW_TYPES = ['mcq', 'diagnostic', 'theory']

export const LOADING_STEPS = [
  { after: 0, text: 'Picking your next question…' },
  { after: 6, text: 'Writing a fresh problem for you…' },
  { after: 30, text: 'Still writing. New problems can take up to a minute…' },
]

export function ItemHeader({ next, topic }) {
  const type = TYPE[next.item_type] || { icon: Target, tone: 'neutral' }
  const band = topic && topic.evidence_count > 0 ? topic.band : 'unseen'
  return (
    <section className="tile flex flex-col gap-4 p-5 sm:p-6 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={type.tone} icon={type.icon}>{ITEM_TYPE_LABELS[next.item_type] || next.item_type}</Chip>
          <Chip>{topicLabel(next.topic)}</Chip>
          {next.difficulty && <Chip tone={DIFF_TONE[next.difficulty] || 'neutral'}>{next.difficulty}</Chip>}
        </div>
        {next.reason && (
          <p className="mt-3 max-w-[75ch] text-sm leading-relaxed text-ink-muted">
            <span className="font-medium text-ink">Why this: </span>{next.reason}
          </p>
        )}
      </div>
      {topic && (
        <div className="w-full shrink-0 rounded-2xl border border-line bg-tile-2 px-4 py-3 md:w-56">
          <div className="flex items-baseline justify-between gap-2 text-xs">
            <span className="text-ink-subtle">Topic level</span>
            <span className={BAND_STYLE[band].text}>
              {BAND_STYLE[band].label}
              {topic.evidence_count > 0 && <span className="ml-1.5 font-mono text-ink">{Math.round(topic.mastery * 100)}%</span>}
            </span>
          </div>
          <LevelBar value={topic.evidence_count > 0 ? topic.mastery : 0} band={band} className="mt-2" />
        </div>
      )}
    </section>
  )
}

export function LoadingState() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true">
      <div className="tile space-y-3 p-6">
        <div className="flex gap-2">
          <Skeleton className="h-6 w-32 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
        <Skeleton className="h-4 w-3/5" />
      </div>
      <BusyNote active steps={LOADING_STEPS} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[5fr_7fr]">
        <div className="tile space-y-3 p-6">
          {[90, 75, 82, 40].map(w => <Skeleton key={w} className="h-3.5" style={{ width: `${w}%` }} />)}
        </div>
        <div className="tile h-[380px] p-6"><Skeleton className="h-full w-full rounded-2xl" /></div>
      </div>
    </div>
  )
}
