import { Cpu } from 'lucide-react'
import { StepTitle, StepNav } from '../../../components/onboarding/StepControls'

export default function ModelStep({ onOpen }) {
  return (
    <div>
      <StepTitle
        eyebrow="AI model"
        title="Choose your AI model"
        subtitle="PET uses an AI model to grade written answers, give hints, answer in chat and write your feedback. Pick one before the check starts."
      />

      <ul className="space-y-3 text-sm leading-relaxed text-ink-muted">
        <li className="flex items-start gap-3 rounded-[18px] border border-line bg-tile-2 p-4">
          <Cpu size={17} className="mt-0.5 shrink-0 text-ink-subtle" aria-hidden="true" />
          <span>
            Use a model running on this computer with Ollama or LM Studio, or a key from
            OpenAI, Anthropic, Google Gemini, Groq, OpenRouter or NVIDIA.
          </span>
        </li>
      </ul>

      <p className="mt-6 text-sm leading-relaxed text-ink-subtle">
        PET tests the model before saving it. You can change it any time from the Model card in the sidebar.
      </p>

      <StepNav onNext={onOpen} nextLabel="Choose model" />
    </div>
  )
}
