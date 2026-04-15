import { useState } from 'react'
import { Trash2, RefreshCw, Clock, ChevronRight } from 'lucide-react'

const LANG_COLORS = {
  python:     'text-yellow-400 bg-yellow-500/10',
  javascript: 'text-yellow-300 bg-yellow-500/10',
  typescript: 'text-blue-400 bg-blue-500/10',
  java:       'text-orange-400 bg-orange-500/10',
  cpp:        'text-blue-300 bg-blue-500/10',
  c:          'text-blue-200 bg-blue-500/10',
  go:         'text-cyan-400 bg-cyan-500/10',
  rust:       'text-orange-300 bg-orange-500/10',
  sql:        'text-green-400 bg-green-500/10',
}

const STATUS_CONFIG = {
  done:    { dot: 'bg-green-400',                 label: 'Done'    },
  running: { dot: 'bg-yellow-400 animate-pulse',  label: 'Running' },
  pending: { dot: 'bg-white/20',                  label: 'Pending' },
  failed:  { dot: 'bg-red-400',                   label: 'Failed'  },
}

function scoreColor(score) {
  if (score == null) return 'text-white/25'
  if (score >= 80)   return 'text-green-400'
  if (score >= 60)   return 'text-yellow-400'
  if (score >= 40)   return 'text-orange-400'
  return 'text-red-400'
}

function scoreBg(score) {
  if (score == null) return 'bg-surface-600/40'
  if (score >= 80)   return 'bg-green-500/10'
  if (score >= 60)   return 'bg-yellow-500/10'
  if (score >= 40)   return 'bg-orange-500/10'
  return 'bg-red-500/10'
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

export default function SubmissionHistory({
  submissions, activeId, loading,
  onSelect, onDelete, onReEval,
}) {
  const [hovered, setHovered] = useState(null)

  return (
    <div className="flex flex-col h-full border-r border-white/[0.06]">
      {/* Header */}
      <div className="px-4 py-4 border-b border-white/[0.06]">
        <p className="font-display font-700 text-sm text-white">History</p>
        <p className="text-white/25 text-xs mt-0.5">{submissions.length} submissions · click to load</p>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-2">
        {loading && (
          <div className="space-y-2 px-3">
            {[1,2,3].map(i => (
              <div key={i} className="h-16 bg-surface-700/30 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {!loading && submissions.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-white/25 text-xs">No submissions yet.</p>
            <p className="text-white/15 text-xs mt-1">Evaluate your first code above.</p>
          </div>
        )}

        {submissions.map(sub => {
          const statusCfg  = STATUS_CONFIG[sub.status] || STATUS_CONFIG.pending
          const langColor  = LANG_COLORS[sub.language] || 'text-white/40 bg-surface-600'
          // score from the summary list (SubmissionSummary doesn't include evaluations)
          // we store score separately in the list after first eval via stats context
          const isActive   = sub.id === activeId
          const isHovered  = hovered === sub.id

          // Title — use AI-generated title (from service) or fallback
          const displayTitle = sub.title && sub.title !== `${sub.language} submission`
            ? sub.title
            : `${sub.language.charAt(0).toUpperCase() + sub.language.slice(1)} #${sub.id}`

          return (
            <div
              key={sub.id}
              onMouseEnter={() => setHovered(sub.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect(sub.id)}
              className={`group relative mx-2 mb-1 px-3 py-3 rounded-xl cursor-pointer transition-all ${
                isActive
                  ? 'bg-brand-600/10 border border-brand-500/25 shadow-sm'
                  : 'hover:bg-surface-700/50 border border-transparent hover:border-white/[0.06]'
              }`}
            >
              <div className="flex items-start gap-2.5">
                {/* Status dot */}
                <div className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${statusCfg.dot}`} />

                <div className="flex-1 min-w-0">
                  {/* Title — AI-generated meaningful name */}
                  <p className={`text-xs font-display font-600 truncate leading-tight ${isActive ? 'text-brand-300' : 'text-white/80'}`}
                     title={displayTitle}>
                    {displayTitle}
                  </p>

                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {/* Language badge */}
                    <span className={`px-1.5 py-0.5 rounded-md text-xs font-mono capitalize ${langColor}`}>
                      {sub.language}
                    </span>

                    {/* Eval count */}
                    {sub.eval_count > 0 && (
                      <span className="text-white/20 text-xs font-mono">{sub.eval_count}× eval</span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 mt-1">
                    <Clock size={10} className="text-white/20" />
                    <span className="text-white/20 text-xs">{timeAgo(sub.created_at)}</span>
                  </div>
                </div>

                {/* Load arrow indicator */}
                {isHovered && !isActive && (
                  <ChevronRight size={14} className="text-brand-400 shrink-0 self-center animate-fade-in" />
                )}
              </div>

              {/* Action row (appears on hover) */}
              <div className={`flex items-center gap-1 mt-2 transition-all ${isHovered || isActive ? 'opacity-100' : 'opacity-0'}`}>
                <button
                  onClick={e => { e.stopPropagation(); onReEval(sub.id) }}
                  className="flex items-center gap-1 px-2 py-1 text-white/30 hover:text-brand-400 hover:bg-brand-600/10 rounded-lg transition-all text-xs"
                  title="Re-evaluate"
                >
                  <RefreshCw size={11} /> Re-eval
                </button>
                <button
                  onClick={e => { e.stopPropagation(); onDelete(sub.id) }}
                  className="flex items-center gap-1 px-2 py-1 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all text-xs ml-auto"
                  title="Delete"
                >
                  <Trash2 size={11} /> Delete
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}