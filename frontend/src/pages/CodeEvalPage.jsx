import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lightbulb, MessageSquareText, Play, RefreshCw, SquareTerminal, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../hooks/useAuth'
import { useCodeEval } from '../hooks/useCodeEval'
import { feedbackAPI, getErrorMessage } from '../utils/api'
import CodeEditor, { TEMPLATES } from '../components/code_eval/CodeEditor'
import ScoreRadar from '../components/code_eval/ScoreRadar'
import IssuesList from '../components/code_eval/IssuesList'
import FeedbackPanel from '../components/code_eval/FeedbackPanel'
import SubmissionHistory from '../components/code_eval/SubmissionHistory'
import AgentSteps from '../components/code_eval/AgentSteps'
import TestResults from '../components/code_eval/TestResults'
import ProblemBank from '../components/code_eval/ProblemBank'
import ProblemStatement from '../components/code_eval/ProblemStatement'
import AppShell from '../components/ui/AppShell'
import PageHeader from '../components/ui/PageHeader'
import Button from '../components/ui/Button'
import Tabs from '../components/ui/Tabs'
import EmptyState from '../components/ui/EmptyState'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import HintLadder from '../components/ui/HintLadder'
import Verdict from '../components/ui/Verdict'
import { TextArea } from '../components/ui/Field'

const TABS = [
  { value: 'scores', label: 'Scores' },
  { value: 'tests', label: 'Tests' },
  { value: 'issues', label: 'Issues' },
  { value: 'feedback', label: 'Feedback' },
]

