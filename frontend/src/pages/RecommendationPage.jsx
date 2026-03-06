import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Sparkles, RefreshCw, BookOpen,
  Database, Info, Filter
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useRecommendations } from '../hooks/useRecommendations'
import AgentThinkingPanel from '../components/recommendation/AgentThinkingPanel'
import RecommendationCard from '../components/recommendation/RecommendationCard'
import AgentStatsBar from '../components/recommendation/AgentStatsBar'
import toast from 'react-hot-toast'

const CONTENT_TYPES = ['all', 'video', 'article', 'exercise', 'quiz', 'project', 'tutorial']
const DIFFICULTY_FILTERS = ['all', 'beginner', 'intermediate', 'advanced']

export default function RecommendationPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const {
    recommendations, agentLog, thoughtSteps,
    loading, generating, seeding,
    fetchRecommendations, fetchAgentLog, runAgent,
    logInteraction, dismiss, seedContent,
  } = useRecommendations()

  const [typeFilter, setTypeFilter]   = useState('all')
  const [diffFilter, setDiffFilter]   = useState('all')
  const [showFilters, setShowFilters] = useState(false)

  // Load existing recommendations on mount
  useEffect(() => {
    fetchRecommendations()
    fetchAgentLog()
  }, [])

  // Filtered list
  const filtered = recommendations.filter(r => {
    const typeOk = typeFilter === 'all' || r.content.content_type === typeFilter
    const diffOk = diffFilter === 'all' || r.content.difficulty  === diffFilter
    return typeOk && diffOk
  })

  const hasProfile =
    (user?.preferred_languages?.length > 0) ||
    (user?.learning_goals?.length > 0) ||
    (user?.skill_level && user.skill_level !== 'beginner')

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
          <div className="ml-auto flex items-center gap-2">
            {/* Seed content button */}
            <button
              onClick={seedContent}
              disabled={seeding}
              title="Seed starter content catalog"
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-white/40 hover:text-white/70 hover:bg-surface-700 transition-colors text-xs font-display"
            >
              <Database size={14} />
              <span className="hidden sm:block">{seeding ? 'Seeding...' : 'Seed Content'}</span>
            </button>

            {/* Run Agent */}
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
            <Sparkles size={12} /> AI-Powered · Collaborative Filtering + LLM Reasoning
          </div>
          <h1 className="font-display font-800 text-3xl text-white mb-2">
            Your Learning Path
          </h1>
          <p className="text-white/40 text-sm max-w-xl">
            The agent analyses your profile, finds learners similar to you, matches content
            to your weak areas, then uses Claude AI to re-rank and explain every pick.
          </p>
        </div>

        {/* ── Profile completeness warning ── */}
        {!hasProfile && (
          <div className="glass-card border-yellow-500/20 p-5 mb-6 flex items-start gap-4">
            <Info size={18} className="text-yellow-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-display font-600 text-yellow-300 text-sm mb-1">
                Complete your profile for better recommendations
              </p>
              <p className="text-white/40 text-xs">
                Add your skill level, preferred languages, and learning goals so the agent
                can personalise your learning path.
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

        {/* ── How it works banner ── */}
        <div className="glass-card p-5 mb-6">
          <p className="text-white/30 text-xs font-mono uppercase tracking-wider mb-4">How the Agent Works</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { step: '1', label: 'Collaborative Filtering', desc: 'Finds learners similar to you', color: 'text-blue-400 bg-blue-600/10' },
              { step: '2', label: 'Content-Based Filter', desc: 'Matches topics to your profile', color: 'text-green-400 bg-green-600/10' },
              { step: '3', label: 'RL Exploration Bonus', desc: 'Diversifies content types', color: 'text-purple-400 bg-purple-600/10' },
              { step: '4', label: 'Claude LLM Reasoning', desc: 'Re-ranks + explains each pick', color: 'text-brand-400 bg-brand-600/10' },
            ].map(s => (
              <div key={s.step} className={`rounded-xl p-3 ${s.color.split(' ')[1]}`}>
                <div className={`text-xs font-mono mb-1 ${s.color.split(' ')[0]}`}>Step {s.step}</div>
                <div className="font-display font-600 text-xs text-white mb-1">{s.label}</div>
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

        {/* ── Empty state: never run ── */}
        {!generating && recommendations.length === 0 && thoughtSteps.length === 0 && (
          <div className="glass-card p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-purple-600/10 border border-purple-500/20 flex items-center justify-center mx-auto mb-5">
              <Sparkles size={28} className="text-purple-400" />
            </div>
            <h3 className="font-display font-700 text-white text-xl mb-2">
              No recommendations yet
            </h3>
            <p className="text-white/40 text-sm mb-6 max-w-md mx-auto">
              Click <strong className="text-white">Seed Content</strong> first to populate the catalog,
              then <strong className="text-white">Run Agent</strong> to generate your personalized learning path.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button onClick={seedContent} disabled={seeding}
                className="flex items-center gap-2 px-4 py-2.5 bg-surface-600 hover:bg-surface-500 text-white text-sm font-display font-600 rounded-xl transition-colors">
                <Database size={16} />
                {seeding ? 'Seeding...' : '1. Seed Content'}
              </button>
              <button onClick={runAgent} disabled={generating}
                className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white text-sm font-display font-600 rounded-xl transition-colors">
                <Sparkles size={16} />
                2. Run Agent
              </button>
            </div>
          </div>
        )}

        {/* ── Recommendations list ── */}
        {recommendations.length > 0 && !generating && (
          <>
            {/* Filters */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="font-display font-700 text-white text-lg">
                  {filtered.length} Recommended for You
                </h2>
                <p className="text-white/30 text-xs mt-0.5">Sorted by agent score · Dismiss to hide</p>
              </div>
              <button
                onClick={() => setShowFilters(v => !v)}
                className="flex items-center gap-1.5 px-3 py-2 text-white/40 hover:text-white/70 hover:bg-surface-700 rounded-xl transition-colors text-sm font-display"
              >
                <Filter size={14} />
                Filter
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
                        className={`px-3 py-1.5 rounded-lg text-xs font-display font-600 capitalize border transition-all ${typeFilter === t
                          ? 'border-purple-500/60 bg-purple-600/10 text-purple-300'
                          : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
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
                        className={`px-3 py-1.5 rounded-lg text-xs font-display font-600 capitalize border transition-all ${diffFilter === d
                          ? 'border-purple-500/60 bg-purple-600/10 text-purple-300'
                          : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
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
                filtered.map((rec) => (
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
              <button onClick={runAgent} disabled={generating}
                className="flex items-center gap-2 px-6 py-3 bg-surface-700 hover:bg-surface-600 border border-white/10 text-white/60 hover:text-white text-sm font-display font-600 rounded-xl transition-all mx-auto">
                <RefreshCw size={16} />
                Regenerate Recommendations
              </button>
              <p className="text-white/20 text-xs mt-2">Agent will re-run CF + CBF + Claude reasoning</p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}