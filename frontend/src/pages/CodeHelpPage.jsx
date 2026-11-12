import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  ArrowLeft, BookOpen, Eye, Flag, Lightbulb, Lock, MessageSquareText, Play, RefreshCw, RotateCcw, Send, Shapes, Sparkles,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { problemsAPI, codeEvalAPI, feedbackAPI, getErrorMessage } from '../utils/api'
import { LANGUAGES, TEMPLATES } from '../components/code/templates'
import { TOPIC_LABELS, languageLabel } from '../components/learning/labels'
import ChatPanel from '../components/chat/ChatPanel'
import AppShell from '../components/ui/AppShell'
import PageHeader from '../components/ui/PageHeader'
import Button from '../components/ui/Button'
import Chip from '../components/ui/Chip'
import Tabs from '../components/ui/Tabs'
import BusyNote from '../components/ui/BusyNote'
import CodeEditor from '../components/ui/CodeEditor'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import EmptyState from '../components/ui/EmptyState'
import { TextField } from '../components/ui/Field'
import CaseBlock, { OutputBlock } from '../components/ui/CaseBlock'
import HintLadder from '../components/ui/HintLadder'
import Verdict, { toneFor } from '../components/ui/Verdict'
import Workbench, { EditorTile, LanguagePicker } from '../components/practice/Workbench'
import { toastAwards } from '../components/practice/shared'

const DIFFICULTIES = [
  { value: 'easy', label: 'Easy', tone: 'mint' },
  { value: 'medium', label: 'Medium', tone: 'sun' },
  { value: 'hard', label: 'Hard', tone: 'coral' },
  { value: 'expert', label: 'Expert', tone: 'pink' },
]
const DIFF_TONE = Object.fromEntries(DIFFICULTIES.map(d => [d.value, d.tone]))

const GENERATE_STEPS = [
  { after: 0, text: 'Writing a new problem for you…' },
  { after: 8, text: 'Writing the test cases…' },
  { after: 25, text: 'Checking the problem works. Almost there…' },
  { after: 60, text: 'Taking longer than usual. Please keep this page open…' },
]
const SOLUTION_STEPS = [
  { after: 0, text: 'Getting the solution…' },
  { after: 5, text: 'Writing it in your language and checking it against the tests…' },
  { after: 45, text: 'Taking longer than usual. Please keep this page open…' },
]
const RUN_STEPS = [{ after: 0, text: 'Running your code on the example tests…' }, { after: 10, text: 'Still running…' }]
const SUBMIT_STEPS = [
  { after: 0, text: 'Compiling your code…' },
  { after: 4, text: 'Running your code against all the tests…' },
  { after: 15, text: 'Scoring correctness, efficiency and style…' },
  { after: 60, text: 'Taking longer than usual. Please keep this page open…' },
]

function loadHistory() {
  try { return JSON.parse(localStorage.getItem('codehelp_history') || '[]') } catch { return [] }
}

function ScoreBreakdown({ scores }) {
  const items = [
    { label: 'Overall', val: scores?.overall },
    { label: 'Correctness', val: scores?.correctness },
    { label: 'Efficiency', val: scores?.efficiency },
    { label: 'Style', val: scores?.style },
  ]
  const tone = v => (v >= 70 ? 'text-pop-mint' : v >= 50 ? 'text-pop-sun' : 'text-pop-coral')
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {items.map(s => (
        <div key={s.label} className="rounded-2xl border border-line bg-canvas/60 px-3 py-3">
          <dd className={`font-mono text-2xl font-semibold ${tone(s.val || 0)}`}>{Math.round(s.val || 0)}</dd>
          <dt className="mt-0.5 text-[11px] text-ink-subtle">{s.label} <span className="text-ink-faint">/ 100</span></dt>
        </div>
      ))}
    </dl>
  )
}

