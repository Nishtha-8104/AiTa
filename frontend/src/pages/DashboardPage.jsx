import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles, LogOut, User, BookOpen, Code2,
  Brain, TrendingUp, Clock, Star, ArrowRight,
  MessageSquare, Trophy, Activity, Layers, Zap,
  Target, BarChart2, CheckCircle2, Users, Shield
} from 'lucide-react'
import { feedbackAPI, codeEvalAPI, userAPI } from '../utils/api'
import toast from 'react-hot-toast'
import ThemeToggle from '../components/ui/ThemeToggle'
import { SkeletonStatCard, SkeletonCard } from '../components/ui/Skeleton'
import { Sparkline, RadialProgress, BarChart } from '../components/ui/MiniChart'
import FeedbackModal from '../components/ui/FeedbackModal'

const ROLE_LABELS = {
  student: 'Student', instructor: 'Instructor',
  ta: 'Teaching Assistant', admin: 'Admin',
}

const FEATURES = [
  {
    id: 'profile', route: '/profile', icon: Brain, label: 'Learner Profile',
    desc: 'Your skill level, goals, and learning preferences — the foundation for every personalised experience.',
    color: 'text-violet-400', iconBg: 'bg-violet-600', border: 'border-violet-500/20', glow: 'hover:shadow-violet-500/10', tag: 'Profile',
  },
  {
    id: 'recommend', route: '/recommendations', icon: BookOpen, label: 'Recommendation Agent',
    desc: 'AI-curated content matched to your profile using collaborative filtering and Groq-powered ranking.',
    color: 'text-blue-400', iconBg: 'bg-blue-600', border: 'border-blue-500/20', glow: 'hover:shadow-blue-500/10', tag: 'Agent',
  },
  {
    id: 'learn', route: '/learn', icon: Sparkles, label: 'Content Player Agent',
    desc: 'Interactive AI tutor with 5 modes — walkthrough, Q&A, quiz, code help, and brainstorm.',
    color: 'text-teal-400', iconBg: 'bg-teal-600', border: 'border-teal-500/20', glow: 'hover:shadow-teal-500/10', tag: 'Agent',
  },
  {
    id: 'code', route: '/code-eval', icon: Code2, label: 'Code Evaluation Agent',
    desc: 'Paste a problem statement, write your solution, and get multi-dimensional AI analysis — scores, issues, corrected code.',
    color: 'text-orange-400', iconBg: 'bg-orange-600', border: 'border-orange-500/20', glow: 'hover:shadow-orange-500/10', tag: 'Agent',
  },
  {
    id: 'feedback', route: '/feedback', icon: MessageSquare, label: 'Feedback Agent',
    desc: 'Personalised feedback synthesised from your code evaluations and learning sessions.',
    color: 'text-pink-400', iconBg: 'bg-pink-600', border: 'border-pink-500/20', glow: 'hover:shadow-pink-500/10', tag: 'Agent',
  },
]

