import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Play, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { getErrorMessage, topicPracticeAPI } from '../utils/api'
import { languageLabel, topicLabel } from '../components/learning/labels'
import LessonMarkdown from '../components/learning/LessonMarkdown'
import AppShell from '../components/ui/AppShell'
import Button from '../components/ui/Button'
import Skeleton from '../components/ui/Skeleton'

export default function TopicExplanationPage() {
  const { topic } = useParams()
  const navigate = useNavigate()
  const [lesson, setLesson] = useState(null)
  const [state, setState] = useState('loading')
  const [starting, setStarting] = useState(false)

  const load = useCallback(() => {
    setState('loading')
    topicPracticeAPI.explanation(topic)
      .then(({ data }) => { setLesson(data); setState('ready') })
      .catch(err => setState(err?.response?.status === 404 ? 'missing' : 'error'))
  }, [topic])
  useEffect(load, [load])

  const start = async () => {
    setStarting(true)
    try {
      await topicPracticeAPI.start(topic)
      navigate(`/topics/${topic}/practice`)
    } catch (err) {
      if (err?.response?.status === 428) {
        navigate('/language-check', { replace: true })
        return
      }
      toast.error(getErrorMessage(err, "Couldn't start the practice. Try again in a moment."))
      setStarting(false)
    }
  }

  const startButton = (
    <Button size="lg" icon={Play} busy={starting} onClick={start}>Start 10 questions</Button>
  )

  return (
    <AppShell title={topicLabel(topic)}>
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <Link to="/topics" className="inline-flex items-center gap-1.5 self-start text-sm text-ink-subtle hover:text-ink">
          <ArrowLeft size={15} /> All topics
        </Link>
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">{lesson ? languageLabel(lesson.language) : 'Topic practice'}</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink md:text-[32px]">{topicLabel(topic)}</h1>
          </div>
          {state !== 'loading' && startButton}
        </header>

        {state === 'loading' && (
          <section className="tile space-y-3 p-6" aria-busy="true">
            {[70, 95, 88, 60, 92, 40].map(w => <Skeleton key={w} className="h-3.5" style={{ width: `${w}%` }} />)}
          </section>
        )}

        {state === 'error' && (
          <section className="tile flex flex-col items-start gap-4 p-6">
            <p className="text-sm text-ink-muted">Couldn't load the explanation. Check your connection, then try again.</p>
            <Button icon={RefreshCw} onClick={load}>Try again</Button>
          </section>
        )}

        {state === 'missing' && (
          <section className="tile p-6">
            <p className="text-sm text-ink-muted">The explanation for this topic isn't written yet. You can still start the questions.</p>
          </section>
        )}

        {state === 'ready' && (
          <>
            <article className="tile p-6 sm:p-8">
              <LessonMarkdown markdown={lesson.markdown} />
            </article>
            <div className="flex flex-col items-start justify-between gap-3 rounded-tile border border-line-strong bg-tile-2 p-5 sm:flex-row sm:items-center">
              <p className="text-sm text-ink-muted">Ready? 10 questions on {topicLabel(topic)}, one at a time.</p>
              {startButton}
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}
