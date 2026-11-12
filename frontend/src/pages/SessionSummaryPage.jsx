import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, Award, BookOpenText, Bug, Code2, HelpCircle, Home, RefreshCw, SearchX, Target, TrendingUp } from 'lucide-react'
import { getErrorMessage, practiceSessionAPI } from '../utils/api'
import { BAND_STYLE, ITEM_TYPE_LABELS, languageLabel, misconceptionLabel, topicLabel } from '../components/learning/labels'
import AppShell from '../components/ui/AppShell'
import PageHeader from '../components/ui/PageHeader'
import Button from '../components/ui/Button'
import Chip from '../components/ui/Chip'
import BusyNote from '../components/ui/BusyNote'
import EmptyState from '../components/ui/EmptyState'
import LevelBar from '../components/ui/LevelBar'
import { SkeletonTile } from '../components/ui/Skeleton'

const TYPES = [
  { key: 'mcq', icon: HelpCircle, tone: 'aqua' },
  { key: 'theory', icon: BookOpenText, tone: 'sun' },
  { key: 'debug', icon: Bug, tone: 'pink' },
  { key: 'coding', icon: Code2, tone: 'mint' },
]

const WRITING_STEPS = [
  { after: 0, text: 'Writing your feedback…' },
  { after: 15, text: 'Still writing. This can take up to a minute…' },
]

const END_NOTE = {
  idle: 'This session closed on its own after 30 minutes with no activity.',
  language_switch: 'This session closed when you switched language.',
  mode_switch: 'This session closed when you started a different kind of practice.',
}

const pct = v => Math.round(v * 100)
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

function duration(s) {
  if (s < 60) return 'under a minute'
  const m = Math.round(s / 60)
  if (m < 60) return `${m} min`
  return `${Math.floor(m / 60)} h ${m % 60} min`
}

function headerLine(wrap) {
  const date = new Date(wrap.started_at).toLocaleString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
  })
  return `${date} · ${duration(wrap.duration_s)} · ${languageLabel(wrap.language)}`
}

