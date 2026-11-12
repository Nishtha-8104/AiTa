import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Flag, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { getErrorMessage, practiceSessionAPI, profileAPI, topicPracticeAPI } from '../utils/api'
import { topicLabel } from '../components/learning/labels'
import AppShell from '../components/ui/AppShell'
import Button from '../components/ui/Button'
import { ItemHeader, LoadingState, NARROW_TYPES, VIEWS } from '../components/practice/ItemFrame'

function Progress({ position, total }) {
  return (
    <div className="flex min-w-[180px] flex-col gap-2">
      <span className="font-mono text-xs text-ink-muted">Question {position} of {total}</span>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={position}>
        <div className="h-full rounded-full bg-ink transition-[width] duration-500" style={{ width: `${(position / total) * 100}%` }} />
      </div>
    </div>
  )
}

export default function TopicRunPage() {
  const { topic } = useParams()
  const navigate = useNavigate()
  const [step, setStep] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [graded, setGraded] = useState(false)
  const [level, setLevel] = useState(null)
  const [finishing, setFinishing] = useState(false)
  const nextRef = useRef(null)

  const finish = useCallback(async (sessionId) => {
    setFinishing(true)
    try {
      await practiceSessionAPI.finish(sessionId)
      navigate(`/practice/session/${sessionId}`)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't finish the practice. Try again in a moment."))
      setFinishing(false)
    }
  }, [navigate])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setGraded(false)
    window.scrollTo({ top: 0 })
    try {
      const { data } = await topicPracticeAPI.next()
      if (!data.done && data.topic !== topic) {
        navigate(`/topics/${data.topic}/practice`, { replace: true })
        return
      }
      setStep(data)
    } catch (err) {
      if (err?.response?.status === 404) {
        navigate(`/topics/${topic}`, { replace: true })
        return
      }
      setError(getErrorMessage(err, "Couldn't load your next question."))
    } finally {
      setLoading(false)
    }
  }, [navigate, topic])

  useEffect(() => { load() }, [load])

  const refreshLevel = useCallback(() => {
    profileAPI.getMastery()
      .then(({ data }) => setLevel(data.topics.find(t => t.topic === topic) || null))
      .catch(() => {})
  }, [topic])

  useEffect(() => { refreshLevel() }, [refreshLevel])

  useEffect(() => {
    if (graded) nextRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [graded])

  const onGraded = () => {
    setGraded(true)
    refreshLevel()
  }

  const View = step && !step.done && VIEWS[step.item_type]
  const last = step && step.position >= step.total

  return (
    <AppShell title={`${topicLabel(topic)} practice`}>
      <div className="mx-auto flex max-w-[1320px] flex-col gap-5">
        <Link to={`/topics/${topic}`} className="inline-flex items-center gap-1.5 self-start text-sm text-ink-subtle hover:text-ink">
          <ArrowLeft size={15} /> Back to the explanation
        </Link>
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Topic practice</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink md:text-[32px]">{topicLabel(topic)}</h1>
          </div>
          {step && !step.done && <Progress position={step.position} total={step.total} />}
        </header>

        {loading && <LoadingState />}

        {error && !loading && (
          <section className="tile flex flex-col items-start gap-4 p-6">
            <p className="text-sm text-ink-muted">{error} Check your connection, then try again.</p>
            <Button icon={RefreshCw} onClick={load}>Try again</Button>
          </section>
        )}

        {step?.done && !loading && (
          <section className="tile flex flex-col items-start gap-4 p-6">
            {step.total > 0 ? (
              <>
                <p className="text-sm text-ink-muted">That's all {step.total} questions. See how your topic level moved.</p>
                <Button size="lg" icon={Flag} busy={finishing} onClick={() => finish(step.session_id)}>See your summary</Button>
              </>
            ) : (
              <p className="text-sm text-ink-muted">There are no questions on {topicLabel(topic)} in your language yet.</p>
            )}
          </section>
        )}

        {View && !loading && (
          <div className={`flex w-full flex-col gap-5 ${NARROW_TYPES.includes(step.item_type) ? 'mx-auto max-w-3xl' : ''}`}>
            <ItemHeader next={step} topic={level} />
            <div className="motion-safe:animate-rise">
              <View key={`${step.item_type}-${step.item.id}`} item={step.item} onGraded={onGraded} />
            </div>
            {graded && (
              <div ref={nextRef} className="flex flex-col items-start justify-between gap-3 rounded-tile border border-line-strong bg-tile-2 p-5 motion-safe:animate-rise sm:flex-row sm:items-center">
                <p className="text-sm text-ink-muted">Graded.</p>
                {last
                  ? <Button size="lg" icon={Flag} busy={finishing} onClick={() => finish(step.session_id)}>See your summary</Button>
                  : <Button size="lg" iconRight={ArrowRight} onClick={load}>Next question</Button>}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}
