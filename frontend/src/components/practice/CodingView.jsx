import { useState } from 'react'
import { Lightbulb, Play, Send } from 'lucide-react'
import toast from 'react-hot-toast'
import { codeEvalAPI, feedbackAPI, getErrorMessage } from '../../utils/api'
import { useAuth } from '../../hooks/useAuth'
import { LANGUAGES, TEMPLATES, isTemplate } from '../code/templates'
import { misconceptionLabel } from '../learning/labels'
import RichText from '../learning/RichText'
import Button from '../ui/Button'
import BusyNote from '../ui/BusyNote'
import CaseBlock, { OutputBlock } from '../ui/CaseBlock'
import Chip from '../ui/Chip'
import CodeEditor from '../ui/CodeEditor'
import HintLadder from '../ui/HintLadder'
import Verdict, { toneFor } from '../ui/Verdict'
import Workbench, { EditorTile, LanguagePicker } from './Workbench'
import { Panel, toastAwards } from './shared'

const STEPS = {
  run: [
    { after: 0, text: 'Running your code on the example…' },
    { after: 10, text: 'Still running…' },
  ],
  submit: [
    { after: 0, text: 'Compiling your code…' },
    { after: 4, text: 'Running your code against all the tests…' },
    { after: 15, text: 'Checking the result and writing a short summary…' },
    { after: 60, text: 'Taking longer than usual. Please keep this page open…' },
  ],
  hint: [
    { after: 0, text: 'Preparing a hint that does not give the answer away…' },
    { after: 30, text: 'Still working on your hint…' },
  ],
}

export function ProblemPanel({ item, eyebrow = 'Problem' }) {
  return (
    <Panel eyebrow={eyebrow} title={item.title}>
      <RichText text={item.statement} className="text-[15px] text-ink-muted" />
      {item.sample_input != null && (
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <OutputBlock label="Example input" value={item.sample_input} tone="aqua" />
          <OutputBlock label="Example output" value={item.sample_output} tone="mint" />
        </div>
      )}
    </Panel>
  )
}

export default function CodingView({ item, onGraded }) {
  const { user } = useAuth()
  const defaultLanguage = user?.preferred_language || 'c'
  const [language, setLanguage] = useState(defaultLanguage)
  const [code, setCode] = useState(TEMPLATES[defaultLanguage])
  const [runResult, setRunResult] = useState(null)
  const [report, setReport] = useState(null)
  const [hints, setHints] = useState([])
  const [busy, setBusy] = useState(null)

  const changeLanguage = lang => {
    if (isTemplate(code)) setCode(TEMPLATES[lang])
    setLanguage(lang)
  }

  const run = async () => {
    setBusy('run')
    try {
      const { data } = await codeEvalAPI.run({ problem_id: item.id, language, code })
      setRunResult(data)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't reach the code runner. Try again in a minute."))
    } finally {
      setBusy(null)
    }
  }

  const submit = async () => {
    setBusy('submit')
    try {
      const { data } = await codeEvalAPI.submitAndEvaluate({
        language, code, title: item.title, problem_id: item.id,
      })
      setReport(data)
      setRunResult(null)
      setHints(data.hint ? [data.hint] : [])
      toastAwards(data)
      if (data.verification_status === 'verified' && data.tests_total > 0) onGraded()
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't grade your code. Try again in a minute."))
    } finally {
      setBusy(null)
    }
  }

  const moreHelp = async () => {
    setBusy('hint')
    try {
      const { data } = await feedbackAPI.hint(item.id)
      setHints(prev => [...prev, data])
      if (report?.verification_status === 'verified') onGraded()
    } catch (err) {
      toast.error(getErrorMessage(err, 'No hint is available right now.'))
    } finally {
      setBusy(null)
    }
  }

  const passed = report && report.tests_total > 0 && report.tests_passed === report.tests_total
  const topLevel = hints.length ? hints[hints.length - 1].level : 0
  const runPassed = runResult && runResult.total > 0 && runResult.passed === runResult.total

  const editor = (
    <>
      <EditorTile
        toolbar={
          <>
            <LanguagePicker languages={LANGUAGES} value={language} onChange={changeLanguage} disabled={Boolean(busy)} />
            <span className="text-xs text-ink-subtle">Tab indents · Esc then Tab leaves the editor</span>
          </>
        }
        footer={
          <>
            <Button variant="secondary" icon={Play} onClick={run} busy={busy === 'run'} disabled={Boolean(busy) || passed}>
              Run example
            </Button>
            <Button icon={Send} onClick={submit} busy={busy === 'submit'} disabled={Boolean(busy) || passed}>
              {report && !passed ? 'Submit again' : 'Submit'}
            </Button>
            {report && !passed && topLevel < 4 && (
              <Button variant="hint" icon={Lightbulb} onClick={moreHelp} busy={busy === 'hint'} disabled={Boolean(busy)} className="sm:ml-auto">
                {topLevel === 0 ? 'Get a hint' : 'Stronger hint'}
              </Button>
            )}
            {!report && <span className="text-xs text-ink-subtle sm:ml-auto">Run example is free. Submit is graded.</span>}
          </>
        }
      >
        <CodeEditor value={code} onChange={setCode} language={language} readOnly={Boolean(busy) || passed} minHeight="360px" maxHeight="640px" label="Your solution" />
      </EditorTile>

      <BusyNote active={Boolean(busy)} steps={STEPS[busy] || STEPS.submit} note={busy === 'submit' ? 'This can take up to a minute.' : null} />

      {runResult && !report && !busy && (
        <Verdict
          tone={runPassed ? 'correct' : runResult.passed > 0 ? 'partial' : 'wrong'}
          title={`Example: ${runResult.verdict}`}
          meta={`${runResult.passed}/${runResult.total} example cases · not graded`}
        >
          {runResult.cases.filter(c => !c.passed).slice(0, 2).map((c, i) => (
            <CaseBlock key={i} input={c.input} expected={c.expected} actual={c.actual} />
          ))}
          {(runResult.compile_output || runResult.stderr) && (
            <div className="mt-4">
              <OutputBlock label={runResult.compile_output ? 'Compiler output' : 'Error output'} value={runResult.compile_output || runResult.stderr} tone="coral" />
            </div>
          )}
        </Verdict>
      )}

      {report && !busy && (
        <Verdict
          tone={toneFor(report.tests_passed, report.tests_total)}
          title={passed ? 'All tests passed' : report.verdict}
          meta={`${report.tests_passed}/${report.tests_total} tests passed`}
        >
          {report.summary && <p>{report.summary}</p>}
          {report.first_failing_case && (
            <CaseBlock
              input={report.first_failing_case.stdin}
              expected={report.first_failing_case.expected_stdout}
              actual={report.first_failing_case.actual_stdout}
            />
          )}
          {report.misconceptions?.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-ink-subtle">Looks like:</span>
              {report.misconceptions.map(m => <Chip key={m} tone="sun">{misconceptionLabel(m)}</Chip>)}
            </div>
          )}
        </Verdict>
      )}

      {hints.length > 0 && !passed && <HintLadder hints={hints} />}
    </>
  )

  return <Workbench problem={<ProblemPanel item={item} />} editor={editor} />
}
