import { CheckCircle2, Code2, GitBranch, Zap } from 'lucide-react'
import { palette } from '../../styles/palette'

const DIMENSIONS = [
  { key: 'correctness', label: 'Correctness', icon: CheckCircle2, bar: 'bg-pop-mint', text: 'text-pop-mint', desc: 'Test cases actually passed', weight: '55%' },
  { key: 'complexity',  label: 'Complexity',  icon: GitBranch,    bar: 'bg-pop-aqua', text: 'text-pop-aqua', desc: 'Branching, function length, parameters', weight: '20%' },
  { key: 'efficiency',  label: 'Efficiency',  icon: Zap,          bar: 'bg-pop-sun',  text: 'text-pop-sun',  desc: 'Estimated time and memory use', weight: '15%' },
  { key: 'style',       label: 'Style',       icon: Code2,        bar: 'bg-pop-pink', text: 'text-pop-pink', desc: 'Formatting, naming, conventions', weight: '10%' },
]

const UNVERIFIED_SHORT = {
  no_problem_statement:      'no problem statement given',
  language_not_executable:   'this language cannot be run yet',
  executor_unavailable:      'the code runner was unreachable',
  reference_unvalidated:     'no trustworthy reference solution',
  insufficient_agreed_tests: 'too few test cases could be checked',
  test_generation_failed:    'test cases could not be made',
}

function band(score) {
  if (score >= 80) return { word: 'Excellent', color: palette.pop.mint }
  if (score >= 60) return { word: 'Good', color: palette.pop.aqua }
  if (score >= 40) return { word: 'Needs work', color: palette.pop.sun }
  return { word: 'Keep going', color: palette.pop.coral }
}

function Gauge({ score }) {
  const r = 52
  const c = 2 * Math.PI * r
  const { word, color } = band(score)
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative h-36 w-36">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90" aria-hidden="true">
          <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" />
          <circle
            cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c - (score / 100) * c}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-3xl font-semibold text-ink">{score.toFixed(0)}</span>
          <span className="text-[11px] text-ink-subtle">of 100</span>
        </div>
      </div>
      <p className="text-sm font-semibold" style={{ color }}>{word}</p>
      <p className="-mt-2 text-xs text-ink-subtle">Overall score</p>
    </div>
  )
}

export default function ScoreRadar({ scores, unverifiedReason }) {
  if (!scores) return null
  return (
    <div className="space-y-5">
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        <Gauge score={scores.overall || 0} />
        <ul className="w-full flex-1 space-y-4">
          {DIMENSIONS.map(dim => {
            const score = scores[dim.key] ?? null
            const Icon = dim.icon
            const missing = score == null
            return (
              <li key={dim.key}>
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className={`flex items-center gap-2 ${missing ? 'text-ink-faint' : 'text-ink-muted'}`}>
                    <Icon size={14} className={missing ? '' : dim.text} /> {dim.label}
                    <span className="font-mono text-[10px] text-ink-faint">{dim.weight}</span>
                  </span>
                  <span className={`font-mono text-xs ${missing ? 'text-ink-faint' : dim.text}`}>{missing ? 'not checked' : score.toFixed(0)}</span>
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/[0.06]">
                  {!missing && <div className={`h-full rounded-full ${dim.bar} transition-[width] duration-1000 ease-out`} style={{ width: `${score}%` }} />}
                </div>
                <p className="mt-1 text-[11px] text-ink-faint">
                  {missing ? (UNVERIFIED_SHORT[unverifiedReason] || 'could not be measured this time') : dim.desc}
                </p>
              </li>
            )
          })}
        </ul>
      </div>
      {scores.correctness == null && (
        <p className="border-t border-line pt-4 text-xs leading-relaxed text-ink-subtle">
          Correctness could not be measured, so the overall score uses the other three parts only. It is not padded with a guess.
        </p>
      )}
    </div>
  )
}
