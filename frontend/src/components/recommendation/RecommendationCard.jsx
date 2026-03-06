import { useState } from 'react'
import {
  ExternalLink, X, Star, Clock, ChevronDown, ChevronUp,
  Video, BookOpen, Code2, FileQuestion, Wrench, BookMarked,
  Zap, Users, Target, Sparkles
} from 'lucide-react'

const CONTENT_TYPE_CONFIG = {
  video    : { icon: Video,       label: 'Video',    color: 'text-red-400 bg-red-500/10 border-red-500/20' },
  article  : { icon: BookOpen,    label: 'Article',  color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  exercise : { icon: Code2,       label: 'Exercise', color: 'text-green-400 bg-green-500/10 border-green-500/20' },
  quiz     : { icon: FileQuestion,label: 'Quiz',     color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' },
  project  : { icon: Wrench,      label: 'Project',  color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  tutorial : { icon: BookMarked,  label: 'Tutorial', color: 'text-brand-400 bg-brand-500/10 border-brand-500/20' },
}

const DIFFICULTY_COLORS = {
  beginner    : 'text-green-400 bg-green-500/10',
  intermediate: 'text-yellow-400 bg-yellow-500/10',
  advanced    : 'text-red-400 bg-red-500/10',
}

function ScoreBar({ label, value, color, icon: Icon }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={11} className={color} />
      <span className="text-white/30 text-xs w-8 font-mono">{label}</span>
      <div className="flex-1 h-1 bg-surface-600 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${
          color.includes('blue') ? 'bg-blue-500' :
          color.includes('green') ? 'bg-green-500' :
          color.includes('purple') ? 'bg-purple-500' : 'bg-brand-500'
        }`} style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="text-white/40 text-xs font-mono w-8">{(value * 100).toFixed(0)}%</span>
    </div>
  )
}

export default function RecommendationCard({ rec, rank, onDismiss, onInteract }) {
  const [expanded, setExpanded]   = useState(false)
  const [interacted, setInteracted] = useState(false)

  const { content } = rec
  const typeConfig  = CONTENT_TYPE_CONFIG[content.content_type] || CONTENT_TYPE_CONFIG.article
  const TypeIcon    = typeConfig.icon

  const handleOpen = () => {
    if (!interacted) {
      onInteract(content.id, 'view')
      setInteracted(true)
    }
    if (content.url) window.open(content.url, '_blank')
  }

  return (
    <div className="glass-card hover:border-white/15 transition-all duration-300 group animate-slide-up overflow-hidden"
      style={{ animationDelay: `${(rank - 1) * 60}ms`, animationFillMode: 'both' }}>

      {/* Rank badge */}
      <div className="flex items-start gap-4 p-5">
        <div className="shrink-0 w-8 h-8 rounded-lg bg-surface-600 flex items-center justify-center">
          <span className="font-display font-700 text-xs text-white/50">#{rank}</span>
        </div>

        <div className="flex-1 min-w-0">
          {/* Top row: type badge + difficulty + duration */}
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-xs font-display font-600 ${typeConfig.color}`}>
              <TypeIcon size={11} />
              {typeConfig.label}
            </span>
            <span className={`px-2 py-0.5 rounded-md text-xs font-mono capitalize ${DIFFICULTY_COLORS[content.difficulty]}`}>
              {content.difficulty}
            </span>
            {content.duration_mins && (
              <span className="flex items-center gap-1 text-white/30 text-xs">
                <Clock size={11} />
                {content.duration_mins}m
              </span>
            )}
            {content.language && content.language !== 'general' && (
              <span className="px-2 py-0.5 rounded-md bg-surface-600 text-white/40 text-xs font-mono">
                {content.language}
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="font-display font-600 text-white text-sm leading-snug mb-1 group-hover:text-brand-300 transition-colors">
            {content.title}
          </h3>

          {/* Source + rating */}
          <div className="flex items-center gap-3 mb-3">
            {content.source && (
              <span className="text-white/30 text-xs">{content.source}</span>
            )}
            {content.avg_rating > 0 && (
              <span className="flex items-center gap-1 text-yellow-400 text-xs">
                <Star size={11} fill="currentColor" />
                {content.avg_rating.toFixed(1)}
              </span>
            )}
          </div>

          {/* Topics */}
          {content.topics?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {content.topics.slice(0, 5).map(t => (
                <span key={t} className="px-2 py-0.5 bg-surface-600/60 rounded-md text-white/40 text-xs font-mono">
                  {t}
                </span>
              ))}
            </div>
          )}

          {/* AI Reasoning (collapsed by default) */}
          {rec.agent_reasoning && (
            <div>
              <button
                onClick={() => setExpanded(v => !v)}
                className="flex items-center gap-1.5 text-brand-400 text-xs font-display font-600 hover:text-brand-300 transition-colors mb-2"
              >
                <Sparkles size={12} />
                AI Reasoning
                {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {expanded && (
                <div className="bg-brand-600/5 border border-brand-500/15 rounded-xl px-4 py-3 mb-3 animate-fade-in">
                  <p className="text-white/60 text-xs font-body leading-relaxed">
                    {rec.agent_reasoning}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Score bars */}
          {expanded && (
            <div className="space-y-2 mb-3 animate-fade-in">
              <p className="text-white/20 text-xs font-mono uppercase tracking-wider mb-2">Scoring Breakdown</p>
              <ScoreBar label="CF"  value={rec.cf_score}  color="text-blue-400"   icon={Users} />
              <ScoreBar label="CBF" value={rec.cbf_score} color="text-green-400"  icon={Target} />
              <ScoreBar label="RL"  value={rec.rl_bonus}  color="text-purple-400" icon={Zap} />
              <ScoreBar label="All" value={rec.score}     color="text-brand-400"  icon={Sparkles} />
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-2 mt-1">
            <button
              onClick={handleOpen}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-display font-600 rounded-lg transition-colors"
            >
              <ExternalLink size={12} />
              {interacted ? 'Reopen' : 'Start Learning'}
            </button>
            <button
              onClick={() => { onInteract(content.id, 'bookmark') }}
              className="px-3 py-1.5 bg-surface-600 hover:bg-surface-500 text-white/50 hover:text-white text-xs font-display rounded-lg transition-colors"
            >
              Bookmark
            </button>
            <button
              onClick={() => setExpanded(v => !v)}
              className="px-3 py-1.5 bg-surface-600 hover:bg-surface-500 text-white/50 hover:text-white text-xs font-display rounded-lg transition-colors ml-auto"
            >
              {expanded ? 'Less' : 'Details'}
            </button>
            <button
              onClick={() => onDismiss(rec.id)}
              className="p-1.5 text-white/20 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10"
              title="Dismiss"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}