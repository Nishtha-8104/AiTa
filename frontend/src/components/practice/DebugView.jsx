import { useState } from 'react'
import { Bug, RotateCcw, Send } from 'lucide-react'
import toast from 'react-hot-toast'
import { assessmentAPI, getErrorMessage } from '../../utils/api'
import { languageLabel } from '../learning/labels'
import RichText from '../learning/RichText'
import Button from '../ui/Button'
import BusyNote from '../ui/BusyNote'
import CaseBlock from '../ui/CaseBlock'
import CodeEditor from '../ui/CodeEditor'
import Verdict, { toneFor } from '../ui/Verdict'
import Workbench, { EditorTile } from './Workbench'
import { LevelNote, Panel, toastAwards } from './shared'

const STEPS = [
  { after: 0, text: 'Compiling your fix…' },
  { after: 4, text: 'Running your fix against the tests…' },
  { after: 20, text: 'Still running. Slow programs take longer…' },
]

export default function DebugView({ item, onGraded }) {
  const [code, setCode] = useState(item.buggy_code)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const lang = languageLabel(item.language)

  const submit = async () => {
    setBusy(true)
    try {
      const { data } = await assessmentAPI.submitDebug(item.id, code)
      setResult(data)
      toastAwards(data)
      onGraded(data.mastery_after)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't reach the code runner. Try again in a minute."))
    } finally {
      setBusy(false)
    }
  }

  const problem = (
    <Panel eyebrow="Your task">
      <div className="flex items-start gap-3 rounded-2xl border border-pop-pink/25 bg-pop-pink/[0.06] p-4">
        <Bug size={18} className="mt-0.5 shrink-0 text-pop-pink" />
        <p className="text-sm leading-relaxed text-ink">
          This <span className="font-semibold">{lang}</span> program has one planted bug. Find it and fix it, then submit.
        </p>
      </div>
      <RichText text={item.statement} className="mt-4 text-[15px] text-ink-muted" />
    </Panel>
  )

  const editor = (
    <>
      <EditorTile
        toolbar={
          <>
            <span className="flex items-center gap-2 text-sm font-medium text-ink">
              <span className="rounded-md bg-tile-3 px-2 py-0.5 font-mono text-xs">{lang}</span> Fix the program
            </span>
            <Button size="sm" variant="ghost" icon={RotateCcw} onClick={() => setCode(item.buggy_code)} disabled={busy || code === item.buggy_code}>
              Reset code
            </Button>
          </>
        }
        footer={
          <Button icon={Send} onClick={submit} busy={busy} disabled={result?.fixed}>
            {busy ? 'Running…' : result ? 'Submit again' : 'Submit fix'}
          </Button>
        }
      >
        <CodeEditor value={code} onChange={setCode} language={item.language} readOnly={busy || result?.fixed} minHeight="320px" maxHeight="620px" label={`${lang} program to fix`} />
      </EditorTile>

      <BusyNote active={busy} steps={STEPS} />

      {result && !busy && (
        <Verdict
          tone={result.fixed ? 'correct' : toneFor(result.tests_passed, result.tests_total)}
          title={result.fixed ? 'Fixed' : 'Not fixed yet'}
          meta={`${result.tests_passed}/${result.tests_total} tests passed`}
        >
          <div className="flex flex-col gap-1">
            {result.verdict && <p>{result.verdict}</p>}
            <LevelNote after={result.mastery_after} />
          </div>
          {!result.fixed && result.failing_input != null && (
            <CaseBlock input={result.failing_input} expected={result.failing_expected} actual={result.failing_actual} />
          )}
        </Verdict>
      )}
    </>
  )

  return <Workbench problem={problem} editor={editor} />
}