function Step({ n, title, hint, children, aside }) {
  return (
    <section className="tile p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-3 text-[15px] font-semibold text-ink">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-tile-3 font-mono text-xs text-ink-muted">{n}</span>
          {title}
          {hint && <span className="text-xs font-normal text-ink-subtle">{hint}</span>}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export default function CodeEvalPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const {
    submissions, activeResult, activeSubmission, stats,
    evaluating, loading, error,
    fetchSubmissions, openSubmission, submitAndEvaluate,
    reEvaluate, fetchStats, deleteSubmission,
  } = useCodeEval()

  const defaultLanguage = user?.preferred_language || 'c'
  const [code, setCode] = useState(TEMPLATES[defaultLanguage])
  const [language, setLanguage] = useState(defaultLanguage)
  const [title, setTitle] = useState('')
  const [problemContext, setProblemCtx] = useState('')
  const [expectedOutput, setExpectedOut] = useState('')
  const [picked, setPicked] = useState(null)
  const [activeTab, setActiveTab] = useState('scores')
  const [toDelete, setToDelete] = useState(null)
  const [moreHints, setMoreHints] = useState({ evaluationId: null, list: [] })
  const [hinting, setHinting] = useState(false)
  const resultRef = useRef(null)

  useEffect(() => {
    fetchSubmissions()
    fetchStats()
  }, [])

  useEffect(() => {
    if (activeResult) {
      setActiveTab('scores')
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    }
  }, [activeResult?.id])

  useEffect(() => {
    if (activeSubmission) {
      setCode(activeSubmission.code || '')
      setLanguage(activeSubmission.language || defaultLanguage)
      setTitle(activeSubmission.title || '')
      setProblemCtx(activeSubmission.problem_context || '')
      setExpectedOut(activeSubmission.expected_output || '')
    }
  }, [activeSubmission?.id])

  // Swapping language swaps the starter code, but only while it is still a starter.
  const handleLanguageChange = (next) => {
    const untouched = !code.trim() || Object.values(TEMPLATES).includes(code)
    setLanguage(next)
    if (untouched && TEMPLATES[next]) setCode(TEMPLATES[next])
  }

  const handleEvaluate = () => submitAndEvaluate({
    language, code, title, problemContext, expectedOutput, problemId: picked?.id,
  })

  const handleReEval = async (id) => {
    await openSubmission(id)
    await reEvaluate(id)
  }

  const evaluationId = activeResult?.evaluation_id
  const hints = activeResult ? [
    ...(activeResult.hint ? [activeResult.hint] : []),
    ...(moreHints.evaluationId === evaluationId ? moreHints.list : []),
  ] : []
  const passed = Boolean(activeResult && activeResult.tests_total > 0 && activeResult.tests_passed === activeResult.tests_total)
  const topLevel = hints.length ? hints[hints.length - 1].level : 0
  const canHint = Boolean(activeResult?.problem_id && activeResult.verification_status === 'verified' && !passed && topLevel < 4)

  const moreHelp = async () => {
    setHinting(true)
    try {
      const { data } = await feedbackAPI.hint(activeResult.problem_id)
      setMoreHints(prev => ({
        evaluationId,
        list: [...(prev.evaluationId === evaluationId ? prev.list : []), data],
      }))
    } catch (err) {
      toast.error(getErrorMessage(err, 'No hint is available right now.'))
    } finally {
      setHinting(false)
    }
  }

  const results = (
    <section ref={resultRef} className="tile scroll-mt-6 p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="eyebrow">Results</p>
        {activeResult && !evaluating && (
          <Tabs tabs={TABS} value={activeTab} onChange={setActiveTab} label="Result sections" size="sm" />
        )}
      </div>

      {evaluating && <AgentSteps evaluating />}

      {!evaluating && !activeResult && error && (
        <Verdict tone="wrong" title="Couldn't evaluate your code">
          <p className="break-words">{error.message}</p>
          <p className="mt-2 text-xs text-ink-subtle">Your code is still in the editor. If it timed out, the result may have been saved anyway: check your saved attempts below.</p>
          <Button size="sm" variant="secondary" icon={RefreshCw} onClick={handleEvaluate} className="mt-4">Try again</Button>
        </Verdict>
      )}

      {!evaluating && !activeResult && !error && (
        <EmptyState
          icon={SquareTerminal}
          title="Your results show up here"
          body="Write or paste code, then press Evaluate. We run it in a sandbox against real tests, so the score is counted, not guessed."
        />
      )}

      {!evaluating && activeResult && (
        <div className="space-y-4 motion-safe:animate-rise">
          {activeTab === 'scores' && <ScoreRadar scores={activeResult.scores} unverifiedReason={activeResult.unverified_reason} />}
          {activeTab === 'tests' && <TestResults result={activeResult} />}
          {activeTab === 'issues' && <IssuesList issues={activeResult.issues} />}
          {activeTab === 'feedback' && <FeedbackPanel evaluation={{ ...activeResult, complexity: activeResult.metrics || {} }} />}
          {hints.length > 0 && !passed && <HintLadder hints={hints} />}
          {canHint && (
            <Button variant="hint" size="sm" icon={Lightbulb} onClick={moreHelp} busy={hinting}>
              {topLevel === 0 ? 'Get a hint' : 'Stronger hint'}
            </Button>
          )}
          <AgentSteps steps={activeResult.agent_steps || []} />
          <div className="flex flex-col gap-3 rounded-[20px] border border-pop-pink/20 bg-pop-pink/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ink-muted">Want a written report on this attempt and your recent work?</p>
            <Button
              size="sm"
              icon={MessageSquareText}
              onClick={() => navigate('/feedback', { state: { evaluation_id: activeResult.evaluation_id } })}
            >
              Open Feedback
            </Button>
          </div>
        </div>
      )}
    </section>
  )

  return (
    <AppShell title="Code workspace">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-5">
        <PageHeader
          eyebrow="Code workspace"
          title="Test any code you write"
          description="Bring a problem and your code. We run it against tests and review it."
          actions={stats && stats.total_evaluations > 0 && (
            <div className="flex items-center gap-3 rounded-full border border-line-strong px-4 py-2 font-mono text-xs text-ink-subtle">
              <span>Average <span className="text-ink">{stats.avg_overall_score.toFixed(0)}</span></span>
              <span className="text-ink-faint">·</span>
              <span>Best <span className="text-pop-mint">{stats.best_score.toFixed(0)}</span></span>
              {stats.improvement_trend > 0 && <TrendingUp size={13} className="text-pop-mint" aria-label="Improving" />}
            </div>
          )}
        />

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_440px] xl:items-start">
          <div className="flex min-w-0 flex-col gap-5">
            <Step n="1" title="Pick a problem" hint="optional">
              <ProblemBank
                selected={picked}
                onPick={(p) => { setPicked(p); setTitle(t => t || p.title) }}
                onClear={() => setPicked(null)}
              />
            </Step>

            <Step n="2" title="The problem">
              {picked ? (
                <ProblemStatement problem={picked} />
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
                  <TextArea
                    label="What should your code do?"
                    helper="Describe one test case. Your program gets T on the first line and must loop over T of them."
                    value={problemContext}
                    onChange={e => setProblemCtx(e.target.value)}
                    placeholder="e.g. Read n numbers and print their sum."
                    rows={4}
                  />
                  <TextArea
                    label="Expected output"
                    optional
                    value={expectedOutput}
                    onChange={e => setExpectedOut(e.target.value)}
                    placeholder="e.g. 15"
                    rows={4}
                    mono
                  />
                </div>
              )}
            </Step>

            <Step
              n="3"
              title="Your code"
              aside={
                <Button icon={Play} onClick={handleEvaluate} busy={evaluating} disabled={!code.trim()}>
                  {evaluating ? 'Evaluating…' : 'Evaluate'}
                </Button>
              }
            >
              <CodeEditor
                code={code} setCode={setCode}
                language={language} setLanguage={handleLanguageChange}
                title={title} setTitle={setTitle}
                evaluating={evaluating}
              />
              <p className="mt-3 text-xs text-ink-subtle">
                Try it with what you know first. If an evaluation of a picked problem fails, hints appear with the result.
              </p>
            </Step>
          </div>

          <div className="flex min-w-0 flex-col gap-5 xl:sticky xl:top-8">
            {results}
            <section className="tile p-5 sm:p-6">
              <div className="mb-4 flex items-center justify-between">
                <p className="eyebrow">Saved attempts</p>
                <span className="font-mono text-xs text-ink-faint">{submissions.length}</span>
              </div>
              <div className="max-h-[420px] overflow-y-auto pr-1">
                <SubmissionHistory
                  submissions={submissions}
                  activeId={activeSubmission?.id}
                  loading={loading}
                  disabled={evaluating}
                  onSelect={openSubmission}
                  onDelete={setToDelete}
                  onReEval={handleReEval}
                />
              </div>
            </section>
          </div>
        </div>

      </div>

      <ConfirmDialog
        open={toDelete != null}
        title="Delete this attempt?"
        body="The code and its results are removed for good. This can't be undone."
        confirmLabel="Delete"
        tone="danger"
        onCancel={() => setToDelete(null)}
        onConfirm={() => { deleteSubmission(toDelete); setToDelete(null) }}
      />
    </AppShell>
  )
}