export default function CodeHelpPage() {
  const { user } = useAuth()
  const location = useLocation()

  const [phase, setPhase] = useState('setup')
  const [topic, setTopic] = useState(location.state?.topic || '')
  const [difficulty, setDiff] = useState('medium')
  const [language, setLang] = useState(user?.preferred_language || 'c')

  const [problem, setProblem] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [seenTitles, setSeenTitles] = useState([])
  // Bank picks are ordered by id: without these, "new problem" returns the same one.
  const [seenIds, setSeenIds] = useState([])

  const [code, setCode] = useState('')
  const [activeTab, setActiveTab] = useState('problem')
  const [gaveUp, setGaveUp] = useState(false)
  const [confirmGiveUp, setConfirmGiveUp] = useState(false)
  const [solution, setSolution] = useState(null)
  const [solutionLoading, setSolutionLoading] = useState(false)
  const [historyId, setHistoryId] = useState(null)

  const [running, setRunning] = useState(false)
  const [runResults, setRunResults] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [evalResult, setEvalResult] = useState(null)
  const [hints, setHints] = useState([])
  const [hinting, setHinting] = useState(false)
  const [history, setHistory] = useState(loadHistory)

  const saveHistory = list => {
    setHistory(list)
    try { localStorage.setItem('codehelp_history', JSON.stringify(list)) } catch { /* storage full or blocked */ }
  }

  const resetSeen = () => { setSeenTitles([]); setSeenIds([]) }

  // Swapping language swaps the starter code, but only while it is still a starter.
  const handleLanguageChange = (next) => {
    const starters = [...Object.values(TEMPLATES), problem?.starter_code]
    const untouched = !code.trim() || starters.includes(code)
    setLang(next)
    setSolution(null)
    if (untouched && TEMPLATES[next]) setCode(TEMPLATES[next])
  }

  const generateProblem = async () => {
    if (!topic.trim()) { toast.error('Enter a topic first'); return }
    setGenerating(true)
    try {
      const { data } = await problemsAPI.generate({
        topic, difficulty, language, exclude_titles: seenTitles, exclude_ids: seenIds,
      })
      setProblem(data)
      setCode(data.starter_code || TEMPLATES[language] || '')
      setActiveTab('problem')
      setEvalResult(null)
      setRunResults(null)
      setHints([])
      setGaveUp(false)
      setSolution(null)
      if (data.title) setSeenTitles(prev => [...new Set([...prev, data.title])])
      if (data.problem_id) setSeenIds(prev => [...new Set([...prev, data.problem_id])])

      const entryId = Date.now()
      setHistoryId(entryId)
      saveHistory([{ id: entryId, title: data.title, topic, difficulty, language, solvedAt: null, score: null, timestamp: entryId }, ...history].slice(0, 50))
      setPhase('problem')
      window.scrollTo({ top: 0 })
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't create a problem. Try again in a minute."))
    } finally {
      setGenerating(false)
    }
  }

  const runCode = async () => {
    if (!code.trim()) { toast.error('Write some code first'); return }
    if (!problem?.problem_id) { toast.error('This problem has no test cases to run.'); return }
    setRunning(true)
    setRunResults(null)
    try {
      const { data } = await codeEvalAPI.run({ problem_id: problem.problem_id, language, code })
      setRunResults({ ...data, error: data.compile_output || data.stderr || null })
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't reach the code runner. Try again in a minute."))
    } finally {
      setRunning(false)
    }
  }

  const submitCode = async () => {
    if (!code.trim()) { toast.error('Write some code first'); return }
    setSubmitting(true)
    try {
      const { data } = await codeEvalAPI.submitAndEvaluate({
        language,
        code,
        title: problem?.title || topic,
        // Bind by id so grading uses the stored problem's tests; the description fallback
        // would create a duplicate problem with a fresh suite.
        problem_id: problem?.problem_id,
        problem_context: problem?.description || '',
      })
      setEvalResult(data)
      setRunResults(null)
      setHints(data.hint ? [data.hint] : [])
      toastAwards(data)
      const score = Math.round(data.scores?.overall || 0)
      saveHistory(history.map(h => (h.id === historyId ? { ...h, score, solvedAt: new Date().toISOString() } : h)))
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't grade your code. Try again in a minute."))
    } finally {
      setSubmitting(false)
    }
  }

  const moreHelp = async () => {
    setHinting(true)
    try {
      const { data } = await feedbackAPI.hint(problem.problem_id)
      setHints(prev => [...prev, data])
    } catch (err) {
      toast.error(getErrorMessage(err, 'No hint is available right now.'))
    } finally {
      setHinting(false)
    }
  }

  // The server only hands the answer over after a pass or a recorded give-up.
  const hasSolution = Boolean(problem?.problem_id)
  const passed = Boolean(evalResult && evalResult.tests_total > 0 && evalResult.tests_passed === evalResult.tests_total)
  const solutionOpen = passed || gaveUp
  const topLevel = hints.length ? hints[hints.length - 1].level : 0
  const canHint = Boolean(evalResult && !passed && problem?.problem_id && topLevel < 4)

  const loadSolution = async (giveUp) => {
    setSolutionLoading(true)
    try {
      const { data } = await problemsAPI.solution(problem.problem_id, { language, give_up: giveUp })
      setSolution(data)
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't load the solution. Try again in a minute."))
    } finally {
      setSolutionLoading(false)
    }
  }

  const openSolution = () => {
    setActiveTab('solution')
    if (passed && !solution && !solutionLoading) loadSolution(false)
  }

  // The id lets the chat's tools run against this problem's stored tests.
  const firstExample = problem?.examples?.[0]
  const problemContext = problem ? [
    `${problem.title || topic}${problem.problem_id ? ` (problem_id ${problem.problem_id})` : ''}`,
    problem.description,
    firstExample && `Example input:\n${firstExample.input}\nExpected output:\n${firstExample.output}`,
    problem.constraints?.length > 0 && `Constraints:\n${problem.constraints.join('\n')}`,
  ].filter(Boolean).join('\n\n') : ''

  const suggestions = [...new Set([
    ...(user?.interested_topics || []).map(t => t.replace(/_/g, ' ')),
    ...Object.values(TOPIC_LABELS),
  ])]

  if (phase === 'setup') {
    return (
      <AppShell title="Coding problems">
        <div className="mx-auto grid max-w-[1180px] grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:items-start">
          <section className="tile p-6 sm:p-8">
            <PageHeader
              eyebrow="Coding problems"
              title="Practise any topic you choose"
              description="Pick a topic and a level. We write a fresh problem with test cases."
            />

            <div className="mt-8 space-y-7">
              <TextField
                label="Topic"
                helper="Type anything, like “two pointers” or “pattern printing”, or pick one below."
                placeholder="e.g. Arrays, Recursion, Strings"
                value={topic}
                onChange={e => { setTopic(e.target.value); resetSeen() }}
                onKeyDown={e => { if (e.key === 'Enter' && !generating) generateProblem() }}
                icon={Shapes}
                autoFocus
              />
              <div className="-mt-3 flex flex-wrap gap-2">
                {suggestions.map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => { setTopic(t); resetSeen() }}
                    aria-pressed={topic === t}
                    className={`min-h-[36px] rounded-full border px-3.5 text-[13px] transition-colors ${
                      topic === t ? 'border-ink bg-ink text-canvas' : 'border-line-strong text-ink-subtle hover:border-ink-faint hover:text-ink'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div role="radiogroup" aria-label="Difficulty">
                  <span className="mb-2.5 block text-[13px] font-medium text-ink-muted">Difficulty</span>
                  <div className="grid grid-cols-2 gap-2">
                    {DIFFICULTIES.map(d => (
                      <button
                        key={d.value}
                        type="button"
                        role="radio"
                        aria-checked={difficulty === d.value}
                        onClick={() => { setDiff(d.value); resetSeen() }}
                        className={`min-h-[44px] rounded-2xl border text-sm font-medium transition-colors ${
                          difficulty === d.value ? 'border-ink bg-ink text-canvas' : 'border-line-strong bg-tile-2 text-ink-muted hover:text-ink'
                        }`}
                      >
                        {d.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="mb-2.5 block text-[13px] font-medium text-ink-muted">Language</span>
                  <LanguagePicker languages={LANGUAGES} value={language} onChange={handleLanguageChange} />
                </div>
              </div>

              <div className="flex flex-col gap-4 border-t border-line pt-6">
                <Button size="lg" icon={Sparkles} onClick={generateProblem} disabled={!topic.trim()} busy={generating} className="self-start">
                  {generating ? 'Creating…' : 'Create a problem'}
                </Button>
                <BusyNote active={generating} steps={GENERATE_STEPS} note="New problems usually take 10 to 40 seconds." />
              </div>
            </div>
          </section>

          <section className="tile p-6">
            <p className="eyebrow">Recent problems</p>
            {history.length === 0 ? (
              <EmptyState className="mt-4" icon={BookOpen} title="Nothing here yet" body="Problems you create show up here with your score." />
            ) : (
              <ul className="mt-3 divide-y divide-line">
                {history.slice(0, 8).map(h => (
                  <li key={h.id} className="flex items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink">{h.title || h.topic}</p>
                      <p className="mt-0.5 truncate text-xs text-ink-subtle">{h.topic} · {languageLabel(h.language)}</p>
                    </div>
                    <Chip tone={DIFF_TONE[h.difficulty] || 'neutral'}>{h.difficulty}</Chip>
                    <span className={`w-14 text-right font-mono text-sm ${h.score == null ? 'text-ink-faint' : h.score >= 70 ? 'text-pop-mint' : 'text-pop-sun'}`}>
                      {h.score == null ? 'not tried' : `${h.score}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </AppShell>
    )
  }

  const tabs = [
    { value: 'problem', label: 'Problem', icon: BookOpen },
    { value: 'hints', label: 'Hints', icon: Lightbulb, badge: problem?.hints?.length || null },
    hasSolution && { value: 'solution', label: 'Solution', icon: solutionOpen ? Eye : Lock },
    { value: 'chat', label: 'Ask PET', icon: MessageSquareText },
  ].filter(Boolean)

  const left = (
    <section className={`tile flex flex-col ${activeTab === 'chat' ? 'h-[calc(100dvh-4rem)] min-h-[520px]' : ''}`}>
      <div className="border-b border-line p-3">
        <Tabs tabs={tabs} value={activeTab} onChange={v => (v === 'solution' ? openSolution() : setActiveTab(v))} label="Problem panels" size="sm" />
      </div>

      <div className={`${activeTab === 'chat' ? 'hidden' : ''} p-5 sm:p-6`}>
        {activeTab === 'problem' && (
          <div className="space-y-5">
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink-muted">{problem.description}</p>
            {problem.examples?.length > 0 && (
              <div className="space-y-3">
                <p className="eyebrow">Examples</p>
                {problem.examples.map((ex, i) => (
                  <div key={i} className="rounded-[18px] border border-line bg-tile-2 p-3">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                      <OutputBlock label="Input" value={ex.input} tone="aqua" />
                      <OutputBlock label="Output" value={ex.output} tone="mint" />
                    </div>
                    {ex.explanation && <p className="mt-3 text-[13px] leading-relaxed text-ink-subtle">{ex.explanation}</p>}
                  </div>
                ))}
              </div>
            )}
            {problem.constraints?.length > 0 && (
              <div>
                <p className="eyebrow">Constraints</p>
                <ul className="mt-2 space-y-1">
                  {problem.constraints.map((c, i) => <li key={i} className="font-mono text-[13px] text-ink-muted">{c}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === 'hints' && (
          problem.hints?.length > 0 ? (
            <ol className="space-y-3">
              {problem.hints.map((h, i) => (
                <li key={i} className="flex gap-3 rounded-[18px] border border-pop-sun/20 bg-pop-sun/[0.05] p-4">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-pop-sun font-mono text-xs font-semibold text-canvas">{i + 1}</span>
                  <span className="pt-0.5 text-sm leading-relaxed text-ink-muted">{h}</span>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState icon={Lightbulb} title="No hints for this problem" body="Try the Ask PET tab. It can give you a hint without the answer." />
          )
        )}

        {activeTab === 'solution' && hasSolution && (
          solutionOpen ? (
            <div className="space-y-5">
              {passed && <Chip tone="mint">You passed every test, so the solution is open.</Chip>}
              <BusyNote active={solutionLoading} steps={SOLUTION_STEPS} />
              {solution?.code && (
                <div>
                  <p className="eyebrow mb-2">Solution · {languageLabel(solution.language)}</p>
                  {solution.language === 'python' && language !== 'python' && (
                    <p className="mb-3 text-[13px] leading-relaxed text-ink-subtle">
                      There is no checked {languageLabel(language)} version of this solution yet, so here is the Python one. The steps are the same.
                    </p>
                  )}
                  <CodeEditor value={solution.code} language={solution.language} readOnly minHeight="160px" maxHeight="480px" label="Solution code" />
                </div>
              )}
              {solution && !solution.code && (
                <EmptyState icon={BookOpen} title="No model answer for this problem" body="Ask PET to walk you through the approach instead." />
              )}
              {!solution && !solutionLoading && (
                <Button size="sm" variant="secondary" icon={RotateCcw} onClick={() => loadSolution(gaveUp)}>Load the solution</Button>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-start gap-4 rounded-[20px] border border-dashed border-line-strong p-6">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-tile-3 text-ink-muted"><Lock size={20} /></span>
              <div>
                <p className="text-[15px] font-semibold text-ink">The solution opens when you pass</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-subtle">Pass every test and it unlocks on its own. Stuck? Try the hints first. You can also give up and see it now.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="hint" size="sm" icon={Lightbulb} onClick={() => setActiveTab('hints')}>See the hints</Button>
                <Button variant="ghost" size="sm" icon={Flag} onClick={() => setConfirmGiveUp(true)}>I give up</Button>
              </div>
            </div>
          )
        )}
      </div>

      {/* Kept mounted while hidden so a reply in progress survives a tab switch */}
      <div className={`${activeTab === 'chat' ? 'flex' : 'hidden'} min-h-0 flex-1 flex-col p-2`}>
        <ChatPanel
          key={problem?.problem_id || problem?.title}
          problemContext={problemContext}
          defaultLanguage={language}
          getCode={() => ({ code, language })}
          className="flex-1 !border-0 !bg-transparent !shadow-none"
        />
      </div>
    </section>
  )

  const right = (
    <>
      <EditorTile
        toolbar={
          <>
            <LanguagePicker languages={LANGUAGES} value={language} onChange={handleLanguageChange} disabled={running || submitting} />
            <Button size="sm" variant="ghost" icon={RotateCcw} onClick={() => setCode(problem?.starter_code || TEMPLATES[language] || '')} disabled={running || submitting}>
              Reset code
            </Button>
          </>
        }
        footer={
          <>
            <Button variant="secondary" icon={Play} onClick={runCode} busy={running} disabled={submitting || hinting || !code.trim()}>Run</Button>
            <Button icon={Send} onClick={submitCode} busy={submitting} disabled={running || hinting || !code.trim()}>Submit</Button>
            {canHint ? (
              <Button variant="hint" icon={Lightbulb} onClick={moreHelp} busy={hinting} disabled={running || submitting} className="sm:ml-auto">
                {topLevel === 0 ? 'Get a hint' : 'Stronger hint'}
              </Button>
            ) : (
              <span className="text-xs text-ink-subtle sm:ml-auto">Run checks the examples. Submit runs every test and scores your code. Try it with what you know first: hints open after a submission that fails.</span>
            )}
          </>
        }
      >
        <CodeEditor value={code} onChange={setCode} language={language} readOnly={submitting} minHeight="380px" maxHeight="640px" label="Your solution" />
      </EditorTile>

      <BusyNote active={running} steps={RUN_STEPS} />
      <BusyNote active={submitting} steps={SUBMIT_STEPS} note="This can take up to a minute." />

      {runResults && !running && (
        <Verdict
          tone={toneFor(runResults.passed, runResults.total)}
          title={runResults.verdict}
          meta={`${runResults.passed}/${runResults.total} example tests passed`}
        >
          {runResults.cases.filter(c => !c.passed).slice(0, 2).map((c, i) => (
            <CaseBlock key={i} input={c.input} expected={c.expected} actual={c.actual} />
          ))}
          {runResults.error && (
            <div className="mt-4"><OutputBlock label="Error output" value={runResults.error} tone="coral" /></div>
          )}
        </Verdict>
      )}

      {evalResult && !submitting && (
        <Verdict
          tone={evalResult.tests_total > 0 ? toneFor(evalResult.tests_passed, evalResult.tests_total) : 'neutral'}
          title={passed ? 'All tests passed' : evalResult.verdict || 'Graded'}
          meta={evalResult.tests_total > 0 ? `${evalResult.tests_passed}/${evalResult.tests_total} tests passed` : null}
        >
          <ScoreBreakdown scores={evalResult.scores} />
          {evalResult.summary && <p className="mt-4">{evalResult.summary}</p>}
          {evalResult.first_failing_case && (
            <CaseBlock
              input={evalResult.first_failing_case.stdin}
              expected={evalResult.first_failing_case.expected_stdout}
              actual={evalResult.first_failing_case.actual_stdout}
            />
          )}
          {evalResult.key_improvements?.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-ink">What to improve</p>
              <ul className="mt-2 space-y-1.5">
                {evalResult.key_improvements.slice(0, 3).map((imp, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-pop-sun" aria-hidden="true" />
                    <span>{imp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {passed && hasSolution && (
            <Button size="sm" variant="secondary" icon={Eye} className="mt-4" onClick={openSolution}>Compare with the solution</Button>
          )}
        </Verdict>
      )}

      {hints.length > 0 && !passed && <HintLadder hints={hints} />}
    </>
  )

  return (
    <AppShell title="Coding problems">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-5">
        <section className="tile flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={DIFF_TONE[problem?.difficulty] || 'neutral'}>{problem?.difficulty}</Chip>
              <Chip>{topic}</Chip>
              <Chip tone="aqua">{languageLabel(language)}</Chip>
            </div>
            <h1 className="mt-3 truncate text-2xl font-semibold tracking-tight text-ink">{problem?.title}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="ghost" icon={ArrowLeft} onClick={() => setPhase('setup')} disabled={generating}>Change topic</Button>
            <Button variant="secondary" icon={RefreshCw} onClick={generateProblem} busy={generating}>New problem, same topic</Button>
          </div>
        </section>

        <BusyNote active={generating} steps={GENERATE_STEPS} />

        <Workbench problem={left} editor={right} />
      </div>

      <ConfirmDialog
        open={confirmGiveUp}
        title="Show the full solution?"
        body="This shows the full solution. Try a hint first? Once you see the answer, the problem is much less useful for practice."
        cancelLabel="Try a hint first"
        confirmLabel="Show solution"
        tone="danger"
        onCancel={() => { setConfirmGiveUp(false); setActiveTab('hints') }}
        onClose={() => setConfirmGiveUp(false)}
        onConfirm={() => { setConfirmGiveUp(false); setGaveUp(true); loadSolution(true) }}
      />
    </AppShell>
  )
}
