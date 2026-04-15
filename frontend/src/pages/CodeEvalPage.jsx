import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Sparkles, Menu, X, Code2, TrendingUp, MessageSquare
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useCodeEval } from '../hooks/useCodeEval'
import CodeEditor from '../components/code_eval/CodeEditor'
import ScoreRadar from '../components/code_eval/ScoreRadar'
import IssuesList from '../components/code_eval/IssuesList'
import FeedbackPanel from '../components/code_eval/FeedbackPanel'
import SubmissionHistory from '../components/code_eval/SubmissionHistory'
import AgentSteps from '../components/code_eval/AgentSteps'

const TABS = [
  { key: 'scores',   label: 'Scores'   },
  { key: 'issues',   label: 'Issues'   },
  { key: 'feedback', label: 'Feedback' },
  { key: 'code',     label: 'Improved Code', hideWhenEmpty: true },
]

export default function CodeEvalPage() {
  const { user }  = useAuth()
  const navigate  = useNavigate()

  const {
    submissions, activeResult, activeSubmission, stats,
    evaluating, loading,
    fetchSubmissions, openSubmission, submitAndEvaluate,
    reEvaluate, fetchStats, deleteSubmission,
  } = useCodeEval()

  // Editor state
  const [code,           setCode]       = useState('')
  const [language,       setLanguage]   = useState('python')
  const [title,          setTitle]      = useState('')
  const [problemContext, setProblemCtx] = useState('')
  const [expectedOutput, setExpectedOut]= useState('')

  // UI state
  const [activeTab,      setActiveTab]   = useState('scores')
  const [showHistory,    setShowHistory] = useState(true)
  const [showSteps,      setShowSteps]   = useState(false)
  const [showProblem,    setShowProblem] = useState(true)   // problem statement always visible
  const resultRef                        = useRef(null)

  useEffect(() => {
    fetchSubmissions()
    fetchStats()
  }, [])

  // Scroll to result when evaluation finishes
  useEffect(() => {
    if (activeResult) {
      setActiveTab('scores')
      setShowSteps(true)
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    }
  }, [activeResult?.id])   // only trigger on NEW result

  // ── When a submission is opened from history, load its code into the editor ──
  useEffect(() => {
    if (activeSubmission) {
      setCode(activeSubmission.code || '')
      setLanguage(activeSubmission.language || 'python')
      setTitle(activeSubmission.title || '')
      setProblemCtx(activeSubmission.problem_context || '')
      setExpectedOut(activeSubmission.expected_output || '')
    }
  }, [activeSubmission?.id])

  const handleEvaluate = async () => {
    setShowSteps(true)
    await submitAndEvaluate({ language, code, title, problemContext, expectedOutput })
  }

  // clicking a history item → load code + show its last evaluation
  const handleSelectHistory = async (id) => {
    await openSubmission(id)   // sets activeSubmission + activeResult inside hook
  }

  // re-evaluate an existing submission (already loaded in editor)
  const handleReEval = async (id) => {
    setShowSteps(true)
    // Open the submission first so its code loads into editor
    await openSubmission(id)
    // Then re-run the agent
    await reEvaluate(id)
  }

  const visibleTabs = TABS.filter(t => {
    if (t.hideWhenEmpty && !activeResult?.corrected_code) return false
    return true
  })

  return (
    <div className="h-screen flex flex-col overflow-hidden">

      {/* ── Navbar ── */}
      <nav className="shrink-0 border-b border-white/[0.06] bg-surface-900/90 backdrop-blur-xl z-40">
        <div className="h-14 flex items-center px-4 gap-3">
          <button onClick={() => navigate('/dashboard')}
            className="p-2 text-white/40 hover:text-white/70 rounded-xl hover:bg-surface-700 transition-all">
            <ArrowLeft size={18} />
          </button>
          <button onClick={() => setShowHistory(v => !v)}
            className="p-2 text-white/40 hover:text-white/70 rounded-xl hover:bg-surface-700 transition-all">
            {showHistory ? <X size={18} /> : <Menu size={18} />}
          </button>

          <div className="flex items-center gap-2 mr-auto">
            <div className="w-7 h-7 rounded-lg bg-orange-600 flex items-center justify-center">
              <Code2 size={14} className="text-white" />
            </div>
            <span className="font-display font-700 text-sm text-white hidden sm:block">
              Code <span className="text-orange-400">Evaluation</span> Agent
            </span>
          </div>

          {/* Stats pill */}
          {stats && stats.total_evaluations > 0 && (
            <div className="hidden md:flex items-center gap-3 px-3 py-1.5 bg-surface-700/60 rounded-xl border border-white/[0.06] text-xs font-mono">
              <span className="text-white/40">Avg</span>
              <span className="text-brand-400 font-600">{stats.avg_overall_score.toFixed(0)}</span>
              <span className="text-white/20">·</span>
              <span className="text-white/40">Best</span>
              <span className="text-green-400 font-600">{stats.best_score.toFixed(0)}</span>
              {stats.improvement_trend > 0 && (
                <><span className="text-white/20">·</span>
                  <TrendingUp size={12} className="text-green-400" /></>
              )}
            </div>
          )}
        </div>
      </nav>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Submission history sidebar */}
        {showHistory && (
          <div className="w-60 shrink-0 overflow-hidden hidden sm:block">
            <SubmissionHistory
              submissions={submissions}
              activeId={activeSubmission?.id}
              loading={loading}
              onSelect={handleSelectHistory}
              onDelete={deleteSubmission}
              onReEval={handleReEval}
            />
          </div>
        )}

        {/* ── Main split pane ── */}
        <div className="flex flex-1 overflow-hidden">

          {/* Left: problem statement + code editor stacked */}
          <div className="flex-1 flex flex-col overflow-hidden border-r border-white/[0.06] min-w-0">

            {/* ── Step 1: Problem Statement ── */}
            <div className="shrink-0 border-b border-white/[0.06] bg-surface-800/50">
              <button
                onClick={() => setShowProblem(v => !v)}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-surface-700/30 transition-colors"
              >
                <div className="w-5 h-5 rounded-md bg-orange-600/20 border border-orange-500/30 flex items-center justify-center shrink-0">
                  <span className="text-orange-400 text-xs font-mono font-700">1</span>
                </div>
                <span className="text-xs font-display font-600 text-white/60">Problem Statement</span>
                {problemContext && (
                  <span className="ml-1 px-1.5 py-0.5 bg-orange-600/15 border border-orange-500/20 rounded text-orange-400 text-xs font-mono">filled</span>
                )}
                <span className="ml-auto text-white/20 text-xs font-mono">{showProblem ? '▲' : '▼'}</span>
              </button>

              {showProblem && (
                <div className="px-4 pb-3 grid grid-cols-2 gap-3 animate-slide-up">
                  <div>
                    <p className="text-white/30 text-xs font-mono mb-1.5">
                      Describe the problem your code should solve
                    </p>
                    <textarea
                      value={problemContext}
                      onChange={e => setProblemCtx(e.target.value)}
                      placeholder="e.g. Given an array of integers, return indices of the two numbers that add up to a target..."
                      rows={4}
                      className="w-full bg-surface-700/40 border border-white/[0.06] rounded-xl px-3 py-2.5 text-xs text-white/70 placeholder-white/20 font-body resize-none focus:outline-none focus:border-orange-500/30 transition-colors"
                    />
                  </div>
                  <div>
                    <p className="text-white/30 text-xs font-mono mb-1.5">
                      Expected output <span className="text-white/20">(optional)</span>
                    </p>
                    <textarea
                      value={expectedOutput}
                      onChange={e => setExpectedOut(e.target.value)}
                      placeholder="e.g. [0, 1]"
                      rows={4}
                      className="w-full bg-surface-700/40 border border-white/[0.06] rounded-xl px-3 py-2.5 text-xs font-mono text-white/70 placeholder-white/20 resize-none focus:outline-none focus:border-orange-500/30 transition-colors"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* ── Step 2: Code Editor ── */}
            <div className="shrink-0 px-4 py-2 bg-surface-800/30 border-b border-white/[0.06] flex items-center gap-2">
              <div className="w-5 h-5 rounded-md bg-orange-600/20 border border-orange-500/30 flex items-center justify-center shrink-0">
                <span className="text-orange-400 text-xs font-mono font-700">2</span>
              </div>
              <span className="text-xs font-display font-600 text-white/60">Your Code</span>
            </div>

            <CodeEditor
              code={code}                 setCode={setCode}
              language={language}         setLanguage={setLanguage}
              title={title}               setTitle={setTitle}
              problemContext={problemContext} setProblemContext={setProblemCtx}
              expectedOutput={expectedOutput} setExpectedOutput={setExpectedOut}
              onEvaluate={handleEvaluate}
              evaluating={evaluating}
              hideProblemPanel   // tell CodeEditor not to show its own context panel
            />
          </div>

          {/* Right: results panel */}
          <div className="w-[480px] shrink-0 flex flex-col overflow-hidden bg-surface-900/30">

            {/* Agent steps */}
            {showSteps && (evaluating || activeResult?.agent_steps?.length > 0) && (
              <div className="shrink-0 px-4 pt-4">
                <AgentSteps
                  steps={activeResult?.agent_steps || []}
                  evaluating={evaluating}
                />
              </div>
            )}

            {/* Empty state */}
            {!evaluating && !activeResult && (
              <div className="flex flex-col items-center justify-center h-full text-center px-8">
                <div className="w-16 h-16 rounded-2xl bg-orange-600/10 border border-orange-500/20 flex items-center justify-center mb-4">
                  <Sparkles size={28} className="text-orange-400" />
                </div>
                <h3 className="font-display font-700 text-white text-lg mb-2">Ready to evaluate</h3>
                <p className="text-white/30 text-sm leading-relaxed max-w-xs">
                  Write or paste code → click <span className="text-orange-400 font-600">Evaluate</span>.
                  Or click any item in history to reload it.
                </p>
                <div className="mt-6 glass-card p-4 text-left w-full max-w-xs">
                  <p className="text-white/20 text-xs font-mono uppercase tracking-wider mb-3">Agent pipeline</p>
                  {[
                    '🔍 Static analysis (10 rule categories)',
                    '📊 6-dimension scoring',
                    '✦  Format button — auto-indent & clean',
                    '🤖 Groq LLM deep review',
                    '✏️  Corrected code with comments',
                    '📚 Personalised learning points',
                  ].map((item, i) => (
                    <p key={i} className="text-white/40 text-xs mb-1.5">{item}</p>
                  ))}
                </div>
              </div>
            )}

            {/* Results tabs */}
            {!evaluating && activeResult && (
              <div className="flex flex-col flex-1 overflow-hidden" ref={resultRef}>
                {/* Tab bar */}
                <div className="shrink-0 flex items-center gap-1 px-4 py-3 border-b border-white/[0.06]">
                  {visibleTabs.map(tab => (
                    <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-display font-600 transition-all ${
                        activeTab === tab.key
                          ? 'bg-brand-600/15 text-brand-300 border border-brand-500/25'
                          : 'text-white/35 hover:text-white/60'
                      }`}>
                      {tab.label}
                    </button>
                  ))}
                  <button onClick={() => setShowSteps(v => !v)}
                    className="ml-auto text-white/20 hover:text-white/50 text-xs font-mono transition-colors">
                    {showSteps ? 'Hide log' : 'Show log'}
                  </button>
                </div>

                {/* Tab content */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                  {activeTab === 'scores' && (
                    <ScoreRadar scores={activeResult.scores} />
                  )}
                  {activeTab === 'issues' && (
                    <IssuesList issues={activeResult.issues} />
                  )}
                  {activeTab === 'feedback' && (
                    <FeedbackPanel evaluation={{
                      ...activeResult,
                      complexity: {
                        time_complexity:       activeResult.time_complexity       ?? activeResult.complexity?.time_complexity,
                        space_complexity:      activeResult.space_complexity      ?? activeResult.complexity?.space_complexity,
                        cyclomatic_complexity: activeResult.cyclomatic_complexity ?? activeResult.complexity?.cyclomatic_complexity,
                        lines_of_code:         activeResult.lines_of_code         ?? activeResult.complexity?.lines_of_code,
                      }
                    }} />
                  )}
                  {activeTab === 'code' && activeResult.corrected_code && (
                    <div className="glass-card overflow-hidden">
                      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
                        <p className="font-display font-600 text-sm text-white">Improved Code</p>
                        <button
                          onClick={() => setCode(activeResult.corrected_code)}
                          className="text-brand-400 text-xs font-display font-600 hover:text-brand-300 transition-colors">
                          Load into editor →
                        </button>
                      </div>
                      <pre className="overflow-x-auto p-4 text-xs font-mono text-green-300/85 leading-6 bg-[#0d1117] max-h-[60vh]">
                        <code>{activeResult.corrected_code}</code>
                      </pre>
                    </div>
                  )}

                  {/* ── Pipeline Step 5: Feedback Agent CTA ── */}
                  <div className="glass-card p-4 border-pink-500/15">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-display font-700 text-sm text-white mb-1">
                          Get personalised feedback → Step 5
                        </p>
                        <p className="text-white/30 text-xs leading-relaxed">
                          The Feedback Agent synthesises this evaluation into rich,
                          context-aware feedback and updates your learning profile.
                        </p>
                      </div>
                      <button
                        onClick={() => navigate('/feedback', {
                          state: { evaluation_id: activeResult.id }
                        })}
                        className="flex items-center gap-1.5 px-3 py-2 bg-pink-600 hover:bg-pink-500 text-white text-xs font-display font-600 rounded-xl transition-all shrink-0 active:scale-95"
                      >
                        <MessageSquare size={13} /> Get Feedback
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}