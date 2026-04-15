import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Sparkles, RefreshCw, BookOpen,
  Info, Filter, Youtube, Zap
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useRecommendations } from '../hooks/useRecommendations'
import AgentThinkingPanel from '../components/recommendation/AgentThinkingPanel'
import RecommendationCard from '../components/recommendation/RecommendationCard'
import AgentStatsBar from '../components/recommendation/AgentStatsBar'

const CONTENT_TYPES    = ['all', 'video', 'article', 'exercise', 'quiz', 'project', 'tutorial']
const DIFFICULTY_FILTERS = ['all', 'beginner', 'intermediate', 'advanced']

export default function RecommendationPage() {
  const { user }   = useAuth()
  const navigate   = useNavigate()
  const {
    recommendations, agentLog, thoughtSteps,
    loading, generating,
    fetchRecommendations, fetchAgentLog, runAgent,
    logInteraction, dismiss,
  } = useRecommendations()

  const [typeFilter,   setTypeFilter]   = useState('all')
  const [diffFilter,   setDiffFilter]   = useState('all')
  const [showFilters,  setShowFilters]  = useState(false)

  useEffect(() => {
    fetchRecommendations()
    fetchAgentLog()
  }, [])

  const filtered = recommendations.filter(r => {
    const typeOk = typeFilter === 'all' || r.content.content_type === typeFilter
    const diffOk = diffFilter === 'all' || r.content.difficulty   === diffFilter
    return typeOk && diffOk
  })

  const hasProfile =
    (user?.preferred_languages?.length > 0) ||
    (user?.learning_goals?.length > 0) ||
    (user?.skill_level && user.skill_level !== 'beginner')

  const ytCount = recommendations.filter(r =>
    r.content.url && (r.content.url.includes('youtube.com') || r.content.url.includes('youtu.be'))
  ).length

  return (
    <div className="min-h-screen">

      {/* ── Navbar ── */}
      <nav className="border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center gap-4">
          <button onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 text-white/40 hover:text-white/70 transition-colors">
            <ArrowLeft size={18} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-purple-600 flex items-center justify-center">
              <BookOpen size={14} className="text-white" />
            </div>
            <span className="font-display font-700 text-lg text-white">
              Content <span className="text-purple-400">Recommendation</span> Agent
            </span>
          </div>
          <div className="ml-auto">
            {/* Single action: Run Agent — seed happens automatically inside agent */}
            <button
              onClick={runAgent}
              disabled={generating}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-sm font-display font-600 rounded-xl transition-all"
            >
              {generating
                ? <><RefreshCw size={15} className="animate-spin" /> Running Agent...</>
                : <><Sparkles size={15} /> Run Agent</>}
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* ── Header ── */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-purple-400 text-xs font-mono mb-2">
            <Sparkles size={12} /> CF + CBF + RL + Groq LLM · YouTube-powered
          </div>
          <h1 className="font-display font-800 text-3xl text-white mb-2">
            Your Learning Path
          </h1>
          <p className="text-white/40 text-sm max-w-xl leading-relaxed">
            Recommendations built entirely from your profile — your topics, languages, and skill level.
            Real YouTube videos fetched per topic, ranked by Groq AI, fresh every session.
          </p>
        </div>

        {/* ── Profile completeness warning ── */}
        {!hasProfile && (
          <div className="glass-card border-yellow-500/20 p-5 mb-6 flex items-start gap-4">
            <Info size={18} className="text-yellow-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-display font-600 text-yellow-300 text-sm mb-1">
                Add topics to your profile to get recommendations
              </p>
              <p className="text-white/40 text-xs">
                The agent uses your saved topics, preferred languages, and skill level
                to generate personalised content. No profile = no recommendations.
              </p>
              <button
                onClick={() => navigate('/profile')}
                className="mt-3 px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 text-xs font-display rounded-lg hover:bg-yellow-500/20 transition-colors"
              >
                Update Profile →
              </button>
            </div>
          </div>
        )}

        {/* ── How it works ── */}
        <div className="glass-card p-5 mb-6">
          <p className="text-white/30 text-xs font-mono uppercase tracking-wider mb-4">How the Agent Works</p>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { step: '1', label: 'Profile Read',         desc: 'Topics, languages, skill level', color: 'text-teal-400   bg-teal-600/10'   },
              { step: '2', label: 'Content Generation',   desc: 'YouTube search per your topics', color: 'text-red-400    bg-red-600/10'    },
              { step: '3', label: 'Collab. Filtering',    desc: 'Similar learner patterns',       color: 'text-blue-400   bg-blue-600/10'   },
              { step: '4', label: 'Content-Based',        desc: 'Matches topics + difficulty',    color: 'text-green-400  bg-green-600/10'  },
              { step: '5', label: 'Groq AI Ranking',      desc: 'Re-ranks + explains picks',      color: 'text-brand-400  bg-brand-600/10'  },
            ].map(s => (
              <div key={s.step} className={`rounded-xl p-3 ${s.color.split(' ')[1]}`}>
                <div className={`text-xs font-mono mb-1 ${s.color.split(' ')[0]}`}>Step {s.step}</div>
                <div className="font-display font-600 text-xs text-white mb-0.5">{s.label}</div>
                <div className="text-white/30 text-xs">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Agent Thinking Panel ── */}
        {(generating || thoughtSteps.length > 0) && (
          <div className="mb-6">
            <AgentThinkingPanel steps={thoughtSteps} generating={generating} />
          </div>
        )}

        {/* ── Agent Stats ── */}
        {agentLog && !generating && (
          <div className="mb-6">
            <AgentStatsBar log={agentLog} />
          </div>
        )}

        {/* ── Empty state ── */}
        {!generating && recommendations.length === 0 && thoughtSteps.length === 0 && (
          <div className="glass-card p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-purple-600/10 border border-purple-500/20 flex items-center justify-center mx-auto mb-5">
              <Sparkles size={28} className="text-purple-400" />
            </div>
            <h3 className="font-display font-700 text-white text-xl mb-2">
              Ready to generate your learning path
            </h3>
            <p className="text-white/40 text-sm mb-6 max-w-md mx-auto">
              Click <strong className="text-white">Run Agent</strong> — it reads your profile topics
              and languages, fetches real YouTube content for each, then uses Groq AI to rank
              and explain every pick just for you.
            </p>
            <div className="flex flex-col items-center gap-3">
              <button
                onClick={runAgent}
                disabled={generating}
                className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white font-display font-600 rounded-xl transition-colors"
              >
                <Sparkles size={16} /> Run Agent
              </button>
              <div className="flex items-center gap-4 text-white/20 text-xs font-mono">
                <span className="flex items-center gap-1"><Youtube size={11} className="text-red-400/60" /> Real YouTube videos</span>
                <span className="flex items-center gap-1"><Zap size={11} className="text-brand-400/60" /> Groq-powered ranking</span>
              </div>
            </div>
          </div>
        )}

        {/* ── Recommendations list ── */}
        {recommendations.length > 0 && !generating && (
          <>
            {/* Header row */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="font-display font-700 text-white text-lg">
                  {filtered.length} Recommended for You
                </h2>
                <div className="flex items-center gap-3 mt-0.5">
                  <p className="text-white/30 text-xs">Sorted by agent score · Dismiss to hide</p>
                  {ytCount > 0 && (
                    <span className="flex items-center gap-1 text-red-400/70 text-xs font-mono">
                      <Youtube size={11} /> {ytCount} YouTube videos
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setShowFilters(v => !v)}
                className="flex items-center gap-1.5 px-3 py-2 text-white/40 hover:text-white/70 hover:bg-surface-700 rounded-xl transition-colors text-sm font-display"
              >
                <Filter size={14} /> Filter
              </button>
            </div>

            {/* Filter controls */}
            {showFilters && (
              <div className="glass-card p-4 mb-5 animate-fade-in space-y-3">
                <div>
                  <p className="label">Content Type</p>
                  <div className="flex flex-wrap gap-2">
                    {CONTENT_TYPES.map(t => (
                      <button key={t} onClick={() => setTypeFilter(t)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-display font-600 capitalize border transition-all ${
                          typeFilter === t
                            ? 'border-purple-500/60 bg-purple-600/10 text-purple-300'
                            : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'
                        }`}>
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="label">Difficulty</p>
                  <div className="flex flex-wrap gap-2">
                    {DIFFICULTY_FILTERS.map(d => (
                      <button key={d} onClick={() => setDiffFilter(d)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-display font-600 capitalize border transition-all ${
                          diffFilter === d
                            ? 'border-purple-500/60 bg-purple-600/10 text-purple-300'
                            : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'
                        }`}>
                        {d}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Cards */}
            <div className="space-y-4">
              {filtered.length === 0 ? (
                <p className="text-white/30 text-sm text-center py-8">
                  No recommendations match these filters.
                </p>
              ) : (
                filtered.map(rec => (
                  <RecommendationCard
                    key={rec.id}
                    rec={rec}
                    rank={rec.rank}
                    onDismiss={dismiss}
                    onInteract={logInteraction}
                  />
                ))
              )}
            </div>

            {/* Re-run */}
            <div className="text-center mt-10">
              <button
                onClick={runAgent}
                disabled={generating}
                className="flex items-center gap-2 px-6 py-3 bg-surface-700 hover:bg-surface-600 border border-white/10 text-white/60 hover:text-white text-sm font-display font-600 rounded-xl transition-all mx-auto"
              >
                <RefreshCw size={16} /> Regenerate Recommendations
              </button>
              <p className="text-white/20 text-xs mt-2">
                Runs full pipeline: CF + CBF + YouTube search + Groq reasoning
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}