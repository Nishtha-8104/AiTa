import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, Sparkles, BarChart2, Menu, X,
  MessageSquare, Code2, Brain, Puzzle, BookOpen
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useContentPlayer } from '../hooks/useContentPlayer'
import SessionSidebar from '../components/content_player/SessionSidebar'
import MessageBubble from '../components/content_player/MessageBubble'
import ChatInput from '../components/content_player/ChatInput'
import SessionInfoPanel from '../components/content_player/SessionInfoPanel'
import WelcomeScreen from '../components/content_player/WelcomeScreen'

const MODE_LABELS = {
  qa: 'Q&A', code_help: 'Code Help', brainstorm: 'Brainstorm',
  quiz: 'Quiz', walkthrough: 'Walkthrough',
}
const MODE_ICONS = {
  qa: MessageSquare, code_help: Code2, brainstorm: Brain,
  quiz: Puzzle, walkthrough: BookOpen,
}

export default function ContentPlayerPage() {
  const { user }    = useAuth()
  const navigate    = useNavigate()
  const [params]    = useSearchParams()

  const {
    sessions, activeSession, messages,
    sending, loading, creating,
    fetchSessions, openSession, createSession,
    sendMessage, rateMessage, archiveSession, clearActive,
  } = useContentPlayer()

  const [showSidebar, setShowSidebar]   = useState(true)
  const [showInfo, setShowInfo]         = useState(false)
  const [currentMode, setCurrentMode]   = useState('qa')
  const bottomRef                       = useRef(null)

  // Load sessions on mount
  useEffect(() => {
    fetchSessions()
  }, [])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  // Sync mode with active session
  useEffect(() => {
    if (activeSession?.mode) setCurrentMode(activeSession.mode)
  }, [activeSession?.id])

  // Handle new session creation from welcome screen or sidebar
  const handleNewSession = async (modeOrConfig) => {
    const config = typeof modeOrConfig === 'string'
      ? { mode: modeOrConfig, language: null, topic: null }
      : modeOrConfig
    const session = await createSession(config)
    if (session) {
      setCurrentMode(session.mode)
      setShowSidebar(false) // on mobile collapse sidebar
    }
  }

  // Handle send
  const handleSend = async ({ message, codeSnippet, codeLanguage, errorMessage }) => {
    if (!activeSession) return
    await sendMessage({
      sessionId: activeSession.id,
      message,
      codeSnippet,
      codeLanguage,
      errorMessage,
      mode: currentMode !== activeSession.mode ? currentMode : undefined,
    })
  }

  const ActiveModeIcon = MODE_ICONS[currentMode] || MessageSquare

  return (
    <div className="h-screen flex flex-col overflow-hidden">

      {/* ── Top Navbar ── */}
      <nav className="shrink-0 border-b border-white/[0.06] bg-surface-900/90 backdrop-blur-xl z-40">
        <div className="h-14 flex items-center px-4 gap-3">
          {/* Back */}
          <button onClick={() => navigate('/dashboard')}
            className="p-2 text-white/40 hover:text-white/70 rounded-xl hover:bg-surface-700 transition-all">
            <ArrowLeft size={18} />
          </button>

          {/* Sidebar toggle */}
          <button onClick={() => setShowSidebar(v => !v)}
            className="p-2 text-white/40 hover:text-white/70 rounded-xl hover:bg-surface-700 transition-all">
            {showSidebar ? <X size={18} /> : <Menu size={18} />}
          </button>

          {/* Brand */}
          <div className="flex items-center gap-2 mr-auto">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <Sparkles size={14} className="text-white" />
            </div>
            <span className="font-display font-700 text-sm text-white hidden sm:block">
              Content <span className="text-brand-400">Player</span> Agent
            </span>
          </div>

          {/* Session mode indicator */}
          {activeSession && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-700/60 rounded-xl border border-white/[0.06]">
              <ActiveModeIcon size={14} className="text-brand-400" />
              <span className="text-xs font-display font-600 text-white/70 hidden sm:block">
                {MODE_LABELS[currentMode]}
              </span>
            </div>
          )}

          {/* Session title */}
          {activeSession?.title && (
            <span className="text-white/30 text-xs font-body truncate max-w-[200px] hidden md:block">
              {activeSession.title}
            </span>
          )}

          {/* Info panel toggle */}
          {activeSession && (
            <button onClick={() => setShowInfo(v => !v)}
              className={`p-2 rounded-xl transition-all ${showInfo ? 'text-brand-400 bg-brand-600/10' : 'text-white/40 hover:text-white/70 hover:bg-surface-700'}`}>
              <BarChart2 size={18} />
            </button>
          )}
        </div>
      </nav>

      {/* ── Main layout ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar */}
        {showSidebar && (
          <div className="w-64 shrink-0 overflow-hidden hidden sm:block">
            <SessionSidebar
              sessions={sessions}
              activeSessionId={activeSession?.id}
              loading={loading}
              onSelectSession={(id) => { openSession(id); setShowSidebar(false) }}
              onNewSession={handleNewSession}
              onArchive={archiveSession}
            />
          </div>
        )}

        {/* Chat area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!activeSession ? (
            // ── Welcome screen ──────────────────────────────────────────────
            <WelcomeScreen onStartSession={handleNewSession} />
          ) : (
            <>
              {/* ── Messages ─────────────────────────────────────────────── */}
              <div className="flex-1 overflow-y-auto py-4">
                {/* Empty session */}
                {messages.length === 0 && !sending && (
                  <div className="flex flex-col items-center justify-center h-full text-center px-8">
                    <div className="w-16 h-16 rounded-2xl bg-brand-600/10 border border-brand-500/20 flex items-center justify-center mb-4">
                      <ActiveModeIcon size={28} className="text-brand-400" />
                    </div>
                    <h3 className="font-display font-700 text-white text-lg mb-2">
                      {MODE_LABELS[currentMode]} Session Ready
                    </h3>
                    <p className="text-white/30 text-sm max-w-sm">
                      {currentMode === 'qa'          && 'Ask any programming question. I\'ll explain with examples and help you really understand.'}
                      {currentMode === 'code_help'   && 'Paste your code and describe the problem. I\'ll guide you to the fix without spoiling it.'}
                      {currentMode === 'brainstorm'  && 'Describe a problem you want to solve. We\'ll explore approaches and trade-offs together.'}
                      {currentMode === 'quiz'        && 'Tell me a topic and I\'ll start quizzing you. I adapt to your level as we go.'}
                      {currentMode === 'walkthrough' && 'Tell me which concept to walk through. I\'ll take you from basics to advanced, step by step.'}
                    </p>
                    {user?.learning_profile?.weak_areas?.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2 justify-center">
                        <span className="text-white/20 text-xs">Your weak areas:</span>
                        {user.learning_profile.weak_areas.slice(0, 4).map(a => (
                          <span key={a} className="px-2.5 py-1 bg-yellow-600/10 border border-yellow-500/20 text-yellow-300/70 text-xs rounded-lg font-mono">
                            {a}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Message list */}
                {messages.map(msg => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    onRate={(id, helpful) => rateMessage(id, helpful)}
                  />
                ))}
                <div ref={bottomRef} className="h-4" />
              </div>

              {/* ── Input ───────────────────────────────────────────────── */}
              <ChatInput
                onSend={handleSend}
                sending={sending}
                sessionMode={currentMode}
                onModeChange={setCurrentMode}
                disabled={creating}
              />
            </>
          )}
        </div>

        {/* Info panel */}
        {showInfo && activeSession && (
          <div className="w-72 shrink-0 overflow-hidden hidden lg:block">
            <SessionInfoPanel
              session={activeSession}
              onClose={() => setShowInfo(false)}
            />
          </div>
        )}
      </div>
    </div>
  )
}