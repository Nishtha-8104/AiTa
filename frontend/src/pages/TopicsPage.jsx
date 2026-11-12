import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, RefreshCw } from 'lucide-react'
import { getErrorMessage, profileAPI } from '../utils/api'
import { BAND_STYLE, languageLabel } from '../components/learning/labels'
import { useAuth } from '../hooks/useAuth'
import AppShell from '../components/ui/AppShell'
import Button from '../components/ui/Button'
import LevelBar from '../components/ui/LevelBar'
import Skeleton from '../components/ui/Skeleton'

function TopicCard({ topic }) {
  const seen = topic.evidence_count > 0
  const band = seen ? topic.band : 'unseen'
  const style = BAND_STYLE[band] || BAND_STYLE.unseen
  return (
    <Link
      to={`/topics/${topic.topic}`}
      className="tile group flex flex-col gap-4 p-5 transition-colors hover:border-ink-faint focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-[17px] font-semibold tracking-tight text-ink">{topic.label}</h2>
        <ArrowRight size={17} className="mt-1 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
      </div>
      <div>
        <div className="flex items-baseline justify-between gap-2 text-xs">
          <span className={style.text}>{style.label}</span>
          {seen && <span className="font-mono text-ink">{Math.round(topic.mastery * 100)}%</span>}
        </div>
        <LevelBar value={seen ? topic.mastery : 0} band={band} className="mt-2" />
      </div>
    </Link>
  )
}

export default function TopicsPage() {
  const { user } = useAuth()
  const [topics, setTopics] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setError(null)
    profileAPI.getMastery()
      .then(({ data }) => setTopics(data.topics))
      .catch(err => setError(getErrorMessage(err, "Couldn't load your topics.")))
  }, [])
  useEffect(load, [load])

  return (
    <AppShell title="Topic practice">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Topic practice</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink md:text-[32px]">Pick a topic to work on</h1>
          </div>
          <p className="max-w-[52ch] text-sm text-ink-subtle">
            Read a short explanation in {languageLabel(user?.preferred_language)}, then answer 10 questions on that topic: theory, multiple choice, debugging and one coding problem. Every answer moves your topic level.
          </p>
        </header>

        {error && (
          <section className="tile flex flex-col items-start gap-4 p-6">
            <p className="text-sm text-ink-muted">{error} Check your connection, then try again.</p>
            <Button icon={RefreshCw} onClick={load}>Try again</Button>
          </section>
        )}

        {!topics && !error && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
            {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-[118px] rounded-tile" />)}
          </div>
        )}

        {topics && (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {topics.map(t => <li key={t.topic}><TopicCard topic={t} /></li>)}
          </ul>
        )}

        <p className="text-sm text-ink-subtle">
          Only want a coding problem? <Link to="/code-help" className="text-ink underline underline-offset-2">Write one on any topic</Link>.
        </p>
      </div>
    </AppShell>
  )
}
