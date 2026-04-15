import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { userAPI } from '../utils/api'
import toast from 'react-hot-toast'
import {
  Code2, Brain, Zap, ChevronRight, ChevronLeft,
  Check, Sparkles, Globe
} from 'lucide-react'

// ── Data ──────────────────────────────────────────────────────────────────────

const LANGUAGES = [
  { id: 'python',     label: 'Python',     icon: '🐍', color: '#3b82f6' },
  { id: 'javascript', label: 'JavaScript', icon: '⚡', color: '#f59e0b' },
  { id: 'java',       label: 'Java',       icon: '☕', color: '#ef4444' },
  { id: 'c++',        label: 'C++',        icon: '⚙️', color: '#8b5cf6' },
  { id: 'go',         label: 'Go',         icon: '🔵', color: '#06b6d4' },
  { id: 'rust',       label: 'Rust',       icon: '🦀', color: '#f97316' },
  { id: 'typescript', label: 'TypeScript', icon: '📘', color: '#2563eb' },
  { id: 'c',          label: 'C',          icon: '🔧', color: '#64748b' },
]

const SKILL_LEVELS = [
  {
    id: 'beginner',
    label: 'Beginner',
    desc: 'Just starting out — learning syntax and basic concepts',
    icon: '🌱',
    color: '#10b981',
    bg: 'rgba(16,185,129,0.1)',
    border: 'rgba(16,185,129,0.4)',
  },
  {
    id: 'intermediate',
    label: 'Intermediate',
    desc: 'Comfortable with basics — ready for data structures & algorithms',
    icon: '🔥',
    color: '#f59e0b',
    bg: 'rgba(245,158,11,0.1)',
    border: 'rgba(245,158,11,0.4)',
  },
  {
    id: 'advanced',
    label: 'Advanced',
    desc: 'Strong fundamentals — tackling complex problems and system design',
    icon: '⚡',
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.1)',
    border: 'rgba(239,68,68,0.4)',
  },
]

const DIFFICULTIES = [
  {
    id: 'easy',
    label: 'Easy',
    desc: 'Warm-up problems to build confidence',
    icon: '○',
    color: '#10b981',
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.35)',
  },
  {
    id: 'medium',
    label: 'Medium',
    desc: 'Balanced challenge — the sweet spot for growth',
    icon: '◑',
    color: '#f59e0b',
    bg: 'rgba(245,158,11,0.08)',
    border: 'rgba(245,158,11,0.35)',
  },
  {
    id: 'hard',
    label: 'Hard',
    desc: 'Push your limits with complex, multi-step problems',
    icon: '●',
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.08)',
    border: 'rgba(239,68,68,0.35)',
  },
]

// ── Step indicator ────────────────────────────────────────────────────────────