function FeatureCard({ feature, onClick, badge }) {
  const Icon = feature.icon
  return (
    <div
      onClick={onClick}
      className={`group relative glass-card p-6 cursor-pointer border ${feature.border} hover:-translate-y-1 hover:shadow-xl ${feature.glow} transition-all duration-200`}
    >
      {badge > 0 && (
        <div className="absolute -top-2 -right-2 min-w-[22px] h-[22px] px-1.5 rounded-full bg-pink-600 flex items-center justify-center z-10">
          <span className="text-white text-xs font-mono font-700">{badge}</span>
        </div>
      )}
      <div className="flex items-start justify-between mb-4">
        <div className={`w-11 h-11 rounded-2xl ${feature.iconBg} flex items-center justify-center shadow-lg`}>
          <Icon size={20} className="text-white" />
        </div>
        <span className={`text-xs font-mono px-2.5 py-1 rounded-full bg-surface-700 ${feature.color}`}>{feature.tag}</span>
      </div>
      <h3 className="font-display font-700 text-base text-white mb-2">{feature.label}</h3>
      <p className="text-white/40 text-sm leading-relaxed font-body">{feature.desc}</p>
      <div className={`flex items-center gap-1.5 mt-4 text-xs font-mono ${feature.color} opacity-0 group-hover:opacity-100 transition-opacity`}>
        Open <ArrowRight size={13} />
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sub, color, trend, loading }) {
  if (loading) return <SkeletonStatCard />
  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-9 h-9 rounded-xl bg-surface-700 flex items-center justify-center ${color}`}>
          <Icon size={17} />
        </div>
        <span className="text-white/40 text-sm font-body">{label}</span>
      </div>
      <div className="flex items-end justify-between">
        <div>
          <div className="font-display font-800 text-2xl text-white">{value}</div>
          {sub && <p className="text-white/25 text-xs mt-1 font-body">{sub}</p>}
        </div>
        {trend && <Sparkline data={trend} color={color.includes('yellow') ? '#f59e0b' : color.includes('teal') ? '#14b8a6' : color.includes('pink') ? '#ec4899' : '#3b82f6'} />}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [feedbackUnread, setFeedbackUnread] = useState(0)
  const [codeStats, setCodeStats]           = useState(null)
  const [statsLoading, setStatsLoading]     = useState(true)
  const [showFeedback, setShowFeedback]     = useState(false)
  const [peerData, setPeerData]             = useState(null)
  const [peerLoading, setPeerLoading]       = useState(true)

  useEffect(() => {
    Promise.all([
      feedbackAPI.unreadCount().catch(() => ({ data: { unread: 0 } })),
      codeEvalAPI.getStats().catch(() => ({ data: null })),
      userAPI.getPeerComparison().catch(() => ({ data: null })),
    ]).then(([fb, stats, peer]) => {
      setFeedbackUnread(fb.data.unread ?? 0)
      setCodeStats(stats.data)
      setPeerData(peer.data)
    }).finally(() => {
      setStatsLoading(false)
      setPeerLoading(false)
    })
  }, [])

  // Show feedback prompt after 30s if user has sessions
  useEffect(() => {
    const timer = setTimeout(() => {
      if ((user?.total_sessions ?? 0) > 0) setShowFeedback(true)
    }, 30000)
    return () => clearTimeout(timer)
  }, [user])

  const handleLogout = async () => {
    await logout()
    toast.success('Logged out')
    navigate('/login')
  }

  const completeness = user?.learning_profile?.profile_completeness ?? 0
  const skillLevel   = user?.skill_level ?? 'beginner'
  const skillColor   = { beginner: 'text-green-400', intermediate: 'text-yellow-400', advanced: 'text-red-400' }[skillLevel] || 'text-white/50'

  // Mock trend data (replace with real API data when available)
  const scoreTrend  = codeStats?.score_history  || [60, 65, 58, 72, 68, 75, 80]
  const sessionTrend = [1, 2, 1, 3, 2, 4, 3]

  // Topic performance for bar chart
  const topicPerf = codeStats?.topic_scores
    ? Object.entries(codeStats.topic_scores).slice(0, 5).map(([label, value]) => ({ label, value: Math.round(value) }))
    : [
        { label: 'Arrays',  value: 78 },
        { label: 'Trees',   value: 62 },
        { label: 'DP',      value: 45 },
        { label: 'Graphs',  value: 55 },
        { label: 'Sorting', value: 82 },
      ]

  const overallScore = codeStats?.avg_score ?? Math.round(topicPerf.reduce((a, b) => a + b.value, 0) / topicPerf.length)

  return (
    <div className="min-h-screen bg-surface-950">

      {/* ── Navbar ── */}
      <nav className="border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center">
              <Sparkles size={15} className="text-white" />
            </div>
            <span className="font-display font-800 text-xl text-white">
              ai<span className="text-brand-400">TA</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <button
              onClick={() => navigate('/profile')}
              className="flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-surface-700/60 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
                <User size={15} className="text-brand-400" />
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-white/80 text-sm font-body leading-none">{user?.username}</p>
                <p className={`text-xs font-mono leading-none mt-0.5 ${skillColor}`}>{skillLevel}</p>
              </div>
            </button>
            <button
              onClick={handleLogout}
              className="p-2.5 rounded-xl text-white/30 hover:text-white/60 hover:bg-surface-700/60 transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10">

        {/* ── Hero ── */}
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-3">
            <span className="flex items-center gap-1.5 text-xs font-mono text-brand-400 bg-brand-600/10 border border-brand-500/20 px-2.5 py-1 rounded-full">
              <Star size={11} /> {ROLE_LABELS[user?.role] ?? 'Student'}
            </span>
          </div>
          <h1 className="font-display font-800 text-4xl text-white mb-2">
            Welcome back, {user?.full_name?.split(' ')[0] || user?.username}
          </h1>
          <p className="text-white/40 font-body text-base max-w-xl">
            Your AI-powered learning workspace. Pick up where you left off or explore something new.
          </p>
        </div>

        {/* ── Profile completeness banner ── */}
        {completeness < 80 && (
          <div className="glass-card p-5 mb-8 border-brand-500/20 flex items-center gap-5">
            <div className="w-10 h-10 rounded-xl bg-brand-600/20 flex items-center justify-center shrink-0">
              <Activity size={18} className="text-brand-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-display font-600 text-white">Complete your profile</span>
                <span className="text-brand-400 text-sm font-mono">{completeness}%</span>
              </div>
              <div className="h-1.5 bg-surface-600 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-700" style={{ width: `${completeness}%` }} />
              </div>
              <p className="text-white/30 text-xs mt-1.5">A complete profile unlocks better AI personalisation across all features.</p>
            </div>
            <button onClick={() => navigate('/profile')} className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-display font-600 rounded-xl transition-colors shrink-0">
              Update
            </button>
          </div>
        )}

        {/* ── Stats row ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard icon={Trophy}       label="Points"   value={user?.points ?? 0}          sub="Keep learning to earn more"  color="text-yellow-400" trend={scoreTrend}   loading={statsLoading} />
          <StatCard icon={Zap}          label="Level"    value={`Level ${user?.level ?? 1}`} sub={skillLevel.charAt(0).toUpperCase() + skillLevel.slice(1)} color="text-brand-400" loading={statsLoading} />
          <StatCard icon={Clock}        label="Sessions" value={user?.total_sessions ?? 0}   sub="Total learning sessions"     color="text-teal-400"  trend={sessionTrend} loading={statsLoading} />
          <StatCard icon={MessageSquare} label="Feedback" value={feedbackUnread > 0 ? feedbackUnread : '—'} sub={feedbackUnread > 0 ? 'Unread reports' : 'All caught up'} color="text-pink-400" loading={statsLoading} />
        </div>


        {/* ── AI Agents ── */}
        {/* <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={14} className="text-brand-400" />
            <p className="text-white/40 text-xs font-mono uppercase tracking-wider">AI Agents</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {FEATURES.filter(f => f.tag === 'Agent').map(feature => (
              <FeatureCard
                key={feature.id}
                feature={feature}
                onClick={() => navigate(feature.route)}
                badge={feature.id === 'feedback' ? feedbackUnread : 0}
              />
            ))}
          </div>
        </div> */}

        {/* ── Suggested next steps ── */}
        <div className="glass-card p-6 mb-8 border-teal-500/15">
          <div className="flex items-center gap-2 mb-4">
            <Target size={15} className="text-teal-400" />
            <p className="text-white/40 text-xs font-mono uppercase tracking-wider">Suggested Next Steps</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {[
              { icon: '📚', label: 'Get recommendations', desc: 'Run the AI agent to discover new content', route: '/recommendations', color: '#3b82f6' },
              { icon: '💻', label: 'Practice a problem', desc: 'Generate a LeetCode-style problem to solve', route: '/code-help', color: '#14b8a6' },
              { icon: '🧑‍💻', label: 'Evaluate your code', desc: 'Paste a problem + solution and get AI feedback', route: '/code-eval', color: '#f97316' },
              { icon: '📊', label: 'Review feedback', desc: 'Check your latest AI-generated feedback report', route: '/feedback', color: '#ec4899' },
            ].map(step => (
              <button
                key={step.label}
                onClick={() => navigate(step.route)}
                style={{ border: `1px solid ${step.color}25` }}
                className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] transition-colors text-left cursor-pointer"
              >
                <span className="text-xl shrink-0">{step.icon}</span>
                <div>
                  <div className="text-white text-sm font-display font-600 mb-0.5">{step.label}</div>
                  <div className="text-white/35 text-xs leading-relaxed">{step.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Peer Comparison ── */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Users size={14} className="text-violet-400" />
            <p className="text-white/40 text-xs font-mono uppercase tracking-wider">Your Standing Among Peers</p>
          </div>

          {peerLoading ? (
            <div className="h-48 glass-card animate-pulse" />
          ) : peerData?.consent_required ? (
            /* ── Consent locked state ── */
            <div className="glass-card p-8 flex flex-col sm:flex-row items-center gap-6 border-violet-500/15">
              <div className="w-16 h-16 rounded-2xl bg-violet-600/15 border border-violet-500/20 flex items-center justify-center shrink-0">
                <Shield size={28} className="text-violet-400" />
              </div>
              <div className="flex-1 text-center sm:text-left">
                <h3 className="font-display font-700 text-white text-lg mb-1">See how you rank against other learners</h3>
                <p className="text-white/40 text-sm leading-relaxed max-w-lg">
                  Enable anonymous data sharing to unlock your percentile rank, score benchmarks,
                  and insights on where you stand. Your name and email are <span className="text-white/60">never</span> shared.
                </p>
                <button
                  onClick={() => navigate('/profile')}
                  className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-display font-600 rounded-xl transition-colors"
                >
                  <Shield size={13} /> Enable in Privacy Settings
                </button>
              </div>
            </div>
          ) : !peerData || peerData.total_peers === 0 ? (
            <div className="glass-card p-8 text-center border-violet-500/10">
              <p className="text-white/30 text-sm">No peers yet — you're the first learner with data sharing on!</p>
            </div>
          ) : (
            /* ── Full comparison card ── */
            <div className="glass-card overflow-hidden border-violet-500/15">

              {/* Top banner — rank + percentile */}
              <div className="bg-gradient-to-r from-violet-600/15 via-violet-500/8 to-transparent px-6 py-5 flex flex-col sm:flex-row items-center gap-6 border-b border-white/[0.06]">

                {/* Percentile ring */}
                <div className="relative shrink-0 w-24 h-24">
                  <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                    <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
                    <circle cx="50" cy="50" r="40" fill="none" stroke="#7c3aed" strokeWidth="10"
                      strokeDasharray={`${2 * Math.PI * 40}`}
                      strokeDashoffset={`${2 * Math.PI * 40 * (1 - (peerData.your_rank?.top_percentile ?? 0) / 100)}`}
                      strokeLinecap="round"
                      style={{ transition: 'stroke-dashoffset 1s ease' }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-display font-800 text-xl text-white leading-none">
                      {peerData.your_rank?.top_percentile ?? 0}%
                    </span>
                    <span className="text-white/30 text-xs font-mono">top</span>
                  </div>
                </div>

                {/* Rank text */}
                <div>
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="font-display font-800 text-3xl text-white">
                      #{peerData.your_rank?.points_rank}
                    </span>
                    <span className="text-white/30 text-sm font-body">
                      out of {peerData.your_rank?.out_of} learners
                    </span>
                  </div>
                  <p className="text-violet-300 text-sm font-body leading-relaxed max-w-sm">
                    {peerData.your_rank?.top_percentile >= 75
                      ? `You're in the top ${100 - peerData.your_rank.top_percentile}% — outstanding performance. Keep pushing.`
                      : peerData.your_rank?.top_percentile >= 50
                      ? `You're above average. A few more sessions and you'll break into the top 25%.`
                      : `You're building momentum. Consistent practice will move you up fast.`}
                  </p>
                </div>
              </div>

              {/* Metric insights */}
              <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-white/[0.06]">
                {(() => {
                  const metrics = [
                    {
                      icon: '🎯',
                      label: 'Code Score',
                      yours: peerData.your_stats?.avg_code_score ?? 0,
                      avg:   peerData.platform_averages?.avg_code_score ?? 0,
                      unit:  '/100',
                      insight: (y, a) => y >= a
                        ? `Your avg score is ${(y - a).toFixed(1)} pts above the platform average.`
                        : `You're ${(a - y).toFixed(1)} pts below average — more evaluations will close this gap.`,
                    },
                    {
                      icon: '⚡',
                      label: 'Learning Sessions',
                      yours: peerData.your_stats?.sessions ?? 0,
                      avg:   peerData.platform_averages?.sessions ?? 0,
                      unit:  '',
                      insight: (y, a) => y >= a
                        ? `You've done ${y - Math.round(a)} more sessions than the average learner.`
                        : `Average learner has ${Math.round(a) - y} more sessions — consistency is key.`,
                    },
                    {
                      icon: '📊',
                      label: 'Accuracy Rate',
                      yours: peerData.your_stats?.accuracy_pct ?? 0,
                      avg:   peerData.platform_averages?.accuracy_pct ?? 0,
                      unit:  '%',
                      insight: (y, a) => y >= a
                        ? `Your accuracy is ${(y - a).toFixed(1)}% higher than peers at your level.`
                        : `Focus on weak areas to bring your accuracy up by ${(a - y).toFixed(1)}%.`,
                    },
                  ]
                  return metrics.map(m => {
                    const better = m.yours >= m.avg
                    const pct    = m.avg > 0 ? Math.min(Math.round((m.yours / m.avg) * 100), 200) : 0
                    return (
                      <div key={m.label} className="p-5">
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-lg">{m.icon}</span>
                          <span className="text-white/40 text-xs font-mono uppercase tracking-wider">{m.label}</span>
                        </div>
                        <div className="flex items-baseline gap-1.5 mb-1">
                          <span className={`font-display font-800 text-2xl ${better ? 'text-white' : 'text-white/70'}`}>
                            {m.yours}{m.unit}
                          </span>
                          <span className={`text-xs font-mono px-1.5 py-0.5 rounded-full ${
                            better
                              ? 'bg-green-500/15 text-green-400'
                              : 'bg-yellow-500/15 text-yellow-400'
                          }`}>
                            {better ? `+${(m.yours - m.avg).toFixed(1)}` : `${(m.yours - m.avg).toFixed(1)}`} vs avg
                          </span>
                        </div>
                        <p className="text-white/30 text-xs leading-relaxed mb-3">
                          {m.insight(m.yours, m.avg)}
                        </p>
                        {/* You vs avg mini bar */}
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2">
                            <span className="text-white/30 text-xs w-6">You</span>
                            <div className="flex-1 h-1.5 bg-surface-600 rounded-full overflow-hidden">
                              <div className="h-full rounded-full bg-violet-500 transition-all duration-700"
                                style={{ width: `${Math.min(pct, 100)}%` }} />
                            </div>
                            <span className="text-white/50 text-xs font-mono w-10 text-right">{m.yours}{m.unit}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-white/20 text-xs w-6">Avg</span>
                            <div className="flex-1 h-1.5 bg-surface-600 rounded-full overflow-hidden">
                              <div className="h-full rounded-full bg-white/20 transition-all duration-700" style={{ width: '100%' }} />
                            </div>
                            <span className="text-white/30 text-xs font-mono w-10 text-right">{m.avg}{m.unit}</span>
                          </div>
                        </div>
                      </div>
                    )
                  })
                })()}
              </div>

              {/* Skill distribution footer */}
              {peerData.skill_distribution && (
                <div className="px-6 py-4 border-t border-white/[0.06] bg-surface-800/30">
                  <div className="flex items-center gap-4">
                    <span className="text-white/25 text-xs font-mono shrink-0">Skill mix</span>
                    <div className="flex-1 flex h-2 rounded-full overflow-hidden gap-px">
                      {Object.entries(peerData.skill_distribution).map(([level, count]) => {
                        const pct = Math.round((count / peerData.total_peers) * 100)
                        const bg  = { beginner: 'bg-green-500', intermediate: 'bg-yellow-500', advanced: 'bg-red-500' }[level] || 'bg-brand-500'
                        const isYou = user?.skill_level === level
                        return (
                          <div key={level} className={`${bg} ${isYou ? 'ring-1 ring-white/40' : ''} transition-all`}
                            style={{ width: `${pct}%` }} title={`${level}: ${pct}%${isYou ? ' (you)' : ''}`} />
                        )
                      })}
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {Object.entries(peerData.skill_distribution).map(([level, count]) => {
                        const pct   = Math.round((count / peerData.total_peers) * 100)
                        const color = { beginner: 'text-green-400', intermediate: 'text-yellow-400', advanced: 'text-red-400' }[level] || 'text-brand-400'
                        const isYou = user?.skill_level === level
                        return (
                          <span key={level} className={`text-xs font-mono capitalize ${color} ${isYou ? 'font-700' : ''}`}>
                            {level} {pct}%{isYou ? ' ←' : ''}
                          </span>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Quick info ── */}
        {(user?.preferred_languages?.length > 0 || user?.learning_goals?.length > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {user.preferred_languages?.length > 0 && (
              <div className="glass-card p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Layers size={15} className="text-white/30" />
                  <h3 className="text-white/40 text-xs font-mono uppercase tracking-wider">Languages</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {user.preferred_languages.map(l => (
                    <span key={l} className="px-3 py-1 bg-surface-700 rounded-lg text-xs font-mono text-white/60">{l}</span>
                  ))}
                </div>
              </div>
            )}
            {user.learning_goals?.length > 0 && (
              <div className="glass-card p-5">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp size={15} className="text-white/30" />
                  <h3 className="text-white/40 text-xs font-mono uppercase tracking-wider">Learning Goals</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {user.learning_goals.map(g => (
                    <span key={g} className="px-3 py-1 bg-brand-600/10 border border-brand-500/20 rounded-lg text-xs font-display text-brand-300">{g}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Feedback modal (auto-prompt after 30s) ── */}
      <FeedbackModal
        open={showFeedback}
        onClose={() => setShowFeedback(false)}
        context="Learning Session"
        onSubmit={async ({ rating, comment }) => {
          // Fire-and-forget — don't block UI
          try { await feedbackAPI.autoGenerate() } catch { /* silent */ }
          toast.success('Thanks for your feedback!')
        }}
      />
    </div>
  )
}
