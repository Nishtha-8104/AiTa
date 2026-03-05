import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles, LogOut, User, BookOpen, Code2, Trophy,
  Brain, TrendingUp, Target, Clock, Star, ChevronRight
} from 'lucide-react'
import toast from 'react-hot-toast'

const SKILL_COLORS = { beginner: 'text-green-400', intermediate: 'text-yellow-400', advanced: 'text-red-400' }
const ROLE_LABELS = { student: 'Student', instructor: 'Instructor', ta: 'Teaching Assistant', admin: 'Admin' }

function StatCard({ icon: Icon, label, value, color = 'text-brand-400' }) {
  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-xl bg-surface-600 flex items-center justify-center ${color}`}>
          <Icon size={18} />
        </div>
        <span className="text-white/40 text-sm font-body">{label}</span>
      </div>
      <div className="font-display font-700 text-2xl text-white">{value}</div>
    </div>
  )
}

function AgentCard({ icon: Icon, title, desc, status, color }) {
  return (
    <div className="glass-card p-5 hover:border-white/15 transition-all cursor-pointer group">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon size={20} />
        </div>
        <span className={`text-xs font-mono px-2 py-1 rounded-lg ${status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-surface-600 text-white/30'}`}>
          {status}
        </span>
      </div>
      <h3 className="font-display font-600 text-white text-sm mb-1">{title}</h3>
      <p className="text-white/40 text-xs font-body leading-relaxed">{desc}</p>
      <div className="flex items-center gap-1 mt-3 text-brand-400 text-xs font-display font-600 opacity-0 group-hover:opacity-100 transition-opacity">
        Open <ChevronRight size={12} />
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    toast.success('Logged out successfully')
    navigate('/login')
  }

  const completeness = user?.learning_profile?.profile_completeness ?? 0

  return (
    <div className="min-h-screen">
      {/* ── Navbar ── */}
      <nav className="border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <Sparkles size={16} className="text-white" />
            </div>
            <span className="font-display font-800 text-xl text-white">ai<span className="text-brand-400">TA</span></span>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/profile')}
              className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-surface-700 transition-colors">
              <div className="w-8 h-8 rounded-full bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
                <User size={16} className="text-brand-400" />
              </div>
              <span className="text-white/70 text-sm font-body hidden sm:block">{user?.username}</span>
            </button>
            <button onClick={handleLogout}
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-white/40 hover:text-white/70 hover:bg-surface-700 transition-colors text-sm">
              <LogOut size={16} />
              <span className="hidden sm:block">Logout</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* ── Welcome ── */}
        <div className="mb-10">
          <div className="flex items-center gap-2 text-brand-400 text-sm font-mono mb-2">
            <Star size={14} /> {ROLE_LABELS[user?.role]}
          </div>
          <h1 className="font-display font-800 text-4xl text-white mb-2">
            Hello, {user?.full_name?.split(' ')[0] || user?.username} 👋
          </h1>
          <p className="text-white/40 font-body">
            {user?.learning_profile?.recommended_next?.length > 0
              ? `You have ${user.learning_profile.recommended_next.length} recommended topics waiting.`
              : "Complete your profile to unlock personalized learning paths."}
          </p>
        </div>

        {/* ── Profile completeness banner ── */}
        {completeness < 100 && (
          <div className="glass-card p-5 mb-8 flex items-center justify-between gap-4 border-brand-500/20">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <span className="font-display font-600 text-sm text-white">Profile Completeness</span>
                <span className="font-mono text-brand-400 text-sm">{completeness}%</span>
              </div>
              <div className="h-1.5 bg-surface-600 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-700"
                  style={{ width: `${completeness}%` }} />
              </div>
              <p className="text-white/30 text-xs mt-2">Complete your profile to help the AI personalize your experience</p>
            </div>
            <button onClick={() => navigate('/profile')}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-display font-600 rounded-xl transition-colors shrink-0">
              Complete Profile
            </button>
          </div>
        )}

        {/* ── Stats ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          <StatCard icon={Trophy} label="Points" value={user?.points ?? 0} color="text-yellow-400" />
          <StatCard icon={TrendingUp} label="Level" value={`Lv. ${user?.level ?? 1}`} color="text-green-400" />
          <StatCard icon={Clock} label="Sessions" value={user?.total_sessions ?? 0} color="text-brand-400" />
          <StatCard icon={Target} label="Skill" value={
            <span className={SKILL_COLORS[user?.skill_level] || 'text-white'}>
              {user?.skill_level?.charAt(0).toUpperCase() + user?.skill_level?.slice(1) || 'Beginner'}
            </span>
          } />
        </div>

        {/* ── AI Agents ── */}
        <div className="mb-6">
          <h2 className="font-display font-700 text-xl text-white mb-1">AI Agents</h2>
          <p className="text-white/30 text-sm">Your personalized learning toolkit</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
          <AgentCard icon={Brain} title="User Profiling Agent" status="active"
            color="bg-brand-600/20 text-brand-400"
            desc="Continuously builds your learning model and tracks your progress across all topics." />
          <AgentCard icon={BookOpen} title="Content Recommendation" status="coming soon"
            color="bg-purple-600/20 text-purple-400"
            desc="Suggests personalized learning paths based on your skill gaps and interests." />
          <AgentCard icon={Code2} title="Code Evaluation Agent" status="coming soon"
            color="bg-green-600/20 text-green-400"
            desc="Reviews your code for correctness, quality, and best practices with detailed analysis." />
        </div>

        {/* ── Quick info ── */}
        {(user?.preferred_languages?.length > 0 || user?.learning_goals?.length > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {user.preferred_languages?.length > 0 && (
              <div className="glass-card p-5">
                <h3 className="font-display font-600 text-sm text-white/50 uppercase tracking-wider mb-3">Languages</h3>
                <div className="flex flex-wrap gap-2">
                  {user.preferred_languages.map(l => (
                    <span key={l} className="px-2.5 py-1 bg-surface-600 rounded-lg text-xs font-mono text-white/70">{l}</span>
                  ))}
                </div>
              </div>
            )}
            {user.learning_goals?.length > 0 && (
              <div className="glass-card p-5">
                <h3 className="font-display font-600 text-sm text-white/50 uppercase tracking-wider mb-3">Learning Goals</h3>
                <div className="flex flex-wrap gap-2">
                  {user.learning_goals.map(g => (
                    <span key={g} className="px-2.5 py-1 bg-brand-600/10 border border-brand-500/20 rounded-lg text-xs font-display text-brand-300">{g}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}