import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowRight, Award, Compass, Lightbulb, Pencil, RefreshCw, Save } from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth'
import { onboardingAPI, getErrorMessage } from '../../../utils/api'
import { topicLabel } from '../../../components/learning/labels'
import BandSummary, { conceptLine } from '../../../components/onboarding/BandSummary'
import {
  AboutFields, LearningFields, aboutForm, aboutPayload, aboutComplete, learningForm, learningComplete,
} from '../../../components/onboarding/BackgroundFields'
import Button from '../../../components/ui/Button'
import BusyNote from '../../../components/ui/BusyNote'

const FINISH_STEPS = [
  { after: 0, text: 'Building your profile…' },
  { after: 4, text: 'Reviewing your written answers…' },
  { after: 25, text: 'Almost there. Written answers take a little longer…' },
]

function BackgroundEditor({ card, onSaved }) {
  const { user } = useAuth()
  const [editing, setEditing] = useState(false)
  const [about, setAbout] = useState(() => aboutForm(card.preferences?.about, user))
  const [learning, setLearning] = useState(() => learningForm(card.preferences?.learning))
  const [saving, setSaving] = useState(false)

  const cancel = () => {
    setAbout(aboutForm(card.preferences?.about, user))
    setLearning(learningForm(card.preferences?.learning))
    setEditing(false)
  }

  const save = async () => {
    setSaving(true)
    try {
      const { data } = await onboardingAPI.editProfile({ about: aboutPayload(about), learning })
      onSaved(data)
      setEditing(false)
      toast.success('Background saved.')
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not save your background.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="rounded-[20px] border border-line bg-tile-2 p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[15px] font-semibold text-ink">Your background</h3>
        {!editing && <Button size="sm" variant="ghost" icon={Pencil} onClick={() => setEditing(true)}>Edit background</Button>}
      </div>
      {editing ? (
        <div className="mt-5 space-y-8">
          <AboutFields form={about} onChange={setAbout} />
          <LearningFields form={learning} onChange={setLearning} />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={cancel} disabled={saving}>Cancel</Button>
            <Button icon={Save} onClick={save} busy={saving} disabled={!aboutComplete(about) || !learningComplete(learning)}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </div>
      ) : (
        <p className="mt-1 text-xs text-ink-subtle">Your answers from the earlier steps. You can change them here or later on your Profile page.</p>
      )}
    </section>
  )
}

export default function ProfileCardStep({ initial, onConflict }) {
  const navigate = useNavigate()
  const { updateUser, refreshUser } = useAuth()
  const [card, setCard] = useState(initial)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [starting, setStarting] = useState(false)
  const finishing = useRef(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    if (!finishing.current) finishing.current = onboardingAPI.finish()
    finishing.current
      .then(({ data }) => { if (!cancelled) setCard(data) })
      .catch(err => {
        finishing.current = null
        if (cancelled) return
        if (err?.response?.status === 409) {
          toast.error(getErrorMessage(err, 'Finish the starting check first.'))
          onConflict?.()
          return
        }
        setError(getErrorMessage(err, 'Could not build your profile.'))
      })
    return () => { cancelled = true }
  }, [attempt])

  const handleSaved = (data) => {
    setCard(data)
    refreshUser().catch(() => {})
  }

  const start = async () => {
    setStarting(true)
    try {
      await refreshUser()
    } catch { /* ignore */ }
    updateUser({ onboarding_done: true })
    navigate('/practice')
  }

  if (!card) {
    return error ? (
      <div className="flex flex-col items-start gap-4" role="alert">
        <p className="text-sm text-ink-muted">{error} Try again in a moment.</p>
        <Button variant="secondary" icon={RefreshCw} onClick={() => setAttempt(a => a + 1)}>Try again</Button>
      </div>
    ) : (
      <BusyNote active steps={FINISH_STEPS} note="This usually takes under a minute." />
    )
  }

  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[22px] border border-pop-mint/25 bg-pop-mint/[0.06] p-6 text-center sm:p-8">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-pop-mint text-canvas shadow-[0_6px_0_theme(colors.key.mint)]" aria-hidden="true">
          <Award size={26} />
        </span>
        <p className="eyebrow mt-5">Your starting title</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{card.title}</h2>
        <p className="mx-auto mt-2 max-w-[48ch] text-sm text-ink-subtle">Here's where you stand right now. It changes as you practise.</p>
      </div>

      <BandSummary card={card} />

      <p className="flex items-center gap-2 text-sm text-ink-muted">
        <Lightbulb size={16} className="shrink-0 text-pop-sun" aria-hidden="true" /> {conceptLine(card)}
      </p>

      <section className="rounded-[20px] border border-line-strong bg-tile-3 p-5">
        <h3 className="flex items-center gap-2 text-[15px] font-semibold text-ink">
          <Compass size={17} className="text-pop-aqua" aria-hidden="true" />
          Start with {topicLabel(card.start_topic)}
        </h3>
        {card.start_reason && <p className="mt-1.5 text-sm leading-relaxed text-ink-subtle">{card.start_reason}</p>}
      </section>

      <BackgroundEditor card={card} onSaved={handleSaved} />

      <div className="flex justify-end border-t border-line pt-6">
        <Button size="lg" iconRight={ArrowRight} onClick={start} busy={starting}>Start learning</Button>
      </div>
    </div>
  )
}
