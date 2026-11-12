import { Clock, FlaskConical } from 'lucide-react'
import Verdict, { toneFor } from '../ui/Verdict'
import CaseBlock, { OutputBlock } from '../ui/CaseBlock'

const UNVERIFIED_REASON = {
  no_problem_statement:      'You did not give a problem statement, so there was nothing to test against.',
  language_not_executable:   'Only C, C++ and Python can be run right now. Other languages get a code review instead.',
  executor_unavailable:      "Couldn't reach the code runner, so nothing could be run. Try again in a minute.",
  reference_unvalidated:     'A reference solution could not be made for this problem, so the tests could not be trusted.',
  insufficient_agreed_tests: 'Too few test cases could be checked for this problem to grade it fairly.',
  test_generation_failed:    'Test cases could not be made right now. Try again in a few minutes.',
}

const CASE_STATUS_LABEL = {
  ok: 'passed',
  wrong_answer: 'wrong output',
  runtime_error: 'crashed',
  timeout: 'too slow',
  memory_exceeded: 'used too much memory',
  compile_error: 'did not compile',
  internal_error: 'could not be run',
}

export default function TestResults({ result }) {
  if (!result) return null

  const {
    compiled, compile_output, verification_status, unverified_reason,
    tests_passed = 0, tests_total = 0, cases = [], first_failing_case, metrics,
    verdict, extra_output, missing_output,
  } = result

  if (compiled === false) {
    return (
      <Verdict tone="wrong" title="Your code did not compile">
        <p>Nothing was run, so there is no score. Fix the error below and evaluate again.</p>
        <div className="mt-4"><OutputBlock label="Compiler output" value={compile_output || 'The compiler gave no output.'} tone="coral" /></div>
      </Verdict>
    )
  }

  if (verification_status !== 'verified') {
    return (
      <Verdict tone="neutral" title="No tests were run">
        <p className="flex items-start gap-2"><FlaskConical size={15} className="mt-0.5 shrink-0 text-ink-subtle" />
          {UNVERIFIED_REASON[unverified_reason] || 'Your code could not be checked against test cases this time.'}
        </p>
        {unverified_reason === 'no_problem_statement' && (
          <p className="mt-2 text-xs text-ink-subtle">Add a problem statement and your code runs against generated test cases, including the edge cases people usually miss.</p>
        )}
      </Verdict>
    )
  }

  const allPassed = tests_total > 0 && tests_passed === tests_total

  return (
    <div className="space-y-4">
      <Verdict tone={toneFor(tests_passed, tests_total)} title={verdict || 'Test results'} meta={`${tests_passed}/${tests_total} tests passed`}>
        <ul className="flex flex-wrap gap-1.5" aria-label="Test cases">
          {cases.map(c => (
            <li
              key={c.ordinal}
              title={`Test ${c.ordinal} (${c.kind}): ${CASE_STATUS_LABEL[c.status] || c.status} · ${c.time_ms} ms`}
              className={`flex h-8 w-8 items-center justify-center rounded-lg border font-mono text-xs ${
                c.passed ? 'border-pop-mint/30 bg-pop-mint/10 text-pop-mint' : 'border-pop-coral/30 bg-pop-coral/10 text-pop-coral'
              }`}
            >
              {c.ordinal}
              <span className="sr-only">{c.passed ? ' passed' : ` ${CASE_STATUS_LABEL[c.status] || 'failed'}`}</span>
            </li>
          ))}
        </ul>

        {verdict === 'No output' ? (
          <p className="mt-4 rounded-2xl border border-pop-sun/20 bg-pop-sun/[0.06] px-3 py-2 text-xs leading-relaxed text-ink-muted">
            Your program ran but printed nothing, so every test counts as wrong. This is usually a loop that never runs. The first line of input is the number of test cases: read it before looping.
          </p>
        ) : (missing_output || extra_output) && (
          <p className="mt-4 rounded-2xl border border-pop-sun/20 bg-pop-sun/[0.06] px-3 py-2 text-xs leading-relaxed text-ink-muted">
            Your program printed {missing_output ? 'fewer' : 'more'} lines than expected. Every test after the first mismatch shifts out of place. Check how many lines you print per test case before hunting a logic bug.
          </p>
        )}

        <div className="mt-4 flex items-center gap-4 border-t border-line pt-3 text-xs text-ink-subtle">
          <span>One run over all {tests_total} tests. Counted, not estimated.</span>
          {metrics?.slowest_case_ms != null && (
            <span className="ml-auto flex shrink-0 items-center gap-1 font-mono"><Clock size={11} /> slowest {metrics.slowest_case_ms} ms</span>
          )}
        </div>
      </Verdict>

      {first_failing_case ? (
        <div className="rounded-[20px] border border-line bg-tile-2 p-5">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-ink">First failing test</p>
            <span className="rounded-full bg-tile-3 px-2.5 py-0.5 font-mono text-[11px] text-ink-subtle">{first_failing_case.kind}</span>
          </div>
          {first_failing_case.rationale && <p className="mt-2 text-xs text-ink-subtle">Checks: {first_failing_case.rationale}</p>}
          <CaseBlock
            title=""
            input={first_failing_case.stdin}
            expected={first_failing_case.expected_stdout}
            actual={first_failing_case.actual_stdout}
          />
          {first_failing_case.stderr && (
            <div className="mt-3"><OutputBlock label="Error output" value={first_failing_case.stderr} tone="coral" /></div>
          )}
        </div>
      ) : allPassed && (
        <p className="text-sm text-ink-muted">Every test passed, including the edge cases. Nice work.</p>
      )}
    </div>
  )
}