function ByType({ byType }) {
  const counts = TYPES.map(t => ({ ...t, ...(byType[t.key] || { tried: 0, solved: 0 }) }))
    .filter(c => c.key !== 'theory' || c.tried > 0)
  const tried = counts.reduce((n, c) => n + c.tried, 0)
  const solved = counts.reduce((n, c) => n + c.solved, 0)
  return (
    <section className="tile p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="eyebrow">What you did</p>
        <span className="font-mono text-xs text-ink-muted">{solved} of {plural(tried, 'item')} solved</span>
      </div>
      <ul className={`mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 ${counts.length === 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
        {counts.map(({ key, icon, tone, tried: t, solved: s }) => (
          <li key={key} className={`rounded-2xl border border-line bg-tile-2 p-4 ${t === 0 ? 'opacity-60' : ''}`}>
            <Chip tone={tone} icon={icon}>{ITEM_TYPE_LABELS[key]}</Chip>
            <p className="mt-3 font-mono text-2xl font-semibold tracking-tight text-ink">
              {s}<span className="text-base text-ink-subtle"> / {t}</span>
            </p>
            <p className="mt-1 text-xs text-ink-subtle">{t === 0 ? 'None this session' : `solved of ${t} tried`}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function TopicChange({ change }) {
  const style = BAND_STYLE[change.band_after] || BAND_STYLE.unseen
  const delta = pct(change.after) - pct(change.before)
  return (
    <li className="py-3.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="min-w-0 truncate text-sm font-medium text-ink">{topicLabel(change.topic)}</span>
        <span className="flex shrink-0 items-center gap-1.5 font-mono text-xs">
          <span className="text-ink-subtle">{pct(change.before)}%</span>
          <ArrowRight size={12} className="text-ink-faint" aria-hidden="true" />
          <span className="sr-only">to</span>
          <span className="text-ink">{pct(change.after)}%</span>
          {delta !== 0 && (
            <span className={`ml-1 ${delta > 0 ? 'text-pop-mint' : 'text-pop-coral'}`}>{delta > 0 ? `+${delta}` : delta}</span>
          )}
        </span>
      </div>
      <LevelBar value={change.after} band={change.band_after} className="mt-2.5" />
      <p className={`mt-1.5 text-xs ${style.text}`}>{style.label}</p>
    </li>
  )
}

function TopicLevels({ topics }) {
  return (
    <section className="tile h-full p-6">
      <p className="eyebrow">Topic levels</p>
      <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">Before and after</h2>
      {topics.length === 0 ? (
        <p className="mt-4 text-[13px] text-ink-subtle">No topic levels moved in this session.</p>
      ) : (
        <ul className="mt-2 divide-y divide-line">
          {topics.map(t => <TopicChange key={t.topic} change={t} />)}
        </ul>
      )}
    </section>
  )
}

function HintsAndMistakes({ hints, mistakes, stuck }) {
  const top = mistakes.slice(0, 3)
  return (
    <section className="tile h-full p-6">
      <p className="eyebrow">Hints used</p>
      <ul className="mt-3 grid grid-cols-4 gap-2">
        {['1', '2', '3', '4'].map(level => (
          <li key={level} className="rounded-xl border border-line bg-tile-2 px-2 py-2.5 text-center">
            <p className="font-mono text-lg font-semibold text-ink">{hints[level] ?? 0}</p>
            <p className="text-[11px] text-ink-subtle">Level {level}</p>
          </li>
        ))}
      </ul>

      <div className="mt-6 border-t border-line pt-5">
        <p className="eyebrow">Most frequent mistakes</p>
        {top.length === 0 ? (
          <p className="mt-3 text-[13px] text-ink-subtle">None recorded in this session.</p>
        ) : (
          <ul className="mt-3 flex flex-wrap gap-2">
            {top.map(m => (
              <li key={m.misconception}>
                <Chip tone="sun">{misconceptionLabel(m.misconception)} <span className="font-mono opacity-80">×{m.count}</span></Chip>
              </li>
            ))}
          </ul>
        )}
      </div>

      {stuck.length > 0 && (
        <p className="mt-5 border-t border-line pt-5 text-[13px] leading-relaxed text-ink-muted">
          <span className="font-medium text-ink">Stuck for a while on: </span>{stuck.map(topicLabel).join(', ')}
        </p>
      )}
    </section>
  )
}

function FeedbackBlock({ wrap, writing, onRetry }) {
  if (writing) return <BusyNote active steps={WRITING_STEPS} note="Your results above are already saved." />
  if (wrap.feedback_status === 'ready' && wrap.feedback) {
    const { summary, work_on_next: next } = wrap.feedback
    return (
      <section className="tile p-6">
        <p className="eyebrow">Feedback</p>
        <p className="mt-3 max-w-[75ch] whitespace-pre-line text-[15px] leading-relaxed text-ink-muted">{summary}</p>
        {next.length > 0 && (
          <div className="mt-5 border-t border-line pt-5">
            <p className="eyebrow">Work on next</p>
            <ul className="mt-3 space-y-2.5">
              {next.map(item => (
                <li key={item} className="flex gap-2.5 text-sm leading-relaxed text-ink">
                  <Target size={16} className="mt-0.5 shrink-0 text-pop-mint" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    )
  }
  if (wrap.feedback_status === 'unavailable' || wrap.feedback_status === 'blocked') {
    return (
      <section className="tile flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="eyebrow">Feedback</p>
          <p className="mt-2 text-sm text-ink-muted">Written feedback isn't available right now. Your results above are still saved.</p>
        </div>
        <Button size="sm" variant="secondary" icon={RefreshCw} disabled={writing} onClick={onRetry}>Try again</Button>
      </section>
    )
  }
  return null
}

function Awards({ awards }) {
  const points = awards.reduce((n, a) => n + (a.points || 0), 0)
  const levelUps = awards.filter(a => a.kind === 'level_up')
  const badges = awards.filter(a => a.kind === 'badge')
  return (
    <section className="tile p-6">
      <p className="eyebrow">Earned this session</p>
      {awards.length === 0 ? (
        <p className="mt-3 text-[13px] text-ink-subtle">No new points this session.</p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-[auto_minmax(0,1fr)] sm:gap-8">
          <div>
            <p className="font-mono text-3xl font-semibold tracking-tight text-ink">+{points.toLocaleString('en-IN')}</p>
            <p className="mt-1 text-xs text-ink-subtle">Points</p>
          </div>
          <div className="space-y-4">
            {levelUps.length > 0 && (
              <ul className="space-y-2">
                {levelUps.map((a, i) => (
                  <li key={`${a.code}-${i}`} className="flex items-center gap-2 text-sm text-ink">
                    <TrendingUp size={15} className="shrink-0 text-pop-mint" aria-hidden="true" /> {a.message}
                  </li>
                ))}
              </ul>
            )}
            {badges.length > 0 && (
              <ul className="flex flex-wrap gap-2">
                {badges.map((b, i) => (
                  <li key={`${b.code}-${i}`} title={b.message}><Chip tone="sun" icon={Award}>{b.title}</Chip></li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

function LoadingState() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-6 md:gap-5" aria-busy="true">
      <SkeletonTile className="h-[200px] md:col-span-6" lines={2} />
      <SkeletonTile className="h-[320px] md:col-span-4" lines={5} />
      <SkeletonTile className="h-[320px] md:col-span-2" lines={3} />
    </div>
  )
}

export default function SessionSummaryPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [wrap, setWrap] = useState(null)
  const [error, setError] = useState(null)
  const [writing, setWriting] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const asked = useRef(null)

  useEffect(() => {
    let cancelled = false
    setWrap(null)
    setError(null)
    practiceSessionAPI.get(id)
      .then(({ data }) => { if (!cancelled) setWrap(data) })
      .catch(err => {
        if (cancelled) return
        setError(err?.response?.status === 404 ? 'missing' : getErrorMessage(err, "Couldn't load this session."))
      })
    return () => { cancelled = true }
  }, [id, attempt])

  const write = useCallback(async (retry) => {
    setWriting(true)
    try {
      const { data } = await practiceSessionAPI.feedback(id, retry)
      setWrap(data)
    } catch {
      setWrap(w => w && { ...w, feedback_status: 'unavailable' })
    } finally {
      setWriting(false)
    }
  }, [id])

  // StrictMode re-runs effects; the ref keeps it to one LLM call per session
  useEffect(() => {
    if (!wrap || wrap.feedback_status !== 'none' || asked.current === wrap.id) return
    asked.current = wrap.id
    write(false)
  }, [wrap, write])

  const actions = (
    <>
      <Button size="lg" iconRight={ArrowRight} onClick={() => navigate('/practice')}>Keep practising</Button>
      <Button size="lg" variant="secondary" icon={Home} onClick={() => navigate('/dashboard')}>Home</Button>
    </>
  )

  return (
    <AppShell title="Session summary">
      <div className="mx-auto flex max-w-[1180px] flex-col gap-5">
        <PageHeader
          eyebrow={wrap?.topic ? 'Topic practice' : 'Practice'}
          title={wrap?.topic ? `${topicLabel(wrap.topic)} summary` : 'Session summary'}
          description={wrap ? headerLine(wrap) : undefined}
        />

        {error === 'missing' && (
          <EmptyState
            icon={SearchX}
            title="This session isn't ready to view"
            body="It may still be open, or it belongs to someone else. Finish a session from Practice to see its summary."
            action={<div className="flex flex-wrap gap-2">{actions}</div>}
          />
        )}

        {error && error !== 'missing' && (
          <section className="tile flex flex-col items-start gap-4 p-6">
            <p className="text-sm text-ink-muted">{error} Check your connection, then try again.</p>
            <Button icon={RefreshCw} onClick={() => setAttempt(a => a + 1)}>Try again</Button>
          </section>
        )}

        {!wrap && !error && <LoadingState />}

        {wrap && (
          <>
            {END_NOTE[wrap.end_reason] && <p className="-mt-2 text-[13px] text-ink-subtle">{END_NOTE[wrap.end_reason]}</p>}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-6 md:gap-5">
              <div className="md:col-span-6 motion-safe:animate-rise">
                <ByType byType={wrap.by_type} />
              </div>
              <div className="md:col-span-4 motion-safe:animate-rise [animation-delay:70ms]">
                <TopicLevels topics={wrap.topics} />
              </div>
              <div className="md:col-span-2 motion-safe:animate-rise [animation-delay:140ms]">
                <HintsAndMistakes hints={wrap.hints} mistakes={wrap.mistakes} stuck={wrap.stuck_topics} />
              </div>
            </div>

            <FeedbackBlock wrap={wrap} writing={writing} onRetry={() => write(true)} />

            {wrap.awards && <Awards awards={wrap.awards} />}

            <div className="flex flex-wrap gap-3 pt-1">{actions}</div>
          </>
        )}
      </div>
    </AppShell>
  )
}
