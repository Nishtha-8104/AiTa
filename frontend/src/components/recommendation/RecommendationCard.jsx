import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ExternalLink, X, Star, Clock, ChevronDown, ChevronUp,
  Video, BookOpen, Code2, FileQuestion, Wrench, BookMarked,
  Zap, Users, Target, Sparkles, Youtube, Play, ArrowRight
} from 'lucide-react'

const CONTENT_TYPE_CONFIG = {
  video    : { icon: Video,        label: 'Video',     color: 'text-red-400   bg-red-500/10   border-red-500/20'    },
  article  : { icon: BookOpen,     label: 'Article',   color: 'text-blue-400  bg-blue-500/10  border-blue-500/20'   },
  exercise : { icon: Code2,        label: 'Exercise',  color: 'text-green-400 bg-green-500/10 border-green-500/20'  },
  quiz     : { icon: FileQuestion, label: 'Quiz',      color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'},
  project  : { icon: Wrench,       label: 'Project',   color: 'text-purple-400 bg-purple-500/10 border-purple-500/20'},
  tutorial : { icon: BookMarked,   label: 'Tutorial',  color: 'text-brand-400 bg-brand-500/10 border-brand-500/20'  },
}

const DIFFICULTY_COLORS = {
  beginner    : 'text-green-400  bg-green-500/10',
  intermediate: 'text-yellow-400 bg-yellow-500/10',
  advanced    : 'text-red-400    bg-red-500/10',
}

function fmt(n) {
  if (!n) return null
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`
  return String(n)
}

function ScoreBar({ label, value, color, icon: Icon }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={11} className={color} />
      <span className="text-white/30 text-xs w-8 font-mono">{label}</span>
      <div className="flex-1 h-1 bg-surface-600 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${
          color.includes('blue') ? 'bg-blue-500' : color.includes('green') ? 'bg-green-500' :
          color.includes('purple') ? 'bg-purple-500' : 'bg-brand-500'
        }`} style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="text-white/40 text-xs font-mono w-8">{(value * 100).toFixed(0)}%</span>
    </div>
  )
}

function isYouTube(url) {
  return url && (url.includes('youtube.com') || url.includes('youtu.be'))
}

