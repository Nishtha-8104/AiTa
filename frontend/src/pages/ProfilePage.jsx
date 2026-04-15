import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, User, Building, MapPin, Code2, Target, Sparkles, Lock } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { userAPI } from '../utils/api'
import toast from 'react-hot-toast'

const LANGUAGES = ['Python', 'Java', 'JavaScript', 'C++', 'C', 'Go', 'Rust', 'TypeScript', 'Swift', 'Kotlin']
const GOALS = ['Web Development', 'Machine Learning', 'Data Science', 'Mobile Apps', 'Competitive Programming', 'System Design', 'DevOps', 'Cybersecurity']
const INTERESTS = ['Algorithms', 'AI/ML', 'Databases', 'Networking', 'Frontend', 'Backend', 'Open Source', 'Research']
const TOPICS = [
  'variables', 'loops', 'functions', 'recursion', 'OOP', 'data structures',
  'algorithms', 'sorting', 'binary search', 'graphs', 'dynamic programming',
  'trees', 'linked lists', 'stacks', 'queues', 'hashing', 'SQL', 'REST APIs',
  'React', 'Node.js', 'machine learning', 'neural networks', 'pandas', 'numpy',
  'system design', 'design patterns', 'concurrency', 'testing', 'git',
]

export default function ProfilePage() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    bio: user?.bio || '',
    institution: user?.institution || '',
    year_of_study: user?.year_of_study || '',
    city: user?.city || '',
    state: user?.state || '',
    skill_level: user?.skill_level || 'beginner',
    years_of_experience: user?.years_of_experience || 0,
    preferred_languages: user?.preferred_languages || [],
    learning_goals: user?.learning_goals || [],
    interests: user?.interests || [],
    interested_topics: user?.interested_topics || [],
  })

  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '' })
  const [saving, setSaving] = useState(false)
  const [savingPw, setSavingPw] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')

  const toggleArray = (field, value) => {
    setForm(f => ({
      ...f,
      [field]: f[field].includes(value) ? f[field].filter(v => v !== value) : [...f[field], value]
    }))
  }

  const handleSaveProfile = async () => {
    setSaving(true)
    try {
      const payload = {
        ...form,
        // coerce year_of_study: empty string → null, otherwise parse as int
        year_of_study: form.year_of_study === '' || form.year_of_study === null
          ? null
          : parseInt(form.year_of_study, 10) || null,
        years_of_experience: parseFloat(form.years_of_experience) || 0,
      }
      const { data } = await userAPI.updateProfile(payload)
      updateUser(data)
      toast.success('Profile updated! ✅')
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : detail || 'Update failed.'
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async () => {
    if (!pwForm.current_password || !pwForm.new_password) {
      toast.error('Fill in both password fields.')
      return
    }
    setSavingPw(true)
    try {
      await userAPI.changePassword(pwForm)
      toast.success('Password changed successfully! 🔒')
      setPwForm({ current_password: '', new_password: '' })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Password change failed.')
    } finally {
      setSavingPw(false)
    }
  }

  const TABS = [
    { id: 'profile', label: 'Profile Info', icon: User },
    { id: 'learning', label: 'Learning', icon: Target },
    { id: 'security', label: 'Security', icon: Lock },
  ]

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center gap-4">
          <button onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 text-white/40 hover:text-white/70 transition-colors">
            <ArrowLeft size={18} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <Sparkles size={14} className="text-white" />
            </div>
            <span className="font-display font-700 text-lg text-white">ai<span className="text-brand-400">TA</span></span>
          </div>
          <span className="text-white/20">/</span>
          <span className="font-display font-600 text-white/60">Edit Profile</span>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-2xl bg-brand-600/20 border border-brand-500/20 flex items-center justify-center">
            <User size={28} className="text-brand-400" />
          </div>
          <div>
            <h1 className="font-display font-700 text-2xl text-white">{user?.username}</h1>
            <p className="text-white/40 text-sm">{user?.email} · <span className="capitalize">{user?.role}</span></p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-surface-800 rounded-xl p-1 mb-6">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 flex-1 py-2.5 px-4 rounded-lg text-sm font-display font-600 transition-all ${activeTab === tab.id ? 'bg-surface-600 text-white' : 'text-white/40 hover:text-white/60'}`}>
              <tab.icon size={15} />
              <span className="hidden sm:block">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* ── Profile Tab ── */}
        {activeTab === 'profile' && (
          <div className="glass-card p-6 space-y-5 animate-fade-in">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className="label">Full Name</label>
                <div className="relative">
                  <User size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="text" value={form.full_name}
                    onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                    placeholder="Your full name" className="input-field pl-10" />
                </div>
              </div>
              <div>
                <label className="label">Institution</label>
                <div className="relative">
                  <Building size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="text" value={form.institution}
                    onChange={e => setForm(f => ({ ...f, institution: e.target.value }))}
                    placeholder="College / University" className="input-field pl-10" />
                </div>
              </div>
              <div>
                <label className="label">City</label>
                <div className="relative">
                  <MapPin size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="text" value={form.city}
                    onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                    placeholder="Your city" className="input-field pl-10" />
                </div>
              </div>
              <div>
                <label className="label">State</label>
                <input type="text" value={form.state}
                  onChange={e => setForm(f => ({ ...f, state: e.target.value }))}
                  placeholder="Your state" className="input-field" />
              </div>
              <div>
                <label className="label">Year of Study</label>
                <input type="number" min="1" max="10" value={form.year_of_study}
                  onChange={e => setForm(f => ({ ...f, year_of_study: e.target.value }))}
                  placeholder="e.g. 2" className="input-field" />
              </div>
              <div>
                <label className="label">Years of Experience</label>
                <input type="number" min="0" max="50" step="0.5" value={form.years_of_experience}
                  onChange={e => setForm(f => ({ ...f, years_of_experience: parseFloat(e.target.value) || 0 }))}
                  placeholder="0" className="input-field" />
              </div>
            </div>
            <div>
              <label className="label">Bio</label>
              <textarea value={form.bio}
                onChange={e => setForm(f => ({ ...f, bio: e.target.value }))}
                placeholder="Tell us about yourself..."
                rows={3}
                className="input-field resize-none" />
            </div>
            <button onClick={handleSaveProfile} disabled={saving} className="btn-primary">
              {saving ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  Saving...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2"><Save size={16} /> Save Changes</span>
              )}
            </button>
          </div>
        )}

        {/* ── Learning Tab ── */}
        {activeTab === 'learning' && (
          <div className="glass-card p-6 space-y-6 animate-fade-in">
            <div>
              <label className="label">Skill Level</label>
              <div className="grid grid-cols-3 gap-3">
                {['beginner', 'intermediate', 'advanced'].map(s => (
                  <button key={s} type="button"
                    onClick={() => setForm(f => ({ ...f, skill_level: s }))}
                    className={`py-3 rounded-xl border text-sm font-display font-600 capitalize transition-all ${form.skill_level === s ? 'border-brand-500/60 bg-brand-600/10 text-brand-300' : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label"><Code2 size={12} className="inline mr-1" />Programming Languages</label>
              <div className="flex flex-wrap gap-2">
                {LANGUAGES.map(lang => (
                  <button key={lang} type="button" onClick={() => toggleArray('preferred_languages', lang)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-500 border transition-all ${form.preferred_languages.includes(lang) ? 'border-brand-500/60 bg-brand-600/10 text-brand-300' : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                    {lang}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label"><Sparkles size={12} className="inline mr-1" />Topics <span className="text-white/30 font-normal">(used by recommendation agent)</span></label>
              <div className="flex flex-wrap gap-2">
                {TOPICS.map(topic => (
                  <button key={topic} type="button" onClick={() => toggleArray('interested_topics', topic)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-500 border transition-all ${form.interested_topics.includes(topic) ? 'border-teal-500/60 bg-teal-600/10 text-teal-300' : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                    {topic}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label"><Target size={12} className="inline mr-1" />Learning Goals</label>
              <div className="flex flex-wrap gap-2">
                {GOALS.map(goal => (
                  <button key={goal} type="button" onClick={() => toggleArray('learning_goals', goal)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-display font-500 border transition-all ${form.learning_goals.includes(goal) ? 'border-brand-500/60 bg-brand-600/10 text-brand-300' : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                    {goal}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Interests</label>
              <div className="flex flex-wrap gap-2">
                {INTERESTS.map(i => (
                  <button key={i} type="button" onClick={() => toggleArray('interests', i)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-display font-500 border transition-all ${form.interests.includes(i) ? 'border-purple-500/60 bg-purple-600/10 text-purple-300' : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                    {i}
                  </button>
                ))}
              </div>
            </div>
            <button onClick={handleSaveProfile} disabled={saving} className="btn-primary">
              {saving ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Saving...</span>
                : <span className="flex items-center justify-center gap-2"><Save size={16} /> Save Learning Profile</span>}
            </button>
          </div>
        )}

        {/* ── Security Tab ── */}
        {activeTab === 'security' && (
          <div className="glass-card p-6 space-y-5 animate-fade-in">
            <div>
              <h3 className="font-display font-600 text-white mb-1">Change Password</h3>
              <p className="text-white/30 text-sm mb-5">Make sure it's at least 8 characters with an uppercase and a digit.</p>
              <div className="space-y-4">
                <div>
                  <label className="label">Current Password</label>
                  <input type="password" value={pwForm.current_password}
                    onChange={e => setPwForm(f => ({ ...f, current_password: e.target.value }))}
                    placeholder="••••••••" className="input-field" />
                </div>
                <div>
                  <label className="label">New Password</label>
                  <input type="password" value={pwForm.new_password}
                    onChange={e => setPwForm(f => ({ ...f, new_password: e.target.value }))}
                    placeholder="••••••••" className="input-field" />
                </div>
                <button onClick={handleChangePassword} disabled={savingPw} className="btn-primary">
                  {savingPw ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Updating...</span>
                    : <span className="flex items-center justify-center gap-2"><Lock size={16} /> Update Password</span>}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}