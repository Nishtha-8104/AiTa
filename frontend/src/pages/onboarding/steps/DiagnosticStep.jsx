import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Code2, Eye, HelpCircle, PenLine, Play, RefreshCw } from 'lucide-react'
import { onboardingAPI, getErrorMessage } from '../../../utils/api'
import { StepTitle } from '../../../components/onboarding/StepControls'
import Button from '../../../components/ui/Button'
import Chip from '../../../components/ui/Chip'
import Skeleton from '../../../components/ui/Skeleton'
import { topicLabel } from '../../../components/learning/labels'
import TopicMap from '../../../components/onboarding/TopicMap'
import RevealPanel from '../../../components/onboarding/RevealPanel'
import PredictOutputView from '../../../components/onboarding/items/PredictOutputView'
import FindBugView from '../../../components/onboarding/items/FindBugView'
import FillBlankView from '../../../components/onboarding/items/FillBlankView'
import WriteCodeView from '../../../components/onboarding/items/WriteCodeView'
import TheoryView from '../../../components/onboarding/items/TheoryView'

const VIEWS = {
  predict_output: PredictOutputView,
  find_bug: FindBugView,
  fill_blank: FillBlankView,
  write_code: WriteCodeView,
  theory: TheoryView,
}

const KIND_LABEL = {
  predict_output: 'Predict the output',
  find_bug: 'Find the bug',
  fill_blank: 'Fill the blank',
  write_code: 'Write the code',
  theory: 'Explain in words',
}

const INTRO_POINTS = [
  { icon: Code2, tone: 'bg-pop-aqua/15 text-pop-aqua', text: 'Code questions: predict the output, find a bug, fill a blank.' },
  { icon: Eye, tone: 'bg-pop-mint/15 text-pop-mint', text: "After each one you'll see the right answer and why." },
  { icon: PenLine, tone: 'bg-pop-pink/15 text-pop-pink', text: 'The last few are short written answers, reviewed together at the end.' },
  { icon: HelpCircle, tone: 'bg-pop-sun/15 text-pop-sun', text: 'Not sure? Press "I don\'t know". It simply counts as not known yet.' },
]

const MAP_NOTE = 'From your code answers so far. Your written answers can still move a topic on your profile.'
const MS_CAP = 3_600_000
const THEORY_COUNT = 3