function Stepper({ current, total }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 40 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 700, transition: 'all 0.3s',
            background: i < current
              ? 'linear-gradient(135deg,#14b8a6,#0891b2)'
              : i === current
                ? 'rgba(20,184,166,0.15)'
                : 'rgba(255,255,255,0.05)',
            border: `2px solid ${i <= current ? '#14b8a6' : 'rgba(255,255,255,0.1)'}`,
            color: i < current ? '#000' : i === current ? '#14b8a6' : 'rgba(255,255,255,0.3)',
            boxShadow: i === current ? '0 0 16px rgba(20,184,166,0.4)' : 'none',
          }}>
            {i < current ? <Check size={14} /> : i + 1}
          </div>
          {i < total - 1 && (
            <div style={{
              width: 60, height: 2, margin: '0 4px',
              background: i < current
                ? 'linear-gradient(90deg,#14b8a6,#0891b2)'
                : 'rgba(255,255,255,0.08)',
              transition: 'background 0.4s',
            }} />
          )}
        </div>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const { user, updateUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)

  const [selections, setSelections] = useState({
    preferred_languages: user?.preferred_languages || [],
    skill_level: user?.skill_level || 'beginner',
    difficulty_preference: 'medium',
  })

  const toggleLang = (id) => {
    setSelections(prev => ({
      ...prev,
      preferred_languages: prev.preferred_languages.includes(id)
        ? prev.preferred_languages.filter(l => l !== id)
        : [...prev.preferred_languages, id],
    }))
  }

  const canNext = () => {
    if (step === 0) return selections.preferred_languages.length > 0
    if (step === 1) return !!selections.skill_level
    if (step === 2) return !!selections.difficulty_preference
    return true
  }

  const handleFinish = async () => {
    setSaving(true)
    try {
      const { data } = await userAPI.updateProfile({
        preferred_languages: selections.preferred_languages,
        skill_level: selections.skill_level,
        // store difficulty preference in learning_goals as a signal
        learning_goals: [`difficulty:${selections.difficulty_preference}`],
        onboarding_complete: true,
      })
      updateUser(data)
      toast.success("You're all set! Let's start learning 🚀")
      navigate('/dashboard')
    } catch {
      toast.error('Failed to save preferences. You can update them in your profile.')
      navigate('/dashboard')
    } finally {
      setSaving(false)
    }
  }

  const STEPS = [
    {
      icon: <Globe size={22} color="#14b8a6" />,
      title: 'Choose your languages',
      subtitle: 'Select the programming languages you work with or want to learn',
    },
    {
      icon: <Brain size={22} color="#8b5cf6" />,
      title: 'What\'s your skill level?',
      subtitle: 'Be honest — the AI adapts to where you are, not where you want to be',
    },
    {
      icon: <Zap size={22} color="#f59e0b" />,
      title: 'Preferred difficulty',
      subtitle: 'This sets the starting point — the AI will adjust as you progress',
    },
  ]

  const current = STEPS[step]

  return (
    <div style={S.page}>
      <div style={S.gridBg} />
      <div style={S.glow1} />
      <div style={S.glow2} />

      <div style={S.wrap}>
        {/* Logo */}
        <div style={S.logoRow}>
          <div style={S.logoIcon}><Sparkles size={18} color="#fff" /></div>
          <span style={S.logoText}>ai<span style={{ color: '#14b8a6' }}>TA</span></span>
        </div>

        {/* Card */}
        <div style={S.card}>
          <Stepper current={step} total={3} />

          {/* Step header */}
          <div style={S.stepHeader}>
            <div style={S.stepIconWrap}>{current.icon}</div>
            <div>
              <h2 style={S.stepTitle}>{current.title}</h2>
              <p style={S.stepSub}>{current.subtitle}</p>
            </div>
          </div>

          {/* ── Step 0: Languages ── */}
          {step === 0 && (
            <div style={S.langGrid}>
              {LANGUAGES.map(lang => {
                const sel = selections.preferred_languages.includes(lang.id)
                return (
                  <button
                    key={lang.id}
                    onClick={() => toggleLang(lang.id)}
                    style={{
                      ...S.langCard,
                      background: sel ? `${lang.color}18` : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${sel ? lang.color : 'rgba(255,255,255,0.08)'}`,
                      boxShadow: sel ? `0 0 20px ${lang.color}25` : 'none',
                    }}
                  >
                    <span style={{ fontSize: 24 }}>{lang.icon}</span>
                    <span style={{
                      fontSize: 13, fontWeight: sel ? 700 : 500,
                      color: sel ? '#fff' : 'rgba(255,255,255,0.55)',
                    }}>{lang.label}</span>
                    {sel && (
                      <div style={{
                        position: 'absolute', top: 8, right: 8,
                        width: 18, height: 18, borderRadius: '50%',
                        background: lang.color,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <Check size={10} color="#000" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* ── Step 1: Skill level ── */}
          {step === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {SKILL_LEVELS.map(level => {
                const sel = selections.skill_level === level.id
                return (
                  <button
                    key={level.id}
                    onClick={() => setSelections(p => ({ ...p, skill_level: level.id }))}
                    style={{
                      ...S.levelCard,
                      background: sel ? level.bg : 'rgba(255,255,255,0.02)',
                      border: `1px solid ${sel ? level.border : 'rgba(255,255,255,0.07)'}`,
                      boxShadow: sel ? `0 0 24px ${level.color}20` : 'none',
                    }}
                  >
                    <span style={{ fontSize: 28 }}>{level.icon}</span>
                    <div style={{ flex: 1, textAlign: 'left' }}>
                      <div style={{ fontSize: 15, fontWeight: 700, color: sel ? '#fff' : 'rgba(255,255,255,0.7)', marginBottom: 3 }}>
                        {level.label}
                      </div>
                      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', lineHeight: 1.4 }}>
                        {level.desc}
                      </div>
                    </div>
                    <div style={{
                      width: 22, height: 22, borderRadius: '50%',
                      border: `2px solid ${sel ? level.color : 'rgba(255,255,255,0.15)'}`,
                      background: sel ? level.color : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.2s',
                    }}>
                      {sel && <Check size={12} color="#000" />}
                    </div>
                  </button>
                )
              })}
            </div>
          )}

          {/* ── Step 2: Difficulty ── */}
          {step === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {DIFFICULTIES.map(diff => {
                const sel = selections.difficulty_preference === diff.id
                return (
                  <button
                    key={diff.id}
                    onClick={() => setSelections(p => ({ ...p, difficulty_preference: diff.id }))}
                    style={{
                      ...S.levelCard,
                      background: sel ? diff.bg : 'rgba(255,255,255,0.02)',
                      border: `1px solid ${sel ? diff.border : 'rgba(255,255,255,0.07)'}`,
                      boxShadow: sel ? `0 0 24px ${diff.color}20` : 'none',
                    }}
                  >
                    <span style={{ fontSize: 28, color: diff.color }}>{diff.icon}</span>
                    <div style={{ flex: 1, textAlign: 'left' }}>
                      <div style={{ fontSize: 15, fontWeight: 700, color: sel ? '#fff' : 'rgba(255,255,255,0.7)', marginBottom: 3 }}>
                        {diff.label}
                      </div>
                      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', lineHeight: 1.4 }}>
                        {diff.desc}
                      </div>
                    </div>
                    <div style={{
                      width: 22, height: 22, borderRadius: '50%',
                      border: `2px solid ${sel ? diff.color : 'rgba(255,255,255,0.15)'}`,
                      background: sel ? diff.color : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.2s',
                    }}>
                      {sel && <Check size={12} color="#000" />}
                    </div>
                  </button>
                )
              })}
            </div>
          )}

          {/* Navigation */}
          <div style={S.navRow}>
            {step > 0 ? (
              <button onClick={() => setStep(s => s - 1)} style={S.btnBack}>
                <ChevronLeft size={16} /> Back
              </button>
            ) : (
              <button onClick={() => navigate('/dashboard')} style={S.btnSkip}>
                Skip for now
              </button>
            )}

            {step < 2 ? (
              <button
                onClick={() => setStep(s => s + 1)}
                disabled={!canNext()}
                style={{ ...S.btnNext, opacity: canNext() ? 1 : 0.4 }}
              >
                Continue <ChevronRight size={16} />
              </button>
            ) : (
              <button
                onClick={handleFinish}
                disabled={saving || !canNext()}
                style={{ ...S.btnNext, opacity: saving || !canNext() ? 0.5 : 1 }}
              >
                {saving ? 'Saving...' : "Let's go! 🚀"}
              </button>
            )}
          </div>
        </div>

        <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.2)', fontSize: 12, marginTop: 16 }}>
          You can change these anytime in your profile settings
        </p>
      </div>
    </div>
  )
}

const S = {
  page: {
    minHeight: '100vh', background: '#050810',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '40px 20px', fontFamily: "'DM Sans','Segoe UI',sans-serif",
    position: 'relative', overflow: 'hidden',
  },
  gridBg: {
    position: 'fixed', inset: 0, pointerEvents: 'none',
    backgroundImage: `linear-gradient(rgba(20,184,166,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(20,184,166,0.03) 1px,transparent 1px)`,
    backgroundSize: '48px 48px',
  },
  glow1: {
    position: 'fixed', top: '-15%', right: '-10%', width: 500, height: 500,
    borderRadius: '50%', pointerEvents: 'none',
    background: 'radial-gradient(circle,rgba(20,184,166,0.1) 0%,transparent 70%)',
  },
  glow2: {
    position: 'fixed', bottom: '-15%', left: '-10%', width: 400, height: 400,
    borderRadius: '50%', pointerEvents: 'none',
    background: 'radial-gradient(circle,rgba(139,92,246,0.08) 0%,transparent 70%)',
  },
  wrap: { width: '100%', maxWidth: 560, position: 'relative', zIndex: 1 },
  logoRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28, justifyContent: 'center' },
  logoIcon: {
    width: 36, height: 36, borderRadius: 10, background: '#14b8a6',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  logoText: { fontSize: 22, fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' },
  card: {
    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 24, padding: '36px 40px', backdropFilter: 'blur(20px)',
  },
  stepHeader: { display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 28 },
  stepIconWrap: {
    width: 44, height: 44, borderRadius: 12, background: 'rgba(255,255,255,0.06)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  stepTitle: { fontSize: 20, fontWeight: 700, color: '#fff', margin: '0 0 4px', letterSpacing: '-0.3px' },
  stepSub: { fontSize: 13, color: 'rgba(255,255,255,0.4)', margin: 0, lineHeight: 1.5 },
  langGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 4,
  },
  langCard: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
    padding: '16px 8px', borderRadius: 14, cursor: 'pointer',
    transition: 'all 0.2s', position: 'relative',
  },
  levelCard: {
    display: 'flex', alignItems: 'center', gap: 16, padding: '18px 20px',
    borderRadius: 14, cursor: 'pointer', transition: 'all 0.2s', width: '100%',
  },
  navRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 32,
  },
  btnBack: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: 'transparent', border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 10, padding: '10px 18px', color: 'rgba(255,255,255,0.5)',
    fontSize: 14, cursor: 'pointer',
  },
  btnSkip: {
    background: 'transparent', border: 'none',
    color: 'rgba(255,255,255,0.3)', fontSize: 13, cursor: 'pointer',
    textDecoration: 'underline',
  },
  btnNext: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: 'linear-gradient(135deg,#14b8a6,#0891b2)',
    border: 'none', borderRadius: 10, padding: '11px 22px',
    color: '#000', fontSize: 14, fontWeight: 700, cursor: 'pointer',
    transition: 'opacity 0.2s',
  },
}
