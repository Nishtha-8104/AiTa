import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowRight, Code2, HelpCircle, Layers, RefreshCw } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { recheckAPI, getErrorMessage } from '../utils/api'
import { StepTitle } from '../components/onboarding/StepControls'
import BandSummary from '../components/onboarding/BandSummary'
import FocusLayout from '../components/ui/FocusLayout'
import Button from '../components/ui/Button'
import BusyNote from '../components/ui/BusyNote'
import DiagnosticStep from './onboarding/steps/DiagnosticStep'

const LABELS = { c: 'C', cpp: 'C++', python: 'Python' }

export default function LanguageCheckPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const language = LABELS[user?.preferred_language] || 'your new language'
  const [result, setResult] = useState(null)
  const [finishing, setFinishing] = useState(false)
  const [finishError, setFinishError] = useState(null)

  const finish = async () => {
    setFinishing(true)
    setFinishError(null)
    try {
      const { data } = await recheckAPI.finish()
      setResult(data)
    } catch (err) {
      setFinishError(getErrorMessage(err, 'Could not save your check.'))
    } finally {
      setFinishing(false)
    }
  }

  // No open check (already finished, or never switched): Practice is free to open.
  const onConflict = () => {
    toast('No language check is waiting for you.')
    navigate('/practice', { replace: true })
  }

  const points = [
    { icon: Layers, tone: 'bg-pop-aqua/15 text-pop-aqua', text: `Your progress in each language is kept separately, so we need to see where you stand in ${language}.` },
    { icon: Code2, tone: 'bg-pop-mint/15 text-pop-mint', text: 'How well you explain ideas carries over, so there are no written answers this time.' },
    { icon: HelpCircle, tone: 'bg-pop-sun/15 text-pop-sun', text: 'Not sure? Press "I don\'t know". It simply counts as not known yet.' },
  ]

  const intro = (
    <>
      <StepTitle eyebrow="Language check" title={`A short check in ${language}`}
        subtitle="Up to 9 code questions, about 4 minutes. It starts easy and adapts to your answers." />
      <ul className="mb-8 space-y-3">
        {points.map(({ icon: Icon, tone, text }) => (
          <li key={text} className="flex items-start gap-3 text-sm leading-relaxed text-ink-muted">
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${tone}`}><Icon size={15} /></span>
            <span className="pt-1.5">{text}</span>
          </li>
        ))}
      </ul>
    </>
  )

  let body
  if (result) {
    body = (
      <div className="tile p-6 sm:p-10 motion-safe:animate-rise">
        <StepTitle eyebrow="Done" title={`You're set up in ${language}`} subtitle={result.title} />
        <div className="mb-8"><BandSummary card={{ bands: result.bands }} /></div>
        <Button size="lg" iconRight={ArrowRight} onClick={() => navigate('/practice', { replace: true })}>Go to Practice</Button>
      </div>
    )
  } else if (finishing || finishError) {
    body = finishError ? (
      <div className="tile flex flex-col items-start gap-4 p-6">
        <p className="text-sm text-ink-muted">{finishError} Try again in a moment.</p>
        <Button variant="secondary" icon={RefreshCw} onClick={finish}>Try again</Button>
      </div>
    ) : (
      <BusyNote active steps={[{ after: 0, text: 'Saving your check…' }]} />
    )
  } else {
    body = <DiagnosticStep api={recheckAPI} intro={intro} written={false} onSaved={finish} onConflict={onConflict} />
  }

  return (
    <FocusLayout width={result || finishing || finishError ? 'max-w-2xl' : 'max-w-6xl'}>
      {body}
    </FocusLayout>
  )
}
