import { useEffect, useState } from 'react'
import { Check, Send, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { assessmentAPI, getErrorMessage } from '../../utils/api'
import { misconceptionLabel } from '../learning/labels'
import RichText from '../learning/RichText'
import Button from '../ui/Button'
import Verdict from '../ui/Verdict'
import { LevelNote, Panel, toastAwards } from './shared'

const LETTERS = 'ABCDEFGH'

function optionState(i, chosen, result) {
  if (!result) return chosen === i ? 'chosen' : 'idle'
  if (i === result.answer_index) return 'right'
  if (i === result.chosen_index) return 'wrong'
  return 'dim'
}

const OPTION_STYLE = {
  idle:   'border-line-strong bg-tile-2 hover:border-ink-faint hover:bg-tile-3',
  chosen: 'border-ink bg-tile-3',
  right:  'border-pop-mint/60 bg-pop-mint/[0.08]',
  wrong:  'border-pop-coral/60 bg-pop-coral/[0.08]',
  dim:    'border-line bg-tile-2 opacity-50',
}

const KEY_STYLE = {
  idle: 'bg-tile-3 text-ink-muted shadow-[0_3px_0_theme(colors.shadow)]',
  chosen: 'bg-ink text-canvas shadow-[0_3px_0_theme(colors.key.ink)]',
  right: 'bg-pop-mint text-canvas shadow-[0_3px_0_theme(colors.key.mint)]',
  wrong: 'bg-pop-coral text-canvas shadow-[0_3px_0_theme(colors.key.coral)]',
  dim: 'bg-tile-3 text-ink-faint',
}

export default function McqView({ item, onGraded }) {
  const [chosen, setChosen] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (result) return
    const onKey = e => {
      if (e.target.closest('input, textarea, [contenteditable="true"]') || e.metaKey || e.ctrlKey || e.altKey) return
      const i = LETTERS.indexOf(e.key.toUpperCase())
      if (i >= 0 && i < item.options.length) setChosen(i)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [item.options.length, result])

  const submit = async () => {
    setBusy(true)
    try {
      const { data } = await assessmentAPI.answerMcq(item.id, chosen)
      setResult(data)
      toastAwards(data)
      onGraded(data.mastery_after)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't check your answer. Try again in a moment."))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Panel>
        <RichText text={item.stem} className="text-[16px] leading-relaxed text-ink" />
      </Panel>

      <div role="radiogroup" aria-label="Answer options" className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {item.options.map((opt, i) => {
          const state = optionState(i, chosen, result)
          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={chosen === i}
              disabled={Boolean(result)}
              onClick={() => setChosen(i)}
              className={`group flex min-h-[64px] items-start gap-3.5 rounded-[18px] border p-4 text-left transition-[background-color,border-color,transform] duration-200 active:scale-[0.99] disabled:cursor-default ${OPTION_STYLE[state]}`}
            >
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] font-mono text-sm font-semibold transition-colors ${KEY_STYLE[state]}`}>
                {state === 'right' ? <Check size={16} strokeWidth={3} /> : state === 'wrong' ? <X size={16} strokeWidth={3} /> : LETTERS[i]}
              </span>
              <code className="min-w-0 flex-1 whitespace-pre-wrap break-words pt-1 font-mono text-[13.5px] leading-relaxed text-ink">{opt}</code>
              {state === 'right' && <span className="sr-only">Correct answer</span>}
              {state === 'wrong' && <span className="sr-only">Your answer</span>}
            </button>
          )
        })}
      </div>

      {!result ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="hidden text-xs text-ink-subtle sm:block">Tip: press A, B, C or D to pick.</p>
          <Button size="lg" icon={Send} onClick={submit} disabled={chosen === null} busy={busy}>
            {busy ? 'Checking…' : 'Check answer'}
          </Button>
        </div>
      ) : (
        <Verdict
          tone={result.correct ? 'correct' : 'wrong'}
          title={result.correct ? 'Correct' : 'Not quite'}
          meta={<LevelNote after={result.mastery_after} />}
        >
          {result.misconception && !result.correct && (
            <p className="mb-2 text-pop-sun">
              That answer is what you get from: <span className="font-semibold">{misconceptionLabel(result.misconception)}</span>
            </p>
          )}
          {result.explanation && <p>{result.explanation}</p>}
        </Verdict>
      )}
    </div>
  )
}