export default function DiagnosticStep({ initial, onSaved, onConflict, onProgress, api = onboardingAPI, intro, written = true }) {
  const [started, setStarted] = useState(!!initial)
  const [diag, setDiag] = useState(null)
  const [map, setMap] = useState(initial?.topic_map || {})
  const [reveal, setReveal] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const inFlight = useRef(false)
  const shownAt = useRef(0)
  const upcoming = useRef(null)
  const moveFocus = useRef(false)
  const headingRef = useRef(null)

  useEffect(() => {
    if (!moveFocus.current || reveal || !diag) return
    moveFocus.current = false
    window.scrollTo(0, 0)
    headingRef.current?.focus({ preventScroll: true })
  }, [diag, reveal])

  const show = (d) => {
    setMap(d.topic_map)
    onProgress?.(d)
    if (d.done || !d.item) {
      onSaved({ current_step: 'card', diagnostic: d, card: null })
      return
    }
    shownAt.current = Date.now()
    setDiag(d)
  }

  const run = async (task) => {
    if (inFlight.current) return
    inFlight.current = true
    setBusy(true)
    try {
      await task()
    } finally {
      inFlight.current = false
      setBusy(false)
    }
  }

  const fetchNext = async () => {
    setLoadError(null)
    try {
      const { data } = await api.next()
      show(data)
    } catch (err) {
      if (err?.response?.status === 409) {
        toast.error(getErrorMessage(err, 'Finish the earlier steps first.'))
        onConflict?.()
        return
      }
      setLoadError(getErrorMessage(err, 'Could not load the next question.'))
    }
  }

  useEffect(() => {
    if (started) run(fetchNext)
  }, [started])

  const submit = (answer) => run(async () => {
    const item = diag.item
    const ms = Math.min(MS_CAP, Math.max(0, Date.now() - shownAt.current))
    try {
      const { data } = await api.answer(item.id, answer, ms)
      if (data.saved_only) {
        toast.success('Saved — reviewed at the end of this block')
        moveFocus.current = true
        show(data.next)
      } else if (item.kind === 'theory') {
        upcoming.current = data.next
        setReveal({ kind: 'theory', items: data.theory_reveals, expectedCount: THEORY_COUNT })
      } else if (data.reveal) {
        upcoming.current = data.next
        setReveal({ kind: item.kind, ...data.reveal, score: data.score })
      } else {
        moveFocus.current = true
        show(data.next)
      }
    } catch (err) {
      const status = err?.response?.status
      if (status === 409) {
        toast.error('That question is out of date. Loading the current one.')
        await fetchNext()
      } else {
        toast.error(getErrorMessage(err, 'Could not submit your answer. Please try again.'))
      }
    }
  })

  const handleContinue = () => {
    setReveal(null)
    moveFocus.current = true
    show(upcoming.current)
  }

  if (!started) {
    return (
      <div className="tile mx-auto max-w-2xl p-6 sm:p-10">
        {intro || (
          <>
            <StepTitle eyebrow="Starting check" title="A short check"
              subtitle="Up to 12 questions in your language. There is no time limit. It starts easy and adapts to your answers." />
            <ul className="mb-8 space-y-3">
              {INTRO_POINTS.map(({ icon: Icon, tone, text }) => (
                <li key={text} className="flex items-start gap-3 text-sm leading-relaxed text-ink-muted">
                  <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${tone}`}><Icon size={15} /></span>
                  <span className="pt-1.5">{text}</span>
                </li>
              ))}
            </ul>
          </>
        )}
        <Button size="lg" icon={Play} onClick={() => setStarted(true)}>Start the check</Button>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="tile mx-auto flex max-w-2xl flex-col items-start gap-4 p-6">
        <p className="text-sm text-ink-muted">{loadError} Check your connection, then try again.</p>
        <Button variant="secondary" icon={RefreshCw} onClick={() => run(fetchNext)} disabled={busy}>Try again</Button>
      </div>
    )
  }

  if (!diag) {
    return (
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_300px]" aria-busy="true" aria-label="Loading the question">
        <div className="tile space-y-4 p-6 sm:p-8">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-12 w-full rounded-2xl" />
        </div>
        <div className="tile h-72 p-5"><Skeleton className="h-full w-full rounded-2xl" /></div>
      </div>
    )
  }

  const { item } = diag
  const View = VIEWS[item.kind]

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_300px] lg:items-start">
      <div className="tile min-w-0 p-6 sm:p-8">
        {reveal ? (
          <RevealPanel reveal={reveal} onContinue={handleContinue} />
        ) : (
          <div key={item.id} className="motion-safe:animate-rise">
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <h2 ref={headingRef} tabIndex={-1} className="mr-1 text-xl font-semibold tracking-tight text-ink focus:outline-none">
                {KIND_LABEL[item.kind] || 'Question'}
              </h2>
              {diag.phase === 'warmup' && <Chip tone="mint">warm-up</Chip>}
              <Chip>{topicLabel(item.topic)}</Chip>
            </div>
            {item.kind === 'theory' && (
              <p className="mb-4 text-xs text-ink-subtle">
                Written answers are saved one by one and reviewed together after the last one.
              </p>
            )}
            {View ? (
              <View item={item} onSubmit={submit} disabled={busy} />
            ) : (
              <div className="flex flex-col items-start gap-4">
                <p className="text-sm text-ink-muted">This question can't be shown here.</p>
                <Button variant="secondary" onClick={() => run(fetchNext)} disabled={busy}>Continue</Button>
              </div>
            )}
          </div>
        )}
      </div>

      <aside className="lg:sticky lg:top-8">
        <TopicMap states={map} note={written ? MAP_NOTE : null} />
      </aside>
    </div>
  )
}
