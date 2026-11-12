import { useState } from 'react'
import { Check } from 'lucide-react'
import { LANGUAGES } from '../../../components/onboarding/options'
import { StepTitle, StepNav, useSaveStep } from '../../../components/onboarding/StepControls'

const KEY = {
  c:      { glyph: 'C',   face: 'bg-pop-aqua', depth: 'shadow-[0_6px_0_theme(colors.key.aqua)]' },
  cpp:    { glyph: 'C++', face: 'bg-pop-pink', depth: 'shadow-[0_6px_0_theme(colors.key.pink)]' },
  python: { glyph: 'Py',  face: 'bg-pop-sun',  depth: 'shadow-[0_6px_0_theme(colors.key.sun)]' },
}

export default function LanguageStep({ initial, onSaved, onBack, onConflict }) {
  const [language, setLanguage] = useState(initial || null)
  const { saving, save } = useSaveStep('language', onSaved, onConflict)

  return (
    <div>
      <StepTitle
        eyebrow="Language"
        title="Pick your language"
        subtitle="The check and your practice problems will use it. You can change it later on your Profile page."
      />

      <div role="radiogroup" aria-label="Programming language" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {LANGUAGES.map(l => {
          const selected = language === l.value
          const key = KEY[l.value]
          return (
            <button
              key={l.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => setLanguage(l.value)}
              className={`relative flex flex-row items-center gap-4 rounded-[20px] border p-5 text-left transition-colors duration-200 sm:flex-col sm:items-start ${
                selected ? 'border-ink bg-tile-3' : 'border-line-strong bg-tile-2 hover:border-ink-faint'
              }`}
            >
              <span aria-hidden="true" className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl font-mono text-lg font-bold text-canvas transition-transform duration-200 ${key.face} ${selected ? 'translate-y-1 shadow-[0_2px_0_rgba(0,0,0,0.4)]' : key.depth}`}>
                {key.glyph}
              </span>
              <span className="min-w-0">
                <span className="block text-[15px] font-semibold text-ink">{l.label}</span>
                <span className="mt-1 block text-xs leading-relaxed text-ink-subtle">{l.blurb}</span>
              </span>
              {selected && (
                <span className="absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-full bg-ink">
                  <Check size={14} className="text-canvas" strokeWidth={3} />
                </span>
              )}
            </button>
          )
        })}
      </div>

      <StepNav onBack={onBack} onNext={() => save({ language })} canNext={!!language} saving={saving} />
    </div>
  )
}
