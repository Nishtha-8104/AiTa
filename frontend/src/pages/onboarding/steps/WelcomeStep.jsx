import { Code2, User, BookOpen, ListChecks } from 'lucide-react'
import { StepTitle, StepNav, useSaveStep } from '../../../components/onboarding/StepControls'

const COLLECTED = [
  { icon: Code2,      tone: 'bg-pop-aqua text-canvas', text: 'The programming language you want to practise in' },
  { icon: User,       tone: 'bg-pop-mint text-canvas', text: 'Your background: year, program, institution, coding experience and goal' },
  { icon: BookOpen,   tone: 'bg-pop-sun text-canvas',  text: 'How you like to learn: explanation style, examples, chat language and study time' },
  { icon: ListChecks, tone: 'bg-pop-pink text-canvas', text: 'Your answers to a short check of up to 12 questions' },
]

export default function WelcomeStep({ onSaved, onConflict }) {
  const { saving, save } = useSaveStep('welcome', onSaved, onConflict)

  return (
    <div>
      <StepTitle
        eyebrow="Welcome"
        title="Let's set up your practice"
        subtitle="Before you start, we'll spend under 10 minutes getting to know you, so your first questions are at the right level."
      />

      <p className="mb-3 text-[13px] font-medium text-ink-muted">What we ask about</p>
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {COLLECTED.map(({ icon: Icon, tone, text }) => (
          <li key={text} className="flex items-start gap-3 rounded-[18px] border border-line bg-tile-2 p-4 text-sm leading-relaxed text-ink-muted">
            <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${tone}`}>
              <Icon size={17} />
            </span>
            <span>{text}</span>
          </li>
        ))}
      </ul>

      <div className="mt-6 space-y-2 text-sm leading-relaxed text-ink-subtle">
        <p>PET uses this to pick your practice problems, hints and chat style, so you start at the right level instead of from scratch.</p>
        <p>You can see and change everything later on your Profile page.</p>
      </div>

      <StepNav onNext={() => save({})} saving={saving} nextLabel="Get started" />
    </div>
  )
}
