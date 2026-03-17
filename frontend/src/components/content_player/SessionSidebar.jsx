import { useState } from 'react'
import {
  Plus, MessageSquare, Code2, Brain, Puzzle,
  BookOpen, Archive, Clock, ChevronRight, Sparkles
} from 'lucide-react'

const MODE_CONFIG = {
  qa:          { icon: MessageSquare, label: 'Q&A',         color: 'text-brand-400 bg-brand-600/10' },
  code_help:   { icon: Code2,          label: 'Code Help',  color: 'text-green-400 bg-green-600/10' },
  brainstorm:  { icon: Brain,          label: 'Brainstorm', color: 'text-purple-400 bg-purple-600/10' },
  quiz:        { icon: Puzzle,         label: 'Quiz',       color: 'text-yellow-400 bg-yellow-600/10' },
  walkthrough: { icon: BookOpen,       label: 'Walkthrough',color: 'text-pink-400 bg-pink-600/10' },
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function SessionItem({ session, isActive, onClick, onArchive }) {
  const cfg  = MODE_CONFIG[session.mode] || MODE_CONFIG.qa
  const Icon = cfg.icon
  const [hover, setHover] = useState(false)

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className={`group relative flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all ${
        isActive
          ? 'bg-brand-600/10 border border-brand-500/20'
          : 'hover:bg-surface-700/50 border border-transparent'
      }`}
      onClick={onClick}
    >
      <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${cfg.color}`}>
        <Icon size={15} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-display font-600 text-white/80 truncate leading-tight">
          {session.title || `New ${cfg.label} session`}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-white/25 text-xs">{timeAgo(session.last_message_at || session.created_at)}</span>
          {session.total_messages > 0 && (
            <span className="text-white/20 text-xs">{session.total_messages} msgs</span>
          )}
          {session.confusion_detected && (
            <span className="text-yellow-400/50 text-xs">⚠</span>
          )}
        </div>
      </div>

      {/* Archive button on hover */}
      {hover && !isActive && (
        <button
          onClick={(e) => { e.stopPropagation(); onArchive(session.id) }}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-white/20 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
          title="Archive session"
        >
          <Archive size={13} />
        </button>
      )}
    </div>
  )
}

export default function SessionSidebar({
  sessions, activeSessionId, loading,
  onSelectSession, onNewSession, onArchive
}) {
  const [showNewModal, setShowNewModal] = useState(false)
  const [newMode, setNewMode]           = useState('qa')
  const [newLang, setNewLang]           = useState('')
  const [newTopic, setNewTopic]         = useState('')

  const handleCreate = () => {
    onNewSession({ mode: newMode, language: newLang || null, topic: newTopic || null })
    setShowNewModal(false)
    setNewMode('qa')
    setNewLang('')
    setNewTopic('')
  }

  return (
    <div className="flex flex-col h-full border-r border-white/[0.06] bg-surface-900/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-600/20 flex items-center justify-center">
            <Sparkles size={14} className="text-brand-400" />
          </div>
          <span className="font-display font-700 text-sm text-white">Sessions</span>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-display font-600 rounded-lg transition-colors"
        >
          <Plus size={13} />
          New
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
        {loading && (
          <div className="space-y-2 px-2">
            {[1,2,3].map(i => (
              <div key={i} className="h-14 bg-surface-700/30 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="px-4 py-8 text-center">
            <MessageSquare size={24} className="text-white/15 mx-auto mb-3" />
            <p className="text-white/30 text-xs">No sessions yet.</p>
            <p className="text-white/20 text-xs mt-1">Click New to start learning.</p>
          </div>
        )}

        {sessions.map(s => (
          <SessionItem
            key={s.id}
            session={s}
            isActive={s.id === activeSessionId}
            onClick={() => onSelectSession(s.id)}
            onArchive={onArchive}
          />
        ))}
      </div>

      {/* New Session Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowNewModal(false)}>
          <div className="glass-card w-full max-w-sm p-6 animate-slide-up"
            onClick={e => e.stopPropagation()}>
            <h3 className="font-display font-700 text-white text-lg mb-1">Start a Session</h3>
            <p className="text-white/40 text-sm mb-5">Choose how you want to learn today</p>

            {/* Mode selection */}
            <p className="label">Learning Mode</p>
            <div className="grid grid-cols-1 gap-2 mb-4">
              {Object.entries(MODE_CONFIG).map(([val, cfg]) => {
                const Icon = cfg.icon
                return (
                  <button key={val}
                    onClick={() => setNewMode(val)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left ${
                      newMode === val
                        ? 'border-brand-500/40 bg-brand-600/10'
                        : 'border-white/[0.06] hover:border-white/15 hover:bg-surface-700/40'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cfg.color}`}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <p className="text-sm font-display font-600 text-white">{cfg.label}</p>
                    </div>
                    {newMode === val && <ChevronRight size={14} className="text-brand-400 ml-auto" />}
                  </button>
                )
              })}
            </div>

            {/* Language */}
            <p className="label">Language (optional)</p>
            <select
              value={newLang}
              onChange={e => setNewLang(e.target.value)}
              className="input-field mb-4"
            >
              <option value="">Any language</option>
              {['Python','JavaScript','Java','C++','C','TypeScript','Go','Rust','SQL'].map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>

            {/* Topic */}
            <p className="label">Topic (optional)</p>
            <input
              value={newTopic}
              onChange={e => setNewTopic(e.target.value)}
              placeholder="e.g. Binary Trees, React Hooks..."
              className="input-field mb-5"
            />

            <div className="flex gap-3">
              <button onClick={() => setShowNewModal(false)}
                className="flex-1 px-4 py-2.5 bg-surface-600 hover:bg-surface-500 text-white/60 text-sm font-display font-600 rounded-xl transition-colors">
                Cancel
              </button>
              <button onClick={handleCreate}
                className="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-sm font-display font-600 rounded-xl transition-colors">
                Start Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}