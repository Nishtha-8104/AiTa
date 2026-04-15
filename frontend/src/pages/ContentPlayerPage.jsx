import { useState, useEffect, useRef } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { useAuth } from "../hooks/useAuth"
import { contentPlayerAPI } from "../utils/api"
import ReactMarkdown from "react-markdown"

const MODES = [
  { id: "walkthrough", label: "Walkthrough", icon: "◈", color: "#14b8a6", desc: "Step-by-step with LeetCode practice" },
  { id: "qa",          label: "Q&A",         icon: "◉", color: "#00d4ff", desc: "Socratic explanations" },
  { id: "quiz",        label: "Quiz",        icon: "⬡", color: "#f59e0b", desc: "Adaptive challenge questions" },
  { id: "code_help",   label: "Code Help",   icon: "⟨/⟩", color: "#7c3aed", desc: "LeetCode-style problems with AI hints" },
  { id: "brainstorm",  label: "Brainstorm",  icon: "⚡", color: "#ef4444", desc: "Compare approaches" },
]

const DIFFICULTY_CONFIG = {
  easy:   { color: "#10b981", label: "Easy",   icon: "○" },
  medium: { color: "#f59e0b", label: "Medium", icon: "◑" },
  hard:   { color: "#ef4444", label: "Hard",   icon: "●" },
  expert: { color: "#8b5cf6", label: "Expert", icon: "◆" },
}

const COMFORT_MESSAGES = {
  struggling: { text: "Dropping difficulty to help you", color: "#f59e0b", icon: "↓" },
  too_easy:   { text: "Ramping up the challenge!",       color: "#10b981", icon: "↑" },
  comfortable: null,
}

