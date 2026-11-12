import { useState } from 'react'
import { Check, Send, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { getErrorMessage, topicPracticeAPI } from '../../utils/api'
import RichText from '../learning/RichText'
import Button from '../ui/Button'
import BusyNote from '../ui/BusyNote'
import Verdict from '../ui/Verdict'
import { LevelNote, Panel, toastAwards } from './shared'

const ANSWER_CAP = 2000
const STEPS = [
  { after: 0, text: 'Reading your answer…' },
  { after: 10, text: 'Still checking it against the key points…' },
]
const RESULT = {
  1: { tone: 'correct', title: 'Well explained' },
  0.5: { tone: 'partial', title: 'Partly there' },
  0: { tone: 'wrong', title: 'Not yet' },
}

export default function TheoryView({ item, onGraded }) {
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    try {
      const { data } = await topicPracticeAPI.answerTheory(item.id, answer)
      setResult(data)
      toastAwards(data)
      onGraded(data.mastery_after)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't check your answer. It's still here; try again in a moment."))
    } finally {
      setBusy(false)
    }
  }

  const verdict = result && (RESULT[result.score] || RESULT[0])

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Panel eyebrow="Explain in your own words">
        <RichText text={item.question} className="text-[16px] leading-relaxed text-ink" />
      </Panel>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-ink">Your answer</span>
        <textarea
          value={answer}
          onChange={e => setAnswer(e.target.value.slice(0, ANSWER_CAP))}
          readOnly={busy || Boolean(result)}
          rows={7}
          placeholder="A few sentences is enough. Say why, not only what."
          className="w-full resize-y rounded-2xl border border-line-strong bg-tile-2 p-4 text-[15px] leading-relaxed text-ink placeholder:text-ink-faint focus:border-ink-faint focus:outline-none"
        />
        <span className="self-end font-mono text-xs text-ink-subtle">{answer.length}/{ANSWER_CAP}</span>
      </label>

      <BusyNote active={busy} steps={STEPS} />

      {!result ? (
        <Button size="lg" icon={Send} onClick={submit} busy={busy} disabled={!answer.trim()} className="self-end">
          {busy ? 'Checking…' : 'Check answer'}
        </Button>
      ) : (
        <Verdict tone={verdict.tone} title={verdict.title} meta={<LevelNote after={result.mastery_after} />}>
          {result.feedback && <p className="mb-3">{result.feedback}</p>}
          <p className="font-medium text-ink">Key points</p>
          <ul className="mt-2 flex flex-col gap-1.5">
            {result.key_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2">
                {result.points_present[i]
                  ? <Check size={15} className="mt-0.5 shrink-0 text-pop-mint" aria-label="You said this" />
                  : <X size={15} className="mt-0.5 shrink-0 text-pop-coral" aria-label="Missing" />}
                <span>{point}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 font-medium text-ink">A model answer</p>
          <RichText text={result.model_answer} className="mt-1" />
        </Verdict>
      )}
    </div>
  )
}