// Derive a clean topic name from content title for Content Player pre-fill
function topicFromContent(content) {
  // Strip source prefix patterns like "Python for Beginners – " → "Python Basics"
  // Use the first meaningful chunk of the title
  const title = content.title || ''
  const cleaned = title
    .replace(/\s*[-–—|]\s*.*/,'')   // remove anything after dash/pipe
    .replace(/\s*[:(].*/,'')         // remove anything after colon/paren
    .trim()
  return cleaned.slice(0, 60) || title.slice(0, 60)
}

export default function RecommendationCard({ rec, rank, onDismiss, onInteract }) {
  const navigate    = useNavigate()
  const [expanded,   setExpanded]   = useState(false)
  const [interacted, setInteracted] = useState(false)

  const { content } = rec
  const typeConfig  = CONTENT_TYPE_CONFIG[content.content_type] || CONTENT_TYPE_CONFIG.article
  const TypeIcon    = typeConfig.icon
  const hasYT       = isYouTube(content.url)
  const hasThumb    = !!content.thumbnail_url

  // Parse agent_reasoning — may be JSON {description, difficulty, why_relevant} or plain text
  const reasoning = (() => {
    if (!rec.agent_reasoning) return null
    try {
      const parsed = JSON.parse(rec.agent_reasoning)
      return {
        description:  parsed.description  || '',
        difficulty:   parsed.difficulty   || '',
        why_relevant: parsed.why_relevant || '',
      }
    } catch {
      // legacy plain-text fallback
      return { description: '', difficulty: '', why_relevant: rec.agent_reasoning }
    }
  })()

  // Open the external resource (YouTube/article)
  const handleOpen = () => {
    if (!interacted) { onInteract(content.id, 'view'); setInteracted(true) }
    if (content.url) window.open(content.url, '_blank')
  }

  // Navigate to Content Player with topic pre-filled (pipeline connection)
  const handleLearn = () => {
    onInteract(content.id, 'view')
    navigate('/learn', {
      state: {
        topic: topicFromContent(content),
        fromRecommendation: true,
      }
    })
  }

  return (
    <div className="glass-card hover:border-white/15 transition-all duration-300 group animate-slide-up overflow-hidden"
      style={{ animationDelay: `${(rank - 1) * 60}ms`, animationFillMode: 'both' }}>
      <div className="flex items-start">

        {/* ── YouTube thumbnail ── */}
        {hasThumb && (
          <div className="relative shrink-0 w-36 self-stretch overflow-hidden cursor-pointer"
            onClick={handleOpen}>
            <img src={content.thumbnail_url} alt={content.title}
              className="w-full h-full object-cover opacity-80 hover:opacity-100 transition-opacity"
              style={{ minHeight: '100px' }} />
            {(content.content_type === 'video' || hasYT) && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/10 transition-colors">
                <div className="w-10 h-10 rounded-full bg-red-600/90 flex items-center justify-center shadow-lg">
                  <Play size={16} className="text-white ml-0.5" fill="white" />
                </div>
              </div>
            )}
            {hasYT && (
              <div className="absolute top-2 left-2">
                <span className="flex items-center gap-1 px-1.5 py-0.5 bg-red-600/90 rounded-md text-white text-xs font-mono font-600">
                  <Youtube size={10} /> YT
                </span>
              </div>
            )}
          </div>
        )}

        {/* ── Content body ── */}
        <div className="flex-1 min-w-0 p-4">

          {/* Badges row */}
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-md bg-surface-600 flex items-center justify-center shrink-0">
              <span className="font-display font-700 text-xs text-white/40">#{rank}</span>
            </div>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-display font-600 ${typeConfig.color}`}>
              <TypeIcon size={10} /> {typeConfig.label}
            </span>
            <span className={`px-2 py-0.5 rounded-md text-xs font-mono capitalize ${DIFFICULTY_COLORS[content.difficulty]}`}>
              {content.difficulty}
            </span>
            {content.duration_mins && (
              <span className="flex items-center gap-1 text-white/30 text-xs">
                <Clock size={10} /> {Math.round(content.duration_mins)}m
              </span>
            )}
            {content.language && content.language !== 'general' && (
              <span className="px-2 py-0.5 rounded-md bg-surface-600 text-white/40 text-xs font-mono">{content.language}</span>
            )}
          </div>

          {/* Title */}
          <h3 className="font-display font-600 text-white text-sm leading-snug mb-1.5 group-hover:text-brand-300 transition-colors cursor-pointer"
            onClick={handleOpen}>
            {content.title}
          </h3>

          {/* Source + rating */}
          <div className="flex flex-wrap items-center gap-3 mb-2">
            {(content.author || content.source) && (
              <span className="text-white/30 text-xs truncate max-w-[180px]">{content.author || content.source}</span>
            )}
            {content.avg_rating > 0 && (
              <span className="flex items-center gap-1 text-yellow-400 text-xs">
                <Star size={10} fill="currentColor" /> {content.avg_rating.toFixed(1)}
              </span>
            )}
          </div>

          {/* Topics */}
          {content.topics?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {content.topics.slice(0, 5).map(t => (
                <span key={t} className="px-2 py-0.5 bg-surface-600/60 rounded-md text-white/40 text-xs font-mono">{t}</span>
              ))}
            </div>
          )}

          {/* AI Reasoning */}
          {reasoning && (
            <div className="mb-2">
              {/* Description — always visible */}
              {reasoning.description && (
                <p className="text-white/50 text-xs font-body leading-relaxed mb-2">
                  {reasoning.description}
                </p>
              )}

              {/* Why relevant — expandable */}
              {reasoning.why_relevant && (
                <>
                  <button onClick={() => setExpanded(v => !v)}
                    className="flex items-center gap-1.5 text-brand-400 text-xs font-display font-600 hover:text-brand-300 transition-colors">
                    <Sparkles size={11} /> Why it's for you
                    {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  </button>
                  {expanded && (
                    <div className="mt-2 bg-brand-600/5 border border-brand-500/15 rounded-xl px-4 py-3 animate-fade-in">
                      {reasoning.difficulty && (
                        <p className="text-white/30 text-xs font-mono mb-1">
                          Difficulty: <span className={`capitalize font-600 ${DIFFICULTY_COLORS[reasoning.difficulty.toLowerCase()] || 'text-white/50'}`}>{reasoning.difficulty}</span>
                        </p>
                      )}
                      <p className="text-white/60 text-xs font-body leading-relaxed">{reasoning.why_relevant}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Score bars */}
          {expanded && (
            <div className="space-y-2 mt-3 mb-2 animate-fade-in">
              <p className="text-white/20 text-xs font-mono uppercase tracking-wider">Scoring</p>
              <ScoreBar label="CF"  value={rec.cf_score}  color="text-blue-400"   icon={Users}    />
              <ScoreBar label="CBF" value={rec.cbf_score} color="text-green-400"  icon={Target}   />
              <ScoreBar label="RL"  value={rec.rl_bonus}  color="text-purple-400" icon={Zap}      />
              <ScoreBar label="All" value={rec.score}     color="text-brand-400"  icon={Sparkles} />
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {/* Primary CTA: Learn with Content Player (pipeline step 3) */}
            <button
              onClick={handleLearn}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-display font-600 rounded-lg transition-all"
              title="Open in Content Player — get a walkthrough of this topic"
            >
              <ArrowRight size={12} /> Learn This
            </button>

            {/* Secondary: open original resource */}
            {content.url && (
              <button
                onClick={handleOpen}
                disabled={!content.url}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-white text-xs font-display font-600 rounded-lg transition-all ${
                  hasYT ? 'bg-red-600/80 hover:bg-red-600' : 'bg-surface-600 hover:bg-surface-500'
                }`}
              >
                {hasYT ? <Youtube size={12} /> : <ExternalLink size={12} />}
                {hasYT ? 'Watch' : 'Open'}
              </button>
            )}

            <button onClick={() => onInteract(content.id, 'bookmark')}
              className="px-3 py-1.5 bg-surface-600 hover:bg-surface-500 text-white/50 hover:text-white text-xs font-display rounded-lg transition-colors">
              Bookmark
            </button>

            <button onClick={() => setExpanded(v => !v)}
              className="px-3 py-1.5 bg-surface-600 hover:bg-surface-500 text-white/50 hover:text-white text-xs font-display rounded-lg transition-colors ml-auto">
              {expanded ? 'Less' : 'Details'}
            </button>

            <button onClick={() => onDismiss(rec.id)}
              className="p-1.5 text-white/20 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10"
              title="Dismiss">
              <X size={13} />
            </button>
          </div>

          {/* YouTube URL */}
          {hasYT && content.url && (
            <p className="mt-2 text-white/20 text-xs font-mono truncate" title={content.url}>
              🔗 {content.url}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}