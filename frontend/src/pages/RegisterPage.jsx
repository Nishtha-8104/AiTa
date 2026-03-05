import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, User, Building, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import toast from 'react-hot-toast'

const ROLES = [
  { value: 'student', label: 'Student', desc: 'I want to learn programming' },
  { value: 'instructor', label: 'Instructor', desc: 'I teach programming courses' },
  { value: 'ta', label: 'Teaching Assistant', desc: 'I assist in programming courses' },
]

const LANGUAGES = ['Python', 'Java', 'JavaScript', 'C++', 'C', 'Go', 'Rust', 'TypeScript']
const GOALS = ['Web Development', 'Machine Learning', 'Data Science', 'Mobile Apps', 'Competitive Programming', 'System Design']

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(1)  // 2-step form
  const [form, setForm] = useState({
    email: '', username: '', password: '', full_name: '',
    role: 'student', institution: '',
    preferred_languages: [], learning_goals: [],
    skill_level: 'beginner',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const toggleArray = (field, value) => {
    setForm(f => ({
      ...f,
      [field]: f[field].includes(value)
        ? f[field].filter(v => v !== value)
        : [...f[field], value]
    }))
  }

  const validateStep1 = () => {
    const e = {}
    if (!form.email) e.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = 'Enter a valid email'
    if (!form.username) e.username = 'Username is required'
    else if (form.username.length < 3) e.username = 'Min 3 characters'
    else if (!/^[a-zA-Z0-9_]+$/.test(form.username)) e.username = 'Only letters, numbers, underscores'
    if (!form.password) e.password = 'Password is required'
    else if (form.password.length < 8) e.password = 'Min 8 characters'
    else if (!/[A-Z]/.test(form.password)) e.password = 'Need at least one uppercase letter'
    else if (!/\d/.test(form.password)) e.password = 'Need at least one digit'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleNext = () => {
    if (validateStep1()) setStep(2)
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      await register(form)
      toast.success('Account created! Please sign in. 🎉')
      navigate('/login')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed.'
      toast.error(msg)
      setErrors({ general: msg })
      setStep(1)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="fixed inset-0 opacity-[0.03]"
        style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />

      <div className="w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
              <Sparkles size={20} className="text-white" />
            </div>
            <span className="font-display font-800 text-2xl text-white">ai<span className="text-brand-400">TA</span></span>
          </div>
          <h1 className="font-display font-700 text-3xl text-white">Create account</h1>
          <p className="text-white/40 text-sm mt-2">Join thousands of learners on aiTA</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-6 px-2">
          {[1, 2].map(s => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-display font-700 transition-all ${step >= s ? 'bg-brand-600 text-white' : 'bg-surface-600 text-white/30'}`}>
                {step > s ? <CheckCircle2 size={14} /> : s}
              </div>
              <span className={`text-xs font-display ${step >= s ? 'text-white/60' : 'text-white/20'}`}>
                {s === 1 ? 'Credentials' : 'Profile'}
              </span>
              {s < 2 && <div className={`h-px flex-1 ${step > s ? 'bg-brand-600' : 'bg-surface-600'}`} />}
            </div>
          ))}
        </div>

        <div className="glass-card p-8">
          {errors.general && (
            <div className="mb-5 flex items-center gap-2.5 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm">
              <AlertCircle size={16} className="shrink-0" />
              {errors.general}
            </div>
          )}

          {/* ── Step 1: Credentials ── */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <label className="label">Full Name</label>
                <div className="relative">
                  <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="text" value={form.full_name}
                    onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                    placeholder="Your full name" className="input-field pl-11" />
                </div>
              </div>

              <div>
                <label className="label">Email Address <span className="text-red-400">*</span></label>
                <div className="relative">
                  <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="email" value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    placeholder="you@example.com"
                    className={`input-field pl-11 ${errors.email ? 'border-red-500/50' : ''}`} />
                </div>
                {errors.email && <p className="error-text"><AlertCircle size={12} />{errors.email}</p>}
              </div>

              <div>
                <label className="label">Username <span className="text-red-400">*</span></label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 font-mono text-sm">@</span>
                  <input type="text" value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    placeholder="your_username"
                    className={`input-field pl-10 ${errors.username ? 'border-red-500/50' : ''}`} />
                </div>
                {errors.username && <p className="error-text"><AlertCircle size={12} />{errors.username}</p>}
              </div>

              <div>
                <label className="label">Password <span className="text-red-400">*</span></label>
                <div className="relative">
                  <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type={showPassword ? 'text' : 'password'} value={form.password}
                    onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    placeholder="Min 8 chars, 1 uppercase, 1 digit"
                    className={`input-field pl-11 pr-12 ${errors.password ? 'border-red-500/50' : ''}`} />
                  <button type="button" onClick={() => setShowPassword(v => !v)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && <p className="error-text"><AlertCircle size={12} />{errors.password}</p>}
              </div>

              <button type="button" onClick={handleNext} className="btn-primary">
                Continue →
              </button>
            </div>
          )}

          {/* ── Step 2: Profile ── */}
          {step === 2 && (
            <div className="space-y-5">
              {/* Role */}
              <div>
                <label className="label">I am a...</label>
                <div className="space-y-2">
                  {ROLES.map(r => (
                    <button key={r.value} type="button"
                      onClick={() => setForm(f => ({ ...f, role: r.value }))}
                      className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left ${form.role === r.value
                        ? 'border-brand-500/60 bg-brand-600/10 text-white'
                        : 'border-white/10 bg-surface-700/30 text-white/50 hover:border-white/20'}`}>
                      <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${form.role === r.value ? 'border-brand-400' : 'border-white/30'}`}>
                        {form.role === r.value && <div className="w-2 h-2 rounded-full bg-brand-400" />}
                      </div>
                      <div>
                        <div className="font-display text-sm font-600">{r.label}</div>
                        <div className="text-xs opacity-60">{r.desc}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Skill level */}
              <div>
                <label className="label">Skill Level</label>
                <div className="grid grid-cols-3 gap-2">
                  {['beginner', 'intermediate', 'advanced'].map(s => (
                    <button key={s} type="button"
                      onClick={() => setForm(f => ({ ...f, skill_level: s }))}
                      className={`py-2 rounded-xl border text-xs font-display font-600 capitalize transition-all ${form.skill_level === s
                        ? 'border-brand-500/60 bg-brand-600/10 text-brand-300'
                        : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* Institution */}
              <div>
                <label className="label">Institution</label>
                <div className="relative">
                  <Building size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="text" value={form.institution}
                    onChange={e => setForm(f => ({ ...f, institution: e.target.value }))}
                    placeholder="Your college or university"
                    className="input-field pl-11" />
                </div>
              </div>

              {/* Languages */}
              <div>
                <label className="label">Languages you know</label>
                <div className="flex flex-wrap gap-2">
                  {LANGUAGES.map(lang => (
                    <button key={lang} type="button"
                      onClick={() => toggleArray('preferred_languages', lang)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-mono font-500 border transition-all ${form.preferred_languages.includes(lang)
                        ? 'border-brand-500/60 bg-brand-600/10 text-brand-300'
                        : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                      {lang}
                    </button>
                  ))}
                </div>
              </div>

              {/* Goals */}
              <div>
                <label className="label">Learning Goals</label>
                <div className="flex flex-wrap gap-2">
                  {GOALS.map(goal => (
                    <button key={goal} type="button"
                      onClick={() => toggleArray('learning_goals', goal)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-display font-500 border transition-all ${form.learning_goals.includes(goal)
                        ? 'border-brand-500/60 bg-brand-600/10 text-brand-300'
                        : 'border-white/10 bg-surface-700/30 text-white/40 hover:border-white/20'}`}>
                      {goal}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setStep(1)} className="btn-secondary">
                  ← Back
                </button>
                <button type="button" onClick={handleSubmit} disabled={loading} className="btn-primary">
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                      Creating...
                    </span>
                  ) : 'Create Account 🚀'}
                </button>
              </div>
            </div>
          )}

          <p className="text-center text-white/30 text-sm mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-500 transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}