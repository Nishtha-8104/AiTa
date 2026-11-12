import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ChevronDown, Flag, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { assessmentAPI, getErrorMessage, practiceSessionAPI, profileAPI } from '../utils/api'
import AppShell from '../components/ui/AppShell'
import Button from '../components/ui/Button'
import TopicLevelsTile from '../components/dashboard/TopicLevelsTile'
import { ItemHeader, LoadingState, NARROW_TYPES, VIEWS } from '../components/practice/ItemFrame'

function AllLevels({ topics, current }) {
  const [open, setOpen] = useState(false)
  if (!topics) return null
  return (
    <section className="flex flex-col gap-3">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="flex h-11 items-center gap-2 self-start rounded-full border border-line-strong px-4 text-sm font-medium text-ink-muted hover:bg-white/[0.04] hover:text-ink"
      >
        {open ? 'Hide' : 'Show'} all topic levels
        <ChevronDown size={15} className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="motion-safe:animate-rise">
          <TopicLevelsTile topics={topics} highlight={current} />
        </div>
      )}
    </section>
  )
}

export default function PracticePage() {
  const navigate = useNavigate()
  const [next, setNext] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [graded, setGraded] = useState(false)
  const [topics, setTopics] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [session, setSession] = useState(null)
  const [finishing, setFinishing] = useState(false)
  const nextRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setGraded(false)
    window.scrollTo({ top: 0 })
    try {
      const { data } = await assessmentAPI.next()
      setNext(data)
      practiceSessionAPI.current().then(({ data }) => setSession(data)).catch(() => {})
    } catch (err) {
      if (err?.response?.status === 428) {
        navigate('/language-check', { replace: true })
        return
      }
      setError(getErrorMessage(err, "Couldn't load your next question."))
    } finally {
      setLoading(false)
    }
  }, [navigate])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    profileAPI.getMastery().then(({ data }) => setTopics(data.topics)).catch(() => {})
    practiceSessionAPI.current().then(({ data }) => setSession(data)).catch(() => {})
  }, [refreshKey])

  const finish = async () => {
    setFinishing(true)
    try {
      await practiceSessionAPI.finish(session.id)
      navigate(`/practice/session/${session.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't finish the session. Try again in a moment."))
      setFinishing(false)
      setRefreshKey(k => k + 1)
    }
  }

  const onGraded = () => {
    setGraded(true)
    setRefreshKey(k => k + 1)
  }

  useEffect(() => {
    if (graded) nextRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [graded])

  const View = next && VIEWS[next.item_type]
  const topic = next && topics?.find(t => t.topic === next.topic)

  return (
    <AppShell title="Practice">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-5">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Practice</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink md:text-[32px]">One question at a time</h1>
          </div>
          <div className="flex flex-col items-start gap-3 sm:items-end">
            <p className="max-w-[46ch] text-sm text-ink-subtle">Each answer is graded, moves your topic level, and picks what comes next.</p>
            {session?.id && (
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono text-xs text-ink-muted">{session.graded_count} answered this session</span>
                <Button size="sm" variant="secondary" icon={Flag} busy={finishing} onClick={finish}>Finish session</Button>
              </div>
            )}
          </div>
        </header>

        {loading && <LoadingState />}

        {error && !loading && (
          <section className="tile flex flex-col items-start gap-4 p-6">
            <p className="text-sm text-ink-muted">{error} Check your connection, then try again.</p>
            <Button icon={RefreshCw} onClick={load}>Try again</Button>
          </section>
        )}

        {next && !loading && View && (
          <div className={`flex w-full flex-col gap-5 ${NARROW_TYPES.includes(next.item_type) ? 'mx-auto max-w-3xl' : ''}`}>
            <ItemHeader next={next} topic={topic} />
            <div className="motion-safe:animate-rise">
              <View key={`${next.item_type}-${next.item.id}`} item={next.item} onGraded={onGraded} />
            </div>
            {graded && (
              <div ref={nextRef} className="flex flex-col items-start justify-between gap-3 rounded-tile border border-line-strong bg-tile-2 p-5 motion-safe:animate-rise sm:flex-row sm:items-center">
                <p className="text-sm text-ink-muted">Graded. Your topic level is updated.</p>
                <Button size="lg" iconRight={ArrowRight} onClick={load}>Next question</Button>
              </div>
            )}
          </div>
        )}

        {!loading && <AllLevels topics={topics} current={next?.topic} />}
      </div>
    </AppShell>
  )
}
