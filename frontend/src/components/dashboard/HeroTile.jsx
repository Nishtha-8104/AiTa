import { useNavigate } from 'react-router-dom'
import { ArrowRight, Shapes } from 'lucide-react'
import Button from '../ui/Button'
import Skeleton from '../ui/Skeleton'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function nextFocus(topics) {
  const pct = t => Math.round(t.mastery * 100)
  const low = topics
    .filter(t => t.unlocked && t.evidence_count > 0 && t.band !== 'mastered')
    .sort((a, b) => a.mastery - b.mastery)[0]
  if (low) return { label: low.label, text: `is your lowest topic level right now, at ${pct(low)}%.` }
  const fresh = topics.find(t => t.unlocked && t.evidence_count === 0)
  if (fresh) return { label: fresh.label, text: "is open and you haven't practised it yet." }
  return null
}

export default function HeroTile({ user, topics, loading }) {
  const navigate = useNavigate()
  const firstName = user?.full_name?.split(' ')[0] || user?.username
  const focus = topics ? nextFocus(topics) : null
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <section className="tile relative grid gap-6 p-6 sm:p-8">
      <div className="flex min-w-0 flex-col">
        <p className="eyebrow">{today}</p>
        <h1 className="mt-3 text-3xl font-semibold leading-[1.1] tracking-tight text-ink md:text-[40px]">
          {greeting()}{firstName ? `, ${firstName}` : ''}.
        </h1>
        <div className="mt-3 min-h-[48px] max-w-[52ch] text-[15px] leading-relaxed text-ink-subtle">
          {loading ? (
            <div className="space-y-2 pt-1">
              <Skeleton className="h-3.5 w-4/5" />
              <Skeleton className="h-3.5 w-1/2" />
            </div>
          ) : focus ? (
            <p><span className="font-medium text-ink">{focus.label}</span> {focus.text} One practice question at a time moves it up.</p>
          ) : (
            <p>Your open topics are all at Mastered. Practice keeps them there and opens new ones.</p>
          )}
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button size="lg" iconRight={ArrowRight} onClick={() => navigate('/practice')}>
            Continue practice
          </Button>
          <Button size="lg" variant="ghost" icon={Shapes} onClick={() => navigate('/topics')}>
            Pick a topic
          </Button>
        </div>
      </div>
    </section>
  )
}
