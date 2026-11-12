import { TextField } from '../ui/Field'
import {
  YEARS, EXPERIENCE, GOALS,
  EXPLANATION_STYLES, EXAMPLE_ORDERS, CHAT_LANGUAGES, HOURS_PER_WEEK, SELF_RATINGS,
} from './options'
import { ChoiceGroup } from './StepControls'

export const LEARNING_FIELDS = ['explanation_style', 'example_order', 'chat_language', 'hours_per_week', 'self_rating']

export const aboutForm = (initial, user) => ({
  year_of_study: initial?.year_of_study ?? (YEARS.some(y => y.value === user?.year_of_study) ? user.year_of_study : null),
  program: initial?.program ?? '',
  institution: initial?.institution ?? user?.institution ?? '',
  experience: initial?.experience ?? null,
  goal: initial?.goal ?? null,
})

export const aboutPayload = (form) => ({
  ...form,
  program: form.program.trim() || null,
  institution: form.institution.trim() || null,
})

export const aboutComplete = (form) => !!form.experience && !!form.goal

export const learningForm = (initial) =>
  Object.fromEntries(LEARNING_FIELDS.map(f => [f, initial?.[f] ?? null]))

export const learningComplete = (form) => LEARNING_FIELDS.every(f => form[f] !== null)

export function AboutFields({ form, onChange, withSchool = true }) {
  const set = (field) => (value) => onChange({ ...form, [field]: value })
  const program = (
    <TextField label="Program" optional maxLength={100} value={form.program}
      onChange={e => set('program')(e.target.value)} placeholder="e.g. B.Tech CSE" />
  )

  return (
    <div className="space-y-6">
      {withSchool ? (
        <>
          <ChoiceGroup label="Year of study" options={YEARS} value={form.year_of_study}
            onChange={set('year_of_study')} columns={6} clearable />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {program}
            <TextField label="Institution" optional maxLength={255} value={form.institution}
              onChange={e => set('institution')(e.target.value)} placeholder="College or university" />
          </div>
        </>
      ) : program}

      <ChoiceGroup label="Coding experience" options={EXPERIENCE} value={form.experience}
        onChange={set('experience')} columns={5} />

      <ChoiceGroup label="Main goal" options={GOALS} value={form.goal}
        onChange={set('goal')} columns={2} />
    </div>
  )
}

export function LearningFields({ form, onChange }) {
  const set = (field) => (value) => onChange({ ...form, [field]: value })
  return (
    <div className="space-y-6">
      <ChoiceGroup label="Explanations" options={EXPLANATION_STYLES} value={form.explanation_style}
        onChange={set('explanation_style')} />
      <ChoiceGroup label="Examples or concept first?" options={EXAMPLE_ORDERS} value={form.example_order}
        onChange={set('example_order')} />
      <ChoiceGroup label="Chat language" options={CHAT_LANGUAGES} value={form.chat_language}
        onChange={set('chat_language')} />
      <ChoiceGroup label="Time for coding each week" options={HOURS_PER_WEEK} value={form.hours_per_week}
        onChange={set('hours_per_week')} columns={4} />
      <ChoiceGroup label="How confident are you with programming?" options={SELF_RATINGS} value={form.self_rating}
        onChange={set('self_rating')} columns={5} />
    </div>
  )
}
