import { useState } from 'react'
import { useAuth } from '../../../hooks/useAuth'
import { AboutFields, aboutForm, aboutPayload, aboutComplete } from '../../../components/onboarding/BackgroundFields'
import { StepTitle, StepNav, useSaveStep } from '../../../components/onboarding/StepControls'

export default function AboutStep({ initial, onSaved, onBack, onConflict }) {
  const { user } = useAuth()
  const [form, setForm] = useState(() => aboutForm(initial, user))
  const { saving, save } = useSaveStep('about', onSaved, onConflict)

  return (
    <div>
      <StepTitle eyebrow="About you" title="A little about you" subtitle="This helps PET pitch questions and explanations at the right level." />
      <AboutFields form={form} onChange={setForm} />
      <StepNav onBack={onBack} onNext={() => save(aboutPayload(form))} saving={saving}
        canNext={aboutComplete(form)} />
    </div>
  )
}
