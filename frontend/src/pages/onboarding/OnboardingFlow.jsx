import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { onboardingAPI, getErrorMessage } from '../../utils/api'
import FocusLayout from '../../components/ui/FocusLayout'
import Button from '../../components/ui/Button'
import Skeleton from '../../components/ui/Skeleton'
import ProgressHeader from '../../components/onboarding/ProgressHeader'
import { STEPS } from '../../components/onboarding/options'
import WelcomeStep from './steps/WelcomeStep'
import LanguageStep from './steps/LanguageStep'
import AboutStep from './steps/AboutStep'
import LearningStep from './steps/LearningStep'
import DiagnosticStep from './steps/DiagnosticStep'
import ProfileCardStep from './steps/ProfileCardStep'
import ModelStep from './steps/ModelStep'
import ModelWindow from '../../components/model/ModelWindow'
import { useModelSettings } from '../../components/model/ModelCard'

const ORDER = [...STEPS.map(s => s.key), 'done']
const VIEWS = {
  welcome: WelcomeStep,
  language: LanguageStep,
  about: AboutStep,
  learning: LearningStep,
  diagnostic: DiagnosticStep,
  card: ProfileCardStep,
}
const CAN_GO_BACK = ['language', 'about', 'learning']

function initialFor(step, state) {
  if (step === 'diagnostic') return state.diagnostic
  if (step === 'card') return state.card
  return state.answers?.[step] ?? null
}

export default function OnboardingFlow() {
  const navigate = useNavigate()
  const { updateUser } = useAuth()
  const [state, setState] = useState(null)
  const [view, setView] = useState(null)
  const [error, setError] = useState(null)
  const model = useModelSettings()

  const load = useCallback(() => {
    setError(null)
    onboardingAPI.state()
      .then(({ data }) => setState(data))
      .catch(err => setError(getErrorMessage(err, 'Could not load your onboarding.')))
  }, [])

  useEffect(load, [load])

  const step = view || state?.current_step

  useEffect(() => {
    if (step !== 'done') return
    updateUser({ onboarding_done: true })
    navigate('/practice', { replace: true })
  }, [step, updateUser, navigate])

  useEffect(() => { window.scrollTo(0, 0) }, [step])

  // After going Back and re-saving, walk forward one step rather than jump to the server's step.
  const handleSaved = (newState) => {
    setState(s => ({ ...s, ...newState }))
    const next = ORDER[ORDER.indexOf(step) + 1]
    setView(ORDER.indexOf(next) < ORDER.indexOf(newState.current_step) ? next : null)
  }

  const handleProgress = (diagnostic) => setState(s => ({ ...s, diagnostic }))

  const handleBack = () => setView(ORDER[ORDER.indexOf(step) - 1])

  // Another tab moved the server on (e.g. started the check), so drop the local Back view.
  const handleConflict = () => {
    setView(null)
    load()
  }

  // The check grades written answers with the AI model, so one must be chosen first.
  const needsModel = step === 'diagnostic' && model.settings?.source === 'none'
  const View = VIEWS[step]
  const diag = step === 'diagnostic' && !needsModel ? state?.diagnostic : null
  const question = diag && !diag.done && diag.item ? diag.order : null

  return (
    <FocusLayout
      width={step === 'diagnostic' ? 'max-w-6xl' : 'max-w-2xl'}
      aside={<span className="hidden text-xs text-ink-subtle sm:block">Setting up your practice · about 10 minutes</span>}
    >
      {error ? (
        <div className="tile flex flex-col items-start gap-4 p-6">
          <p className="text-sm text-ink-muted">{error} Check your connection, then try again.</p>
          <Button variant="secondary" icon={RefreshCw} onClick={load}>Try again</Button>
        </div>
      ) : !View ? (
        <div className="space-y-6" aria-busy="true">
          <Skeleton className="h-1.5 w-full rounded-full" />
          <div className="tile space-y-4 p-8">
            <Skeleton className="h-7 w-1/2" />
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-4 w-3/5" />
          </div>
        </div>
      ) : needsModel ? (
        <>
          <ProgressHeader step={step} />
          <div className="tile p-6 sm:p-10 motion-safe:animate-rise">
            <ModelStep settings={model.settings} onOpen={() => model.setOpen(true)} />
          </div>
        </>
      ) : (
        <>
          <ProgressHeader step={step} question={question} remaining={diag?.remaining} />
          <div className={`${step === 'diagnostic' ? '' : 'tile p-6 sm:p-10'} motion-safe:animate-rise`}>
            <View
              key={step}
              initial={initialFor(step, state)}
              onSaved={handleSaved}
              onConflict={handleConflict}
              onProgress={handleProgress}
              onBack={CAN_GO_BACK.includes(step) ? handleBack : undefined}
            />
          </div>
        </>
      )}
      {model.open && model.settings && (
        <ModelWindow settings={model.settings} onClose={() => model.setOpen(false)} onChange={model.setSettings} />
      )}
    </FocusLayout>
  )
}
