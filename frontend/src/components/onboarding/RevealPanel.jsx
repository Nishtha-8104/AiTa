import { useEffect, useRef } from 'react'
import { ArrowRight, Check, Clock, X } from 'lucide-react'
import { topicLabel } from '../learning/labels'
import Button from '../ui/Button'
import Verdict from '../ui/Verdict'
import { OutputBlock } from '../ui/CaseBlock'

const EXPECTED_LABEL = {
  predict_output: 'The program prints',
  find_bug: 'A fixed version',
  fill_blank: 'The blank is',
  write_code: 'A reference solution',
}

const VERDICTS = {
  skipped: { tone: 'neutral', text: "Couldn't run this one, moving on" },
  correct: { tone: 'correct', text: 'Correct' },
  partial: { tone: 'partial', text: 'Partly right' },
  wrong:   { tone: 'wrong', text: 'Not quite' },
}

function verdictOf(score, correct) {
  if (score == null) return correct == null ? 'skipped' : correct ? 'correct' : 'wrong'
  if (score >= 1) return 'correct'
  return score > 0 ? 'partial' : 'wrong'
}

function CodeReveal({ reveal }) {
  if (reveal.score == null && reveal.correct == null) {
    return (
      <Verdict tone="neutral" title={VERDICTS.skipped.text}>
        The code runner is unavailable right now, so this question isn't counted. Nothing you need to do.
      </Verdict>
    )
  }
  const v = VERDICTS[verdictOf(reveal.score, reveal.correct)]
  const bugLineInWhy = reveal.why?.includes(`line ${reveal.bug_line}`)
  return (
    <Verdict
      tone={v.tone}
      title={v.text}
      meta={reveal.kind === 'write_code' && reveal.total > 0 ? `${reveal.passed}/${reveal.total} tests passed` : null}
    >
      {reveal.why && <p>{reveal.why}</p>}
      {reveal.compile_output && (
        <div className="mt-3">
          <OutputBlock label="Compiler message" value={reveal.compile_output} tone="coral" />
        </div>
      )}
      {reveal.kind === 'find_bug' && reveal.bug_line != null && !bugLineInWhy && (
        <p className="mt-2">The bug is on <span className="font-mono text-pop-sun">line {reveal.bug_line}</span>.</p>
      )}
      {reveal.expected != null && reveal.expected !== '' && (
        <div className="mt-4">
          <OutputBlock label={EXPECTED_LABEL[reveal.kind] || 'Expected'} value={reveal.expected} tone="mint" />
        </div>
      )}
    </Verdict>
  )
}

function TheoryItem({ entry }) {
  const r = entry.reveal || {}
  const v = VERDICTS[verdictOf(entry.score, r.correct ?? false)]
  return (
    <li className="rounded-[20px] border border-line bg-tile-2 p-5">
      <p className="eyebrow text-[10px]">{topicLabel(entry.topic)}</p>
      {entry.question && <p className="mt-2 text-sm text-ink">{entry.question}</p>}
      {entry.score == null && r.correct == null
        ? <p className="mt-3 text-sm text-ink-subtle">This answer couldn't be reviewed, so it isn't counted.</p>
        : <Verdict tone={v.tone} title={v.text} className="mt-3 !p-4">{entry.feedback}</Verdict>}
      {Array.isArray(r.rubric) && (
        <ul className="mt-4 space-y-1.5" aria-label="Key points">
          {r.rubric.map((point, i) => {
            const hit = !!r.points_present?.[i]
            return (
              <li key={i} className="flex items-start gap-2 text-sm">
                {hit ? <Check size={15} className="mt-0.5 shrink-0 text-pop-mint" aria-label="Covered" />
                  : <X size={15} className="mt-0.5 shrink-0 text-ink-faint" aria-label="Missing" />}
                <span className={hit ? 'text-ink-muted' : 'text-ink-subtle'}>{point}</span>
              </li>
            )
          })}
        </ul>
      )}
      {r.model_answer && (
        <div className="mt-4 border-t border-line pt-4">
          <p className="eyebrow text-[10px]">A model answer</p>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">{r.model_answer}</p>
        </div>
      )}
    </li>
  )
}

function TheoryReveal({ reveal }) {
  const items = reveal.items || []
  if (!items.length) {
    return (
      <Verdict tone="neutral" title="Saved">
        <span className="flex items-start gap-2"><Clock size={16} className="mt-0.5 shrink-0" /> Your answers are saved and will be reviewed shortly.</span>
      </Verdict>
    )
  }
  return (
    <>
      <h3 className="mb-4 text-lg font-semibold tracking-tight text-ink">Your written answers</h3>
      <ul className="space-y-3">
        {items.map(entry => <TheoryItem key={entry.item_id} entry={entry} />)}
      </ul>
      {reveal.expectedCount > items.length && (
        <p className="mt-3 text-xs text-ink-subtle">The rest are saved and will be reviewed shortly.</p>
      )}
    </>
  )
}

export default function RevealPanel({ reveal, onContinue }) {
  const continueRef = useRef(null)
  useEffect(() => { continueRef.current?.focus() }, [reveal])

  return (
    <div className="motion-safe:animate-rise" aria-live="polite">
      {reveal.kind === 'theory' ? <TheoryReveal reveal={reveal} /> : <CodeReveal reveal={reveal} />}
      <div className="mt-6 flex justify-end">
        <Button ref={continueRef} size="lg" iconRight={ArrowRight} onClick={onContinue}>Continue</Button>
      </div>
    </div>
  )
}
