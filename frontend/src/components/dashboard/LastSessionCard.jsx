import { useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { topicLabel } from '../learning/labels'
import Button from '../ui/Button'
import Chip from '../ui/Chip'

const SHOWN_TOPICS = 4
const END_NOTE = {
  language_switch: ended => `It ended when you switched language on ${ended}.`,
  mode_switch: ended => `It ended when you started a different kind of practice on ${ended}.`,
}

export default function LastSessionCard({ session }) {
  const navigate = useNavigate()
  const { solved, topics } = session
  const ended = new Date(session.ended_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
  const extra = topics.length - SHOWN_TOPICS

  return (
    <section className="tile flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="eyebrow">Your last session</p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">
          {solved > 0 ? `You solved ${solved} ${solved === 1 ? 'item' : 'items'}.` : 'Your summary is ready.'}
        </h2>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-subtle">
          {END_NOTE[session.end_reason] ? END_NOTE[session.end_reason](ended) : `It closed on its own on ${ended}.`} See how your topic levels moved.
        </p>
        {topics.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {topics.slice(0, SHOWN_TOPICS).map(t => <li key={t}><Chip>{topicLabel(t)}</Chip></li>)}
            {extra > 0 && <li><Chip>+{extra} more</Chip></li>}
          </ul>
        )}
      </div>
      <Button iconRight={ArrowRight} onClick={() => navigate(`/practice/session/${session.id}`)} className="self-start sm:self-auto">
        See summary
      </Button>
    </section>
  )
}