export default function ContentPlayerPage() {
  const { user }   = useAuth()
  const navigate   = useNavigate()
  const location   = useLocation()
  const messagesEndRef = useRef(null)

  const [phase, setPhase]               = useState("setup")
  const [selectedMode, setSelectedMode] = useState("walkthrough")
  const [topic, setTopic]               = useState(location.state?.topic || "")
  const [language, setLanguage]         = useState("python")
  const [difficulty, setDifficulty]     = useState("medium")

  const [sessionId, setSessionId]       = useState(null)
  const [messages, setMessages]         = useState([])
  const [input, setInput]               = useState("")
  const [codeSnippet, setCodeSnippet]   = useState("")
  const [showCodeInput, setShowCodeInput] = useState(false)
  const [loading, setLoading]           = useState(false)

  const [difficultyChanged, setDifficultyChanged] = useState(false)
  const [comfortSignal, setComfortSignal]         = useState(null)
  const [currentTopic, setCurrentTopic]           = useState(location.state?.topic || "")
  const [topicChanged, setTopicChanged]           = useState(false)

  const [sessions, setSessions]         = useState([])
  const [histLoading, setHistLoading]   = useState(false)

  const interestedTopics = user?.interested_topics || []

  // Fetch session history
  useEffect(() => {
    setHistLoading(true)
    contentPlayerAPI.getSessions()
      .then(({ data }) => setSessions(data || []))
      .catch(() => {})
      .finally(() => setHistLoading(false))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (location.state?.fromRecommendation && location.state?.topic) {
      setTopic(location.state.topic)
      setCurrentTopic(location.state.topic)
    }
  }, [])

  // Resume an existing session
  const resumeSession = async (session) => {
    setLoading(true)
    try {
      const { data } = await contentPlayerAPI.getSession(session.id)
      const msgs = (data.messages || []).map(m => ({
        id: m.id, role: m.role, content: m.content, concepts: [],
      }))
      setSessionId(session.id)
      setCurrentTopic(session.topic || "")
      setSelectedMode(session.mode || "walkthrough")
      setMessages(msgs)
      setPhase("active")
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Start a new session
  const startSession = async () => {
    if (!topic.trim()) return
    if (selectedMode === "code_help") {
      navigate("/code-help", { state: { topic, language, difficulty } })
      return
    }
    setLoading(true)
    try {
      const { data: session } = await contentPlayerAPI.createSession({
        mode: selectedMode, topic, language, difficulty,
      })
      setSessionId(session.id)
      setCurrentTopic(topic)
      setPhase("active")
      // Refresh history list
      setSessions(prev => [session, ...prev])
      await sendMessage(session.id, `Let's start learning about ${topic}. Please begin!`)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = async (sid, messageText) => {
    const id   = sid || sessionId
    const text = messageText || input.trim()
    if (!text || !id) return

    setInput("")
    setLoading(true)
    setDifficultyChanged(false)
    setComfortSignal(null)
    setTopicChanged(false)

    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }])

    try {
      const { data: res } = await contentPlayerAPI.chat(id, {
        message: text,
        code_snippet: codeSnippet || undefined,
      })

      if (res.difficulty_changed) {
        setDifficulty(res.difficulty)
        setDifficultyChanged(true)
        setComfortSignal(res.comfort_signal)
        setTimeout(() => setDifficultyChanged(false), 4000)
      }
      if (res.topic_changed && res.topic !== currentTopic) {
        setCurrentTopic(res.topic)
        setTopicChanged(true)
        setTimeout(() => setTopicChanged(false), 5000)
      }

      setMessages(prev => [...prev, {
        role: "assistant", content: res.response,
        id: res.message_id, difficulty: res.difficulty, concepts: res.concepts,
      }])
      setCodeSnippet("")
      setShowCodeInput(false)
    } catch {
      setMessages(prev => [...prev, {
        role: "error", content: "Failed to get response. Please try again.", id: Date.now(),
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const activeMode = MODES.find(m => m.id === selectedMode)
  const diffConfig = DIFFICULTY_CONFIG[difficulty] || DIFFICULTY_CONFIG.medium

  // ── Shared history sidebar (used in both phases) ──────────────────────────
  const HistorySidebar = () => (
    <div style={S.sidebar}>
      <div style={S.sidebarHead}>
        <span style={S.sidebarTitle}>Sessions</span>
        <button onClick={() => setPhase("setup")} style={S.newBtn}>+ New</button>
      </div>
      <div style={S.sidebarList}>
        {histLoading && [1,2,3].map(i => <div key={i} style={S.skelItem} />)}
        {!histLoading && sessions.length === 0 && (
          <p style={S.sidebarEmpty}>No sessions yet</p>
        )}
        {!histLoading && sessions.map(s => {
          const m      = MODES.find(x => x.id === s.mode) || MODES[0]
          const active = s.id === sessionId
          const date   = s.created_at
            ? new Date(s.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })
            : ""
          return (
            <button key={s.id} onClick={() => resumeSession(s)} style={{
              ...S.sidebarItem,
              background: active ? `${m.color}14` : "rgba(255,255,255,0.02)",
              border: `1px solid ${active ? m.color + "40" : "rgba(255,255,255,0.06)"}`,
            }}>
              <span style={{ fontSize: 15, color: m.color, flexShrink: 0 }}>{m.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={S.sidebarTopic}>{s.topic || "Untitled"}</p>
                <p style={{ ...S.sidebarMeta, color: m.color + "cc" }}>{m.label} · {date}</p>
              </div>
              {active && <span style={{ color: m.color, fontSize: 9 }}>●</span>}
            </button>
          )
        })}
      </div>
    </div>
  )

  // ── SETUP PHASE ───────────────────────────────────────────────────────────
  if (phase === "setup") {
    return (
      <div style={S.page}>
        <div style={S.gridBg} />

        {/* Top bar */}
        <div style={S.topBar}>
          <button onClick={() => navigate("/dashboard")} style={S.backBtnSm}>← Dashboard</button>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "#14b8a6", fontSize: 18 }}>◈</span>
            <span style={S.brandText}>Learning Studio</span>
          </div>
          <div style={{ width: 110 }} />
        </div>

        <div style={S.setupLayout}>
          {/* Left sidebar */}
          <HistorySidebar />

          {/* Setup card */}
          <div style={S.setupCard}>
            <h1 style={S.setupTitle}>What are we learning today?</h1>
            <p style={S.setupSub}>Your topics are remembered across all agents</p>

            {/* Topic input */}
            <input
              style={S.topicInput}
              placeholder="e.g. Binary Search Trees, Dynamic Programming..."
              value={topic}
              onChange={e => setTopic(e.target.value)}
              onKeyDown={e => e.key === "Enter" && startSession()}
              autoFocus
            />

            {/* Profile topic chips */}
            {interestedTopics.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <p style={S.fieldLabel}>Your saved topics</p>
                <div style={S.chipRow}>
                  {interestedTopics.map(t => (
                    <button key={t} onClick={() => setTopic(t.replace(/_/g, " "))} style={{
                      ...S.chip,
                      background: topic === t.replace(/_/g, " ") ? "rgba(20,184,166,0.15)" : "rgba(255,255,255,0.04)",
                      border: `1px solid ${topic === t.replace(/_/g, " ") ? "#14b8a6" : "rgba(255,255,255,0.1)"}`,
                      color: topic === t.replace(/_/g, " ") ? "#14b8a6" : "rgba(255,255,255,0.5)",
                    }}>{t.replace(/_/g, " ")}</button>
                  ))}
                </div>
              </div>
            )}

            {/* Mode selection */}
            <p style={S.fieldLabel}>Learning mode</p>
            <div style={S.modeGrid}>
              {MODES.map(mode => (
                <button key={mode.id} onClick={() => setSelectedMode(mode.id)} style={{
                  ...S.modeCard,
                  background: selectedMode === mode.id ? `${mode.color}12` : "rgba(255,255,255,0.03)",
                  border: `1px solid ${selectedMode === mode.id ? mode.color : "rgba(255,255,255,0.08)"}`,
                  boxShadow: selectedMode === mode.id ? `0 0 18px ${mode.color}20` : "none",
                }}>
                  <span style={{ fontSize: 20, color: mode.color }}>{mode.icon}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>{mode.label}</div>
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 2 }}>{mode.desc}</div>
                  </div>
                  {selectedMode === mode.id && <span style={{ marginLeft: "auto", color: mode.color }}>✓</span>}
                </button>
              ))}
            </div>

            {/* Language + Difficulty */}
            <div style={S.row2}>
              <div>
                <p style={S.fieldLabel}>Language</p>
                <select value={language} onChange={e => setLanguage(e.target.value)} style={S.select}>
                  {["python","javascript","java","c++","go","rust"].map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              <div>
                <p style={S.fieldLabel}>Starting difficulty</p>
                <select value={difficulty} onChange={e => setDifficulty(e.target.value)} style={S.select}>
                  {Object.entries(DIFFICULTY_CONFIG).map(([k, v]) => (
                    <option key={k} value={k}>{v.icon} {v.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={startSession}
              disabled={!topic.trim() || loading}
              style={{ ...S.startBtn, opacity: !topic.trim() || loading ? 0.5 : 1 }}
            >
              {loading ? "Starting..." : `Begin ${activeMode?.label} →`}
            </button>
          </div>
        </div>

        <style>{`@keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:1} }`}</style>
      </div>
    )
  }

  // ── ACTIVE SESSION PHASE ──────────────────────────────────────────────────
  return (
    <div style={S.page}>
      <div style={S.gridBg} />

      {/* Top bar */}
      <div style={S.topBar}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button onClick={() => navigate("/dashboard")} style={S.backBtnSm} title="Dashboard">⌂</button>
          <button onClick={() => setPhase("setup")} style={{ ...S.backBtnSm, fontSize: 12 }} title="Back to setup">← Sessions</button>
        </div>

        <div style={S.topBarCenter}>
          <span style={{ color: activeMode?.color, fontSize: 15 }}>{activeMode?.icon}</span>
          <span style={S.topBarMode}>{activeMode?.label}</span>
          <span style={S.topBarSep}>·</span>
          <span style={S.topBarTopic}>{currentTopic}</span>
        </div>

        <div style={S.topBarRight}>
          <div style={{ ...S.diffBadge, background: `${diffConfig.color}15`, border: `1px solid ${diffConfig.color}40`, color: diffConfig.color }}>
            {diffConfig.icon} {diffConfig.label}
          </div>
          <button onClick={() => navigate("/code-eval", { state: { fromContentPlayer: true, topic: currentTopic } })} style={S.evalBtn}>
            Evaluate Code →
          </button>
        </div>
      </div>

      {/* Notifications */}
      {difficultyChanged && comfortSignal && COMFORT_MESSAGES[comfortSignal] && (
        <div style={{ ...S.notification, background: `${COMFORT_MESSAGES[comfortSignal].color}15`, border: `1px solid ${COMFORT_MESSAGES[comfortSignal].color}40`, color: COMFORT_MESSAGES[comfortSignal].color }}>
          {COMFORT_MESSAGES[comfortSignal].icon} {COMFORT_MESSAGES[comfortSignal].text} — now at <strong>{difficulty}</strong>
        </div>
      )}
      {topicChanged && (
        <div style={S.topicNotif}>⟳ Topic updated to: <strong>{currentTopic}</strong></div>
      )}

      {/* Split layout */}
      <div style={S.activeLayout}>

        {/* Left sidebar */}
        <HistorySidebar />

        {/* Chat panel */}
        <div style={S.chatPanel}>
          <div style={S.messagesArea}>
            {messages.map(msg => (
              <div key={msg.id} style={{ ...S.msgRow, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                {msg.role === "assistant" && (
                  <div style={{ ...S.avatar, background: activeMode?.color || "#14b8a6" }}>{activeMode?.icon}</div>
                )}
                <div style={{
                  ...S.bubble,
                  background: msg.role === "user" ? "rgba(20,184,166,0.12)" : "rgba(255,255,255,0.04)",
                  border: `1px solid ${msg.role === "user" ? "rgba(20,184,166,0.25)" : "rgba(255,255,255,0.08)"}`,
                  maxWidth: msg.role === "user" ? "60%" : "78%",
                }}>
                  {msg.role === "error"
                    ? <p style={{ color: "#ef4444", margin: 0 }}>{msg.content}</p>
                    : (
                      <div style={S.mdContent}>
                        <ReactMarkdown components={{
                          code({ inline, children }) {
                            return inline
                              ? <code style={S.inlineCode}>{children}</code>
                              : <div style={S.codeBlock}><pre style={{ margin: 0, overflowX: "auto" }}><code style={{ color: "#e2e8f0", fontSize: 13 }}>{children}</code></pre></div>
                          }
                        }}>{msg.content}</ReactMarkdown>
                      </div>
                    )
                  }
                  {msg.concepts?.length > 0 && (
                    <div style={S.conceptTags}>
                      {msg.concepts.map(c => <span key={c} style={S.conceptTag}>{c}</span>)}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={S.msgRow}>
                <div style={{ ...S.avatar, background: activeMode?.color || "#14b8a6" }}>{activeMode?.icon}</div>
                <div style={{ ...S.bubble, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={S.typingDots}>
                    <span style={{ ...S.dot, animationDelay: "0ms" }} />
                    <span style={{ ...S.dot, animationDelay: "150ms" }} />
                    <span style={{ ...S.dot, animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {showCodeInput && (
            <div style={S.codeInputArea}>
              <textarea
                style={S.codeTextarea}
                placeholder="Paste your code here..."
                value={codeSnippet}
                onChange={e => setCodeSnippet(e.target.value)}
                rows={5}
              />
            </div>
          )}

          <div style={S.inputArea}>
            <button
              onClick={() => setShowCodeInput(!showCodeInput)}
              style={{ ...S.codeToggleBtn, background: showCodeInput ? "rgba(124,58,237,0.2)" : "transparent", color: showCodeInput ? "#a78bfa" : "rgba(255,255,255,0.4)" }}
              title="Attach code"
            >⟨/⟩</button>

            <textarea
              style={S.messageInput}
              placeholder={`Ask about ${currentTopic}... (Enter to send)`}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />

            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              style={{ ...S.sendBtn, background: input.trim() && !loading ? "#14b8a6" : "rgba(255,255,255,0.1)", color: input.trim() && !loading ? "#000" : "rgba(255,255,255,0.3)" }}
            >→</button>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes dotBounce { 0%,80%,100%{transform:translateY(0);opacity:.4} 40%{transform:translateY(-6px);opacity:1} }
        @keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:1} }
      `}</style>
    </div>
  )
}

const S = {
  page: { minHeight: "100vh", background: "#050810", display: "flex", flexDirection: "column", fontFamily: "'DM Sans','Segoe UI',sans-serif", position: "relative" },
  gridBg: { position: "fixed", inset: 0, backgroundImage: `linear-gradient(rgba(20,184,166,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(20,184,166,0.025) 1px,transparent 1px)`, backgroundSize: "48px 48px", pointerEvents: "none", zIndex: 0 },

  // Top bar
  topBar: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 20px", background: "rgba(5,8,16,0.92)", borderBottom: "1px solid rgba(255,255,255,0.06)", backdropFilter: "blur(10px)", position: "sticky", top: 0, zIndex: 20 },
  backBtnSm: { background: "transparent", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "6px 12px", color: "rgba(255,255,255,0.5)", fontSize: 13, cursor: "pointer" },
  brandText: { fontSize: 15, fontWeight: 700, color: "#fff" },
  topBarCenter: { display: "flex", alignItems: "center", gap: 8, fontSize: 14 },
  topBarMode: { color: "#fff", fontWeight: 600 },
  topBarSep: { color: "rgba(255,255,255,0.2)" },
  topBarTopic: { color: "rgba(255,255,255,0.5)", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  topBarRight: { display: "flex", alignItems: "center", gap: 10 },
  diffBadge: { padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600 },
  evalBtn: { background: "rgba(249,115,22,0.12)", border: "1px solid rgba(249,115,22,0.3)", borderRadius: 8, padding: "6px 14px", color: "#fb923c", fontSize: 12, fontWeight: 600, cursor: "pointer" },

  // Notifications
  notification: { margin: "8px 20px", padding: "10px 16px", borderRadius: 10, fontSize: 13, fontWeight: 500, position: "relative", zIndex: 5 },
  topicNotif: { margin: "8px 20px", padding: "10px 16px", borderRadius: 10, fontSize: 13, fontWeight: 500, background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)", color: "#00d4ff", position: "relative", zIndex: 5 },

  // Setup layout
  setupLayout: { display: "grid", gridTemplateColumns: "260px 1fr", gap: 0, flex: 1, position: "relative", zIndex: 1 },
  setupCard: { padding: "32px 36px", maxWidth: 640, width: "100%", margin: "0 auto" },
  setupTitle: { fontSize: 24, fontWeight: 700, color: "#fff", margin: "0 0 6px", letterSpacing: "-0.4px" },
  setupSub: { fontSize: 13, color: "rgba(255,255,255,0.35)", margin: "0 0 24px" },
  topicInput: { width: "100%", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(20,184,166,0.3)", borderRadius: 10, padding: "13px 16px", color: "#fff", fontSize: 15, outline: "none", boxSizing: "border-box", marginBottom: 24 },
  fieldLabel: { fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "1px", margin: "0 0 10px" },
  chipRow: { display: "flex", flexWrap: "wrap", gap: 8 },
  chip: { padding: "6px 14px", borderRadius: 20, fontSize: 12, cursor: "pointer", fontWeight: 500 },
  modeGrid: { display: "flex", flexDirection: "column", gap: 8, marginBottom: 24 },
  modeCard: { display: "flex", alignItems: "center", gap: 14, padding: "13px 16px", borderRadius: 12, cursor: "pointer", transition: "all 0.15s", textAlign: "left", width: "100%" },
  row2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 },
  select: {
    width: "100%",
    background: "#131313e3",   // 🔥 darker background
    color: "#fff",
    border: "1px solid rgba(0, 0, 0, 0.12)",
    borderRadius: "10px",
    padding: "10px 14px",
    fontSize: "14px",
    outline: "none",
    cursor: "pointer"
  },
  // select: { width: "100%", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 10, padding: "10px 14px", color: "#fff", fontSize: 14, outline: "none", cursor: "pointer" },
  startBtn: { width: "100%", background: "linear-gradient(135deg,#14b8a6,#0891b2)", border: "none", borderRadius: 12, padding: "14px", color: "#000", fontSize: 15, fontWeight: 700, cursor: "pointer", transition: "opacity 0.2s" },

  // Sidebar (shared)
  sidebar: { width: 260, borderRight: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.01)", display: "flex", flexDirection: "column", height: "calc(100vh - 57px)", position: "sticky", top: 57, overflowY: "auto" },
  sidebarHead: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", flexShrink: 0 },
  sidebarTitle: { fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "1px" },
  newBtn: { background: "rgba(20,184,166,0.12)", border: "1px solid rgba(20,184,166,0.3)", borderRadius: 6, padding: "4px 10px", color: "#14b8a6", fontSize: 12, fontWeight: 700, cursor: "pointer" },
  sidebarList: { flex: 1, overflowY: "auto", padding: "8px" },
  sidebarEmpty: { fontSize: 12, color: "rgba(255,255,255,0.2)", textAlign: "center", padding: "24px 0", margin: 0 },
  sidebarItem: { width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, cursor: "pointer", textAlign: "left", marginBottom: 4, transition: "all 0.15s" },
  sidebarTopic: { fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.8)", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  sidebarMeta: { fontSize: 11, margin: "2px 0 0", fontFamily: "monospace" },
  skelItem: { height: 52, background: "rgba(255,255,255,0.04)", borderRadius: 10, marginBottom: 6, animation: "pulse 1.5s ease-in-out infinite" },

  // Active layout
  activeLayout: { display: "flex", flex: 1, overflow: "hidden", height: "calc(100vh - 57px)" },
  chatPanel: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" },
  messagesArea: { flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: 16 },
  msgRow: { display: "flex", alignItems: "flex-start", gap: 12 },
  avatar: { width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0, color: "#fff", fontWeight: 700 },
  bubble: { borderRadius: 14, padding: "14px 18px" },
  mdContent: { color: "rgba(255,255,255,0.85)", fontSize: 14, lineHeight: 1.7 },
  inlineCode: { background: "rgba(0,212,255,0.12)", border: "1px solid rgba(0,212,255,0.2)", borderRadius: 4, padding: "2px 6px", fontSize: 12, fontFamily: "monospace", color: "#7dd3fc" },
  codeBlock: { background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: "14px", margin: "10px 0", fontFamily: "'JetBrains Mono','Courier New',monospace", overflowX: "auto" },
  conceptTags: { display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.06)" },
  conceptTag: { background: "rgba(20,184,166,0.1)", border: "1px solid rgba(20,184,166,0.2)", borderRadius: 10, padding: "3px 10px", fontSize: 11, color: "#2dd4bf" },
  typingDots: { display: "flex", gap: 5, alignItems: "center", padding: "4px 0" },
  dot: { width: 7, height: 7, borderRadius: "50%", background: "rgba(255,255,255,0.4)", display: "inline-block", animation: "dotBounce 1.2s ease-in-out infinite" },

  // Input
  inputArea: { display: "flex", alignItems: "center", gap: 10, padding: "12px 20px", background: "rgba(5,8,16,0.9)", borderTop: "1px solid rgba(255,255,255,0.06)", backdropFilter: "blur(10px)", flexShrink: 0 },
  codeToggleBtn: { border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "9px 12px", cursor: "pointer", fontSize: 13, fontFamily: "monospace", transition: "all 0.2s", flexShrink: 0 },
  messageInput: { flex: 1, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: "10px 14px", color: "#fff", fontSize: 14, resize: "none", outline: "none", fontFamily: "'DM Sans',sans-serif", lineHeight: 1.5 },
  codeInputArea: { padding: "10px 20px", background: "rgba(5,8,16,0.8)", borderTop: "1px solid rgba(124,58,237,0.2)", flexShrink: 0 },
  codeTextarea: { width: "100%", background: "rgba(0,0,0,0.4)", border: "1px solid rgba(124,58,237,0.25)", borderRadius: 10, padding: "12px", color: "#e2e8f0", fontSize: 13, fontFamily: "'JetBrains Mono',monospace", resize: "none", outline: "none", boxSizing: "border-box" },
  sendBtn: { width: 40, height: 40, borderRadius: "50%", border: "none", fontSize: 18, cursor: "pointer", transition: "all 0.2s", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 },
}
