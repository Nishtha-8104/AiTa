import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { contentPlayerAPI, codeEvalAPI } from '../utils/api'
import toast from 'react-hot-toast'
import {
  ArrowLeft, RefreshCw, Eye, EyeOff, Play, ChevronDown,
  CheckCircle2, Clock, Lightbulb, BookOpen, Send, Loader2,
  Code2, MessageSquare, Trophy, ChevronRight, X
} from 'lucide-react'

const DIFFICULTY_STYLE = {
  easy:   { color: '#10b981', bg: 'rgba(16,185,129,0.1)',   border: 'rgba(16,185,129,0.3)'  },
  medium: { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)',   border: 'rgba(245,158,11,0.3)'  },
  hard:   { color: '#ef4444', bg: 'rgba(239,68,68,0.1)',    border: 'rgba(239,68,68,0.3)'   },
  expert: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)',   border: 'rgba(139,92,246,0.3)'  },
}

const LANGUAGES = ['python', 'javascript', 'java', 'c++', 'go', 'rust']

// ── Markdown-lite renderer ────────────────────────────────────────────────────
function Md({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  return (
    <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: 14, lineHeight: 1.7 }}>
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} style={{ height: 8 }} />
        if (/^#{1,3} /.test(line)) {
          const content = line.replace(/^#+\s/, '')
          return <p key={i} style={{ fontWeight: 700, color: '#fff', margin: '12px 0 4px', fontSize: 15 }}>{content}</p>
        }
        if (/^[-*] /.test(line.trim())) {
          return (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
              <span style={{ color: '#14b8a6', flexShrink: 0, marginTop: 2 }}>▸</span>
              <span>{line.replace(/^[\s]*[-*] /, '')}</span>
            </div>
          )
        }
        return <p key={i} style={{ margin: '2px 0' }}>{line}</p>
      })}
    </div>
  )
}

