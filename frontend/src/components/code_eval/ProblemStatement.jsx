import Chip from '../ui/Chip'
import { OutputBlock } from '../ui/CaseBlock'

export default function ProblemStatement({ problem }) {
  if (!problem) return null

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[15px] font-semibold text-ink">{problem.title}</span>
        {problem.topic && <Chip>{problem.topic}</Chip>}
        <Chip tone="aqua">{problem.test_count} tests</Chip>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">{problem.statement}</p>
      {problem.constraints && (
        <p className="font-mono text-xs leading-relaxed text-ink-subtle">Constraints: {problem.constraints}</p>
      )}
      {problem.sample_input && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <OutputBlock label="Sample input" value={problem.sample_input} tone="aqua" />
          <OutputBlock label="Sample output" value={problem.sample_output} tone="mint" />
        </div>
      )}
    </div>
  )
}