export default function CodeHelpPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const prefillTopic = location.state?.topic || ''

  // ── Setup state ───────────────────────────────────────────────────────────
  const [phase, setPhase]         = useState('setup')   // setup | problem
  const [topic, setTopic]         = useState(prefillTopic)
  const [difficulty, setDiff]     = useState('medium')
  const [language, setLang]       = useState('python')

  // ── Problem state ─────────────────────────────────────────────────────────
  const [problem, setProblem]     = useState(null)
  const [generating, setGenerating] = useState(false)
  const [seenTitles, setSeenTitles] = useState([])  // track generated problem titles

  // ── Editor state ──────────────────────────────────────────────────────────
  const [code, setCode]           = useState('')
  const [showSolution, setShowSolution] = useState(false)
  const [activeTab, setActiveTab] = useState('problem')  // problem | hints | solution

  // ── AI chat state ─────────────────────────────────────────────────────────
  const [sessionId, setSessionId] = useState(null)
  const [chatMsgs, setChatMsgs]   = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef                = useRef(null)

  // ── Run state ─────────────────────────────────────────────────────────────
  const [running, setRunning]     = useState(false)
  const [runResults, setRunResults] = useState(null)  // null | { passed, total, cases }

  // ── Submission state ──────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false)
  const [evalResult, setEvalResult] = useState(null)
  const [showEval, setShowEval]   = useState(false)

  // ── History ───────────────────────────────────────────────────────────────
  const [history, setHistory]     = useState(() => {
    try { return JSON.parse(localStorage.getItem('codehelp_history') || '[]') }
    catch { return [] }
  })

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMsgs])

  // ── Generate problem ──────────────────────────────────────────────────────
  const generateProblem = async () => {
    if (!topic.trim()) { toast.error('Enter a topic first'); return }
    setGenerating(true)
    try {
      const { data } = await contentPlayerAPI.generateProblem({
        topic,
        difficulty,
        language,
        exclude_titles: seenTitles,   // tell backend which problems to skip
      })
      setProblem(data)
      setCode(data.starter_code || '')
      setShowSolution(false)
      setActiveTab('problem')
      setEvalResult(null)
      setChatMsgs([])
      setSessionId(null)

      // Track this title so it won't be generated again this session
      if (data.title) {
        setSeenTitles(prev => [...new Set([...prev, data.title])])
      }

      // Create a content player session for history
      const { data: session } = await contentPlayerAPI.createSession({
        mode: 'code_help',
        topic: data.title || topic,
        language,
        difficulty,
      })
      setSessionId(session.id)

      // Save to local history
      const entry = {
        id: session.id,
        title: data.title,
        topic,
        difficulty,
        language,
        solvedAt: null,
        score: null,
        timestamp: Date.now(),
      }
      const updated = [entry, ...history].slice(0, 50)
      setHistory(updated)
      localStorage.setItem('codehelp_history', JSON.stringify(updated))

      setPhase('problem')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate problem')
    } finally {
      setGenerating(false)
    }
  }

  // ── Run against test cases ────────────────────────────────────────────────
  const runCode = async () => {
    if (!code.trim()) { toast.error('Write some code first'); return }
    if (!problem?.examples?.length) { toast.error('No test cases available'); return }
    setRunning(true)
    setRunResults(null)
    try {
      // Ask the AI to run the code against each example and report pass/fail
      const testCases = problem.examples.map((ex, i) =>
        `Test ${i + 1}:\n  Input: ${ex.input}\n  Expected Output: ${ex.output}`
      ).join('\n\n')

      const prompt = `You are a code runner. Given this ${language} code and test cases, determine if the code would produce the correct output for each test case.

Code:
\`\`\`${language}
${code}
\`\`\`

Test Cases:
${testCases}

For each test case, respond ONLY with valid JSON (no markdown):
{
  "cases": [
    { "input": "...", "expected": "...", "actual": "...", "passed": true/false, "error": null or "error message" }
  ]
}

Simulate the execution mentally. If the code has a syntax error or would crash, set passed: false and error to the error message.`

      const { data } = await contentPlayerAPI.chat(sessionId, { message: prompt })

      // Parse JSON from response
      let parsed = null
      try {
        const jsonMatch = data.response.match(/\{[\s\S]*\}/)
        if (jsonMatch) parsed = JSON.parse(jsonMatch[0])
      } catch { /* ignore */ }

      if (parsed?.cases) {
        const passed = parsed.cases.filter(c => c.passed).length
        setRunResults({ passed, total: parsed.cases.length, cases: parsed.cases })
        if (passed === parsed.cases.length) toast.success(`All ${passed} test cases passed!`)
        else toast(`${passed}/${parsed.cases.length} test cases passed`, { icon: '🧪' })
      } else {
        // Fallback: show raw response
        setRunResults({ passed: 0, total: problem.examples.length, cases: [], raw: data.response })
      }
    } catch (err) {
      toast.error('Run failed. Try again.')
    } finally {
      setRunning(false)
    }
  }

  // ── Submit code for evaluation ────────────────────────────────────────────
  const submitCode = async () => {
    if (!code.trim()) { toast.error('Write some code first'); return }
    setSubmitting(true)
    try {
      const { data } = await codeEvalAPI.submitAndEvaluate({
        language,
        code,
        title: problem?.title || topic,
        problem_context: problem?.description || '',
      })
      setEvalResult(data)
      setShowEval(true)

      // Update history with score
      const score = Math.round(data.scores?.overall || 0)
      const updated = history.map(h =>
        h.id === sessionId ? { ...h, score, solvedAt: new Date().toISOString() } : h
      )
      setHistory(updated)
      localStorage.setItem('codehelp_history', JSON.stringify(updated))

      if (score >= 70) toast.success(`Score: ${score}/100 — Great work!`)
      else toast(`Score: ${score}/100 — Keep improving!`, { icon: '📊' })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Evaluation failed')
    } finally {
      setSubmitting(false)
    }
  }

  // ── AI hint chat ──────────────────────────────────────────────────────────
  const sendChat = async () => {
    if (!chatInput.trim() || !sessionId) return
    const msg = chatInput.trim()
    setChatInput('')
    setChatMsgs(prev => [...prev, { role: 'user', content: msg }])
    setChatLoading(true)
    try {
      const { data } = await contentPlayerAPI.chat(sessionId, {
        message: msg,
        code_snippet: code || undefined,
      })
      setChatMsgs(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch {
      setChatMsgs(prev => [...prev, { role: 'error', content: 'Failed to get hint.' }])
    } finally {
      setChatLoading(false)
    }
  }

  const diffStyle = DIFFICULTY_STYLE[difficulty] || DIFFICULTY_STYLE.medium
  const probDiffStyle = problem ? (DIFFICULTY_STYLE[problem.difficulty] || DIFFICULTY_STYLE.medium) : diffStyle

  // ── SETUP SCREEN ──────────────────────────────────────────────────────────
  if (phase === 'setup') {
    return (
      <div style={S.page}>
        <div style={S.gridBg} />

        <div style={S.setupWrap}>
          {/* Header */}
          <div style={S.setupHeader}>
            <button onClick={() => navigate('/learn')} style={S.backBtn}>
              <ArrowLeft size={16} /> Back
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={S.logoIcon}><Code2 size={16} color="#fff" /></div>
              <span style={S.logoText}>Code Help</span>
            </div>
            <div style={{ width: 80 }} />
          </div>

          <div style={S.setupCard}>
            <h1 style={S.setupTitle}>Generate a Coding Problem</h1>
            <p style={S.setupSub}>LeetCode-style problems with AI hints and instant evaluation</p>

            {/* Topic */}
            <div style={S.fieldGroup}>
              <label style={S.label}>Topic</label>
              <input
                style={S.input}
                placeholder="e.g. Binary Search, Two Pointers, Dynamic Programming..."
                value={topic}
                onChange={e => { setTopic(e.target.value); setSeenTitles([]) }}
                onKeyDown={e => e.key === 'Enter' && generateProblem()}
                autoFocus
              />
            </div>

            {/* Quick topics */}
            {(user?.interested_topics?.length > 0) && (
              <div style={{ marginBottom: 24 }}>
                <p style={S.label}>Your topics</p>
                <div style={S.chipRow}>
                  {user.interested_topics.map(t => (
                    <button key={t} onClick={() => setTopic(t.replace(/_/g, ' '))} style={{
                      ...S.chip,
                      background: topic === t.replace(/_/g, ' ') ? 'rgba(20,184,166,0.15)' : 'rgba(255,255,255,0.04)',
                      border: `1px solid ${topic === t.replace(/_/g, ' ') ? '#14b8a6' : 'rgba(255,255,255,0.1)'}`,
                      color: topic === t.replace(/_/g, ' ') ? '#14b8a6' : 'rgba(255,255,255,0.5)',
                    }}>{t.replace(/_/g, ' ')}</button>
                  ))}
                </div>
              </div>
            )}

            {/* Difficulty + Language */}
            <div style={S.row2}>
              <div style={S.fieldGroup}>
                <label style={S.label}>Difficulty</label>
                <div style={S.diffRow}>
                  {Object.entries(DIFFICULTY_STYLE).map(([k, v]) => (
                    <button key={k} onClick={() => { setDiff(k); setSeenTitles([]) }} style={{
                      ...S.diffBtn,
                      background: difficulty === k ? v.bg : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${difficulty === k ? v.border : 'rgba(255,255,255,0.08)'}`,
                      color: difficulty === k ? v.color : 'rgba(255,255,255,0.4)',
                    }}>{k.charAt(0).toUpperCase() + k.slice(1)}</button>
                  ))}
                </div>
              </div>
              <div style={S.fieldGroup}>
                <label style={S.label}>Language</label>
                <select value={language} onChange={e => setLang(e.target.value)} style={S.select}>
                  {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
            </div>

            <button
              onClick={generateProblem}
              disabled={!topic.trim() || generating}
              style={{ ...S.genBtn, opacity: !topic.trim() || generating ? 0.5 : 1 }}
            >
              {generating ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Generating...</> : <><Code2 size={16} /> Generate Problem</>}
            </button>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div style={S.historySection}>
              <p style={S.historyTitle}>Recent Problems</p>
              <div style={S.historyList}>
                {history.slice(0, 8).map(h => {
                  const ds = DIFFICULTY_STYLE[h.difficulty] || DIFFICULTY_STYLE.medium
                  return (
                    <div key={h.id} style={S.historyItem}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={S.historyName}>{h.title || h.topic}</p>
                        <p style={S.historyMeta}>{h.topic} · {h.language}</p>
                      </div>
                      <span style={{ ...S.diffPill, background: ds.bg, border: `1px solid ${ds.border}`, color: ds.color }}>
                        {h.difficulty}
                      </span>
                      {h.score !== null && (
                        <span style={{ ...S.scorePill, color: h.score >= 70 ? '#10b981' : '#f59e0b' }}>
                          {h.score}/100
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    )
  }

  // ── PROBLEM SCREEN ────────────────────────────────────────────────────────
  return (
    <div style={S.page}>
      <div style={S.gridBg} />

      {/* Top bar */}
      <div style={S.topBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => setPhase('setup')} style={S.backBtnSm}>
            <ArrowLeft size={15} />
          </button>
          <span style={S.problemTitle}>{problem?.title}</span>
          <span style={{
            ...S.diffPill,
            background: probDiffStyle.bg,
            border: `1px solid ${probDiffStyle.border}`,
            color: probDiffStyle.color,
          }}>{problem?.difficulty}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={generateProblem} style={S.iconBtn} title="New problem on same topic">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Main split layout */}
      <div style={S.splitLayout}>

        {/* ── LEFT PANEL: Problem ── */}
        <div style={S.leftPanel}>
          {/* Tabs */}
          <div style={S.tabs}>
            {[
              { id: 'problem',  label: 'Problem',  icon: <BookOpen size={13} /> },
              { id: 'hints',    label: 'Hints',    icon: <Lightbulb size={13} /> },
              { id: 'solution', label: 'Solution', icon: <Eye size={13} /> },
            ].map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                ...S.tab,
                background: activeTab === tab.id ? 'rgba(255,255,255,0.08)' : 'transparent',
                color: activeTab === tab.id ? '#fff' : 'rgba(255,255,255,0.4)',
                borderBottom: activeTab === tab.id ? '2px solid #14b8a6' : '2px solid transparent',
              }}>
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          <div style={S.leftContent}>
            {/* Problem tab */}
            {activeTab === 'problem' && problem && (
              <div>
                <h2 style={S.probName}>{problem.title}</h2>
                <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                  <span style={{ ...S.diffPill, background: probDiffStyle.bg, border: `1px solid ${probDiffStyle.border}`, color: probDiffStyle.color }}>
                    {problem.difficulty}
                  </span>
                  <span style={S.langPill}>{language}</span>
                  <span style={S.topicPill}>{topic}</span>
                </div>

                <p style={S.sectionLabel}>Description</p>
                <p style={S.descText}>{problem.description}</p>

                {problem.examples?.length > 0 && (
                  <>
                    <p style={S.sectionLabel}>Examples</p>
                    {problem.examples.map((ex, i) => (
                      <div key={i} style={S.exampleBox}>
                        <div style={S.exRow}><span style={S.exLabel}>Input:</span><code style={S.exCode}>{ex.input}</code></div>
                        <div style={S.exRow}><span style={S.exLabel}>Output:</span><code style={S.exCode}>{ex.output}</code></div>
                        {ex.explanation && <div style={S.exRow}><span style={S.exLabel}>Explanation:</span><span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>{ex.explanation}</span></div>}
                      </div>
                    ))}
                  </>
                )}

                {problem.constraints?.length > 0 && (
                  <>
                    <p style={S.sectionLabel}>Constraints</p>
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {problem.constraints.map((c, i) => (
                        <li key={i} style={{ color: 'rgba(255,255,255,0.55)', fontSize: 13, marginBottom: 4, fontFamily: 'monospace' }}>{c}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {/* Hints tab */}
            {activeTab === 'hints' && problem && (
              <div>
                <p style={S.sectionLabel}>Hints</p>
                {problem.hints?.length > 0
                  ? problem.hints.map((h, i) => (
                    <div key={i} style={S.hintBox}>
                      <Lightbulb size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: 2 }} />
                      <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14 }}>{h}</span>
                    </div>
                  ))
                  : <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: 14 }}>No hints available.</p>
                }

                {/* AI Chat for hints */}
                <div style={{ marginTop: 24 }}>
                  <p style={S.sectionLabel}>Ask AI for a hint</p>
                  <div style={S.chatArea}>
                    {chatMsgs.length === 0 && (
                      <p style={{ color: 'rgba(255,255,255,0.2)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
                        Ask for a hint without spoiling the solution
                      </p>
                    )}
                    {chatMsgs.map((m, i) => (
                      <div key={i} style={{
                        ...S.chatMsg,
                        alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                        background: m.role === 'user' ? 'rgba(20,184,166,0.12)' : 'rgba(255,255,255,0.05)',
                        border: `1px solid ${m.role === 'user' ? 'rgba(20,184,166,0.25)' : 'rgba(255,255,255,0.08)'}`,
                        color: m.role === 'error' ? '#ef4444' : 'rgba(255,255,255,0.8)',
                      }}>
                        {m.content}
                      </div>
                    ))}
                    {chatLoading && (
                      <div style={{ ...S.chatMsg, alignSelf: 'flex-start', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>Thinking...</span>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  <div style={S.chatInputRow}>
                    <input
                      style={S.chatInput}
                      placeholder="Ask for a hint..."
                      value={chatInput}
                      onChange={e => setChatInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && sendChat()}
                    />
                    <button onClick={sendChat} disabled={!chatInput.trim() || chatLoading} style={S.chatSendBtn}>
                      <Send size={14} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Solution tab */}
            {activeTab === 'solution' && problem && (
              <div>
                {!showSolution ? (
                  <div style={S.solutionBlur}>
                    <Eye size={28} color="rgba(255,255,255,0.2)" />
                    <p style={{ color: 'rgba(255,255,255,0.4)', margin: '12px 0 20px', fontSize: 14, textAlign: 'center' }}>
                      Try solving it yourself first.<br />The solution will be revealed when you're ready.
                    </p>
                    <button onClick={() => setShowSolution(true)} style={S.revealBtn}>
                      Reveal Solution
                    </button>
                  </div>
                ) : (
                  <div>
                    <p style={S.sectionLabel}>Solution</p>
                    <div style={S.codeDisplay}>
                      <pre style={{ margin: 0, overflowX: 'auto', color: '#e2e8f0', fontSize: 13, lineHeight: 1.6 }}>
                        <code>{problem.solution_code}</code>
                      </pre>
                    </div>
                    {problem.explanation && (
                      <>
                        <p style={{ ...S.sectionLabel, marginTop: 20 }}>Explanation</p>
                        <Md text={problem.explanation} />
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT PANEL: Editor ── */}
        <div style={S.rightPanel}>
          {/* Editor header */}
          <div style={S.editorHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Code2 size={14} color="rgba(255,255,255,0.4)" />
              <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>Solution</span>
              <span style={S.langPill}>{language}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                onClick={() => setCode(problem?.starter_code || '')}
                style={S.resetBtn}
                title="Reset to starter code"
              >
                <RefreshCw size={12} /> Reset
              </button>
              {/* Run button */}
              <button
                onClick={runCode}
                disabled={running || !code.trim()}
                style={{
                  ...S.runBtn,
                  background: 'rgba(16,185,129,0.15)',
                  border: '1px solid rgba(16,185,129,0.35)',
                  color: '#10b981',
                  opacity: running || !code.trim() ? 0.5 : 1,
                }}
              >
                {running
                  ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  : <Play size={13} />}
                {running ? 'Running...' : 'Run'}
              </button>
              {/* Submit button */}
              <button
                onClick={submitCode}
                disabled={submitting || !code.trim()}
                style={{
                  ...S.runBtn,
                  opacity: submitting || !code.trim() ? 0.5 : 1,
                }}
              >
                {submitting
                  ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  : <Trophy size={13} />}
                {submitting ? 'Evaluating...' : 'Submit'}
              </button>
            </div>
          </div>

          {/* Code editor */}
          <textarea
            style={S.editor}
            value={code}
            onChange={e => setCode(e.target.value)}
            spellCheck={false}
            placeholder="Write your solution here..."
          />

          {/* Run results panel */}
          {runResults && (
            <div style={S.runPanel}>
              <div style={S.runPanelHeader}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Play size={13} color={runResults.passed === runResults.total ? '#10b981' : '#f59e0b'} />
                  <span style={{ color: '#fff', fontWeight: 600, fontSize: 13 }}>Test Results</span>
                  <span style={{
                    padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 700,
                    background: runResults.passed === runResults.total ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                    color: runResults.passed === runResults.total ? '#10b981' : '#f59e0b',
                    border: `1px solid ${runResults.passed === runResults.total ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
                  }}>
                    {runResults.passed}/{runResults.total} passed
                  </span>
                </div>
                <button onClick={() => setRunResults(null)} style={S.closeBtn}><X size={13} /></button>
              </div>

              {runResults.raw ? (
                <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, margin: 0, lineHeight: 1.6 }}>
                  {runResults.raw}
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {runResults.cases.map((c, i) => (
                    <div key={i} style={{
                      background: c.passed ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)',
                      border: `1px solid ${c.passed ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                      borderRadius: 10, padding: '10px 14px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <span style={{ fontSize: 14 }}>{c.passed ? '✅' : '❌'}</span>
                        <span style={{ color: c.passed ? '#10b981' : '#ef4444', fontSize: 13, fontWeight: 600 }}>
                          Test Case {i + 1}
                        </span>
                      </div>
                      <div style={S.testRow}>
                        <span style={S.testLabel}>Input</span>
                        <code style={S.testCode}>{c.input}</code>
                      </div>
                      <div style={S.testRow}>
                        <span style={S.testLabel}>Expected</span>
                        <code style={{ ...S.testCode, color: '#86efac' }}>{c.expected}</code>
                      </div>
                      <div style={S.testRow}>
                        <span style={S.testLabel}>Got</span>
                        <code style={{ ...S.testCode, color: c.passed ? '#86efac' : '#fca5a5' }}>{c.actual}</code>
                      </div>
                      {c.error && (
                        <div style={{ marginTop: 6, color: '#fca5a5', fontSize: 12, fontFamily: 'monospace' }}>
                          ⚠ {c.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Eval result */}
          {evalResult && showEval && (
            <div style={S.evalPanel}>
              <div style={S.evalHeader}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Trophy size={15} color="#f59e0b" />
                  <span style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>Evaluation Result</span>
                </div>
                <button onClick={() => setShowEval(false)} style={S.closeBtn}><X size={14} /></button>
              </div>

              {/* Score row */}
              <div style={S.scoreRow}>
                {[
                  { label: 'Overall',     val: evalResult.scores?.overall },
                  { label: 'Correctness', val: evalResult.scores?.correctness },
                  { label: 'Efficiency',  val: evalResult.scores?.efficiency },
                  { label: 'Style',       val: evalResult.scores?.style },
                ].map(s => (
                  <div key={s.label} style={S.scoreCard}>
                    <div style={{
                      ...S.scoreNum,
                      color: s.val >= 70 ? '#10b981' : s.val >= 50 ? '#f59e0b' : '#ef4444'
                    }}>{Math.round(s.val || 0)}</div>
                    <div style={S.scoreLabel}>{s.label}</div>
                  </div>
                ))}
              </div>

              {evalResult.summary && (
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13, margin: '12px 0 0', lineHeight: 1.6 }}>
                  {evalResult.summary}
                </p>
              )}

              {evalResult.key_improvements?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <p style={{ ...S.sectionLabel, marginBottom: 6 }}>Key improvements</p>
                  {evalResult.key_improvements.slice(0, 3).map((imp, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                      <span style={{ color: '#f59e0b', flexShrink: 0 }}>→</span>
                      <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 13 }}>{imp}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S = {
  page: {
    minHeight: '100vh', background: '#050810', display: 'flex',
    flexDirection: 'column', fontFamily: "'DM Sans','Segoe UI',sans-serif",
    position: 'relative', overflow: 'hidden',
  },
  gridBg: {
    position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
    backgroundImage: `linear-gradient(rgba(20,184,166,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(20,184,166,0.02) 1px,transparent 1px)`,
    backgroundSize: '48px 48px',
  },
  // Setup
  setupWrap: { maxWidth: 640, margin: '0 auto', padding: '32px 20px', width: '100%', position: 'relative', zIndex: 1 },
  setupHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 },
  backBtn: { display: 'flex', alignItems: 'center', gap: 6, background: 'transparent', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: '8px 14px', color: 'rgba(255,255,255,0.5)', fontSize: 13, cursor: 'pointer' },
  logoIcon: { width: 32, height: 32, borderRadius: 10, background: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  logoText: { fontSize: 16, fontWeight: 700, color: '#fff' },
  setupCard: { background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 20, padding: 32, marginBottom: 24 },
  setupTitle: { fontSize: 24, fontWeight: 700, color: '#fff', margin: '0 0 6px', letterSpacing: '-0.4px' },
  setupSub: { fontSize: 14, color: 'rgba(255,255,255,0.35)', margin: '0 0 28px' },
  fieldGroup: { marginBottom: 20 },
  label: { fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '1px', display: 'block', marginBottom: 8 },
  input: { width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(20,184,166,0.3)', borderRadius: 10, padding: '13px 16px', color: '#fff', fontSize: 15, outline: 'none', boxSizing: 'border-box' },
  chipRow: { display: 'flex', flexWrap: 'wrap', gap: 8 },
  chip: { padding: '6px 14px', borderRadius: 20, fontSize: 12, cursor: 'pointer', fontWeight: 500 },
  row2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 },
  diffRow: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  diffBtn: { padding: '8px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s' },
  select: { width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10, padding: '10px 14px', color: '#fff', fontSize: 14, outline: 'none', cursor: 'pointer' },
  genBtn: { width: '100%', background: 'linear-gradient(135deg,#7c3aed,#6d28d9)', border: 'none', borderRadius: 12, padding: '14px', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 },
  historySection: { background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, padding: 20 },
  historyTitle: { fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 12 },
  historyList: { display: 'flex', flexDirection: 'column', gap: 8 },
  historyItem: { display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)' },
  historyName: { fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.8)', margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  historyMeta: { fontSize: 12, color: 'rgba(255,255,255,0.3)', margin: '2px 0 0', fontFamily: 'monospace' },
  diffPill: { padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' },
  scorePill: { fontSize: 13, fontWeight: 700, fontFamily: 'monospace', whiteSpace: 'nowrap' },
  // Problem screen
  topBar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', background: 'rgba(5,8,16,0.95)', borderBottom: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(10px)', position: 'sticky', top: 0, zIndex: 20 },
  backBtnSm: { background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '6px 10px', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center' },
  problemTitle: { fontSize: 15, fontWeight: 700, color: '#fff', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  iconBtn: { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '7px 10px', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center' },
  runBtn: { display: 'flex', alignItems: 'center', gap: 6, background: '#7c3aed', border: 'none', borderRadius: 8, padding: '8px 16px', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' },
  splitLayout: { display: 'flex', flex: 1, overflow: 'hidden', height: 'calc(100vh - 53px)', position: 'relative', zIndex: 1 },
  leftPanel: { width: '42%', minWidth: 320, display: 'flex', flexDirection: 'column', borderRight: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' },
  tabs: { display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)', flexShrink: 0 },
  tab: { display: 'flex', alignItems: 'center', gap: 6, padding: '11px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none', transition: 'all 0.15s' },
  leftContent: { flex: 1, overflowY: 'auto', padding: '20px 20px 40px' },
  probName: { fontSize: 20, fontWeight: 700, color: '#fff', margin: '0 0 12px', letterSpacing: '-0.3px' },
  sectionLabel: { fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '1px', margin: '20px 0 8px' },
  descText: { color: 'rgba(255,255,255,0.75)', fontSize: 14, lineHeight: 1.7, margin: 0 },
  exampleBox: { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: '14px 16px', marginBottom: 10 },
  exRow: { display: 'flex', gap: 10, marginBottom: 6, alignItems: 'flex-start', flexWrap: 'wrap' },
  exLabel: { fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.4)', minWidth: 80, fontFamily: 'monospace' },
  exCode: { background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '2px 8px', fontSize: 13, color: '#7dd3fc', fontFamily: 'monospace' },
  langPill: { padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)', color: '#a78bfa' },
  topicPill: { padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: 'rgba(20,184,166,0.1)', border: '1px solid rgba(20,184,166,0.25)', color: '#2dd4bf' },
  hintBox: { display: 'flex', gap: 10, padding: '12px 14px', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)', borderRadius: 10, marginBottom: 10 },
  chatArea: { background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 12, padding: 14, minHeight: 120, maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 },
  chatMsg: { padding: '10px 14px', borderRadius: 10, fontSize: 13, lineHeight: 1.6, maxWidth: '90%' },
  chatInputRow: { display: 'flex', gap: 8, marginTop: 10 },
  chatInput: { flex: 1, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '9px 14px', color: '#fff', fontSize: 13, outline: 'none' },
  chatSendBtn: { background: '#14b8a6', border: 'none', borderRadius: 8, padding: '9px 14px', color: '#000', cursor: 'pointer', display: 'flex', alignItems: 'center' },
  solutionBlur: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 20px', textAlign: 'center' },
  revealBtn: { background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10, padding: '10px 24px', color: 'rgba(255,255,255,0.7)', fontSize: 14, fontWeight: 600, cursor: 'pointer' },
  codeDisplay: { background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: 16, fontFamily: "'JetBrains Mono','Courier New',monospace" },
  // Right panel
  rightPanel: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  editorHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 },
  resetBtn: { display: 'flex', alignItems: 'center', gap: 5, background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, padding: '5px 10px', color: 'rgba(255,255,255,0.4)', fontSize: 12, cursor: 'pointer' },
  editor: { flex: 1, background: '#0d1117', border: 'none', outline: 'none', padding: '20px', color: '#e2e8f0', fontSize: 14, fontFamily: "'JetBrains Mono','Courier New',monospace", lineHeight: 1.7, resize: 'none', minHeight: 0 },
  evalPanel: { background: 'rgba(5,8,16,0.98)', borderTop: '1px solid rgba(255,255,255,0.08)', padding: '16px 20px', maxHeight: '45%', overflowY: 'auto', flexShrink: 0 },
  evalHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  closeBtn: { background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.3)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center' },
  scoreRow: { display: 'flex', gap: 12, flexWrap: 'wrap' },
  scoreCard: { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: '10px 16px', textAlign: 'center', minWidth: 70 },
  scoreNum: { fontSize: 22, fontWeight: 800, fontFamily: 'monospace', lineHeight: 1 },
  scoreLabel: { fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.5px' },
  runPanel: { background: 'rgba(5,8,16,0.98)', borderTop: '1px solid rgba(255,255,255,0.08)', padding: '14px 16px', maxHeight: '40%', overflowY: 'auto', flexShrink: 0 },
  runPanelHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  testRow: { display: 'flex', gap: 10, marginBottom: 4, alignItems: 'flex-start' },
  testLabel: { fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.3)', minWidth: 64, fontFamily: 'monospace', paddingTop: 2 },
  testCode: { background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 5, padding: '2px 8px', fontSize: 12, fontFamily: 'monospace', color: '#7dd3fc' },
}