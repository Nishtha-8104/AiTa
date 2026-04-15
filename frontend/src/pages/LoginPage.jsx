import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, Sparkles, AlertCircle, ShieldCheck, RefreshCw } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const { loginStep1, loginStep2 } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()
  const from      = location.state?.from?.pathname || '/dashboard'

  // ── Step 1 state ──────────────────────────────────────────────────────────
  const [form,         setForm]         = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [errors,       setErrors]       = useState({})
  const [loading,      setLoading]      = useState(false)

  // ── Step 2 state ──────────────────────────────────────────────────────────
  const [step,       setStep]       = useState(1)          // 1 = password, 2 = OTP
  const [otpToken,   setOtpToken]   = useState('')
  const [emailHint,  setEmailHint]  = useState('')
  const [otp,        setOtp]        = useState(['', '', '', '', '', ''])
  const [otpError,   setOtpError]   = useState('')
  const [verifying,  setVerifying]  = useState(false)
  const [resending,  setResending]  = useState(false)
  const [countdown,  setCountdown]  = useState(0)          // resend cooldown seconds
  const otpRefs = useRef([])

  // Countdown timer for resend
  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  // ── Step 1: validate + submit ─────────────────────────────────────────────
  const validateStep1 = () => {
    const e = {}
    if (!form.email) e.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = 'Enter a valid email'
    if (!form.password) e.password = 'Password is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleStep1 = async (e) => {
    e.preventDefault()
    if (!validateStep1()) return
    setLoading(true)
    try {
      const data = await loginStep1(form.email, form.password)
      setOtpToken(data.otp_token)
      setEmailHint(data.email_hint)
      setStep(2)
      setCountdown(30)
      toast.success('OTP sent to your email!')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed. Please try again.'
      toast.error(msg)
      setErrors({ general: msg })
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: OTP input handling ────────────────────────────────────────────
  const handleOtpChange = (index, value) => {
    if (!/^\d*$/.test(value)) return          // digits only
    const next = [...otp]
    next[index] = value.slice(-1)             // one digit per box
    setOtp(next)
    setOtpError('')
    if (value && index < 5) otpRefs.current[index + 1]?.focus()
  }

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus()
    }
    if (e.key === 'Enter') handleVerifyOtp()
  }

  const handleOtpPaste = (e) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (pasted.length === 6) {
      setOtp(pasted.split(''))
      otpRefs.current[5]?.focus()
    }
  }

  const handleVerifyOtp = async () => {
    const code = otp.join('')
    if (code.length < 6) { setOtpError('Enter all 6 digits'); return }
    setVerifying(true)
    setOtpError('')
    try {
      const user = await loginStep2(otpToken, code)
      toast.success(`Welcome back, ${user.username}! 👋`)
      navigate(from, { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid OTP. Please try again.'
      setOtpError(msg)
      setOtp(['', '', '', '', '', ''])
      otpRefs.current[0]?.focus()
    } finally {
      setVerifying(false)
    }
  }

  const handleResend = async () => {
    if (countdown > 0) return
    setResending(true)
    try {
      const data = await loginStep1(form.email, form.password)
      setOtpToken(data.otp_token)
      setOtp(['', '', '', '', '', ''])
      setOtpError('')
      setCountdown(30)
      toast.success('New OTP sent!')
      otpRefs.current[0]?.focus()
    } catch {
      toast.error('Failed to resend OTP.')
    } finally {
      setResending(false)
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
          <h1 className="font-display font-700 text-3xl text-white">
            {step === 1 ? 'Welcome back' : 'Verify your identity'}
          </h1>
          <p className="text-white/40 font-body mt-2 text-sm">
            {step === 1
              ? 'Sign in to continue your learning journey'
              : `Enter the 6-digit OTP sent to ${emailHint}`}
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 justify-center mb-6">
          {[1, 2].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-700 transition-all ${
                step === s
                  ? 'bg-brand-600 text-white'
                  : step > s
                  ? 'bg-green-600 text-white'
                  : 'bg-surface-700 text-white/30'
              }`}>
                {step > s ? '✓' : s}
              </div>
              {s < 2 && <div className={`w-10 h-0.5 rounded-full transition-all ${step > 1 ? 'bg-green-600' : 'bg-surface-700'}`} />}
            </div>
          ))}
        </div>

        <div className="glass-card p-8">

          {/* ── STEP 1: Email + Password ── */}
          {step === 1 && (
            <>
              {errors.general && (
                <div className="mb-5 flex items-center gap-2.5 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm">
                  <AlertCircle size={16} className="shrink-0" />
                  {errors.general}
                </div>
              )}
              <form onSubmit={handleStep1} className="space-y-5">
                <div>
                  <label className="label">Email Address</label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                    <input
                      type="email"
                      value={form.email}
                      onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                      placeholder="you@example.com"
                      className={`input-field pl-11 ${errors.email ? 'border-red-500/50' : ''}`}
                      autoComplete="email"
                    />
                  </div>
                  {errors.email && <p className="error-text"><AlertCircle size={12} />{errors.email}</p>}
                </div>

                <div>
                  <label className="label">Password</label>
                  <div className="relative">
                    <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      placeholder="••••••••"
                      className={`input-field pl-11 pr-12 ${errors.password ? 'border-red-500/50' : ''}`}
                      autoComplete="current-password"
                    />
                    <button type="button" onClick={() => setShowPassword(v => !v)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password && <p className="error-text"><AlertCircle size={12} />{errors.password}</p>}
                </div>

                <button type="submit" disabled={loading} className="btn-primary mt-2">
                  {loading
                    ? <span className="flex items-center justify-center gap-2">
                        <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        Sending OTP…
                      </span>
                    : 'Continue →'}
                </button>
              </form>

              <p className="text-center text-white/30 text-sm mt-6">
                Don't have an account?{' '}
                <Link to="/register" className="text-brand-400 hover:text-brand-300 font-500 transition-colors">
                  Create one
                </Link>
              </p>
            </>
          )}

          {/* ── STEP 2: OTP Input ── */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 p-4 bg-brand-600/8 border border-brand-500/20 rounded-xl">
                <ShieldCheck size={20} className="text-brand-400 shrink-0" />
                <p className="text-white/60 text-sm">
                  A 6-digit OTP was sent to <span className="text-white font-600">{emailHint}</span>.
                  It expires in 10 minutes.
                </p>
              </div>

              {/* 6-box OTP input */}
              <div>
                <label className="label text-center block mb-3">Enter OTP</label>
                <div className="flex gap-2 justify-center" onPaste={handleOtpPaste}>
                  {otp.map((digit, i) => (
                    <input
                      key={i}
                      ref={el => otpRefs.current[i] = el}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={e => handleOtpChange(i, e.target.value)}
                      onKeyDown={e => handleOtpKeyDown(i, e)}
                      className={`w-12 h-14 text-center text-xl font-mono font-700 rounded-xl border bg-surface-700/60 text-white focus:outline-none transition-all ${
                        otpError
                          ? 'border-red-500/60 bg-red-500/5'
                          : digit
                          ? 'border-brand-500/60 bg-brand-600/10'
                          : 'border-white/10 focus:border-brand-500/50'
                      }`}
                    />
                  ))}
                </div>
                {otpError && (
                  <p className="flex items-center justify-center gap-1.5 text-red-400 text-xs mt-3">
                    <AlertCircle size={12} /> {otpError}
                  </p>
                )}
              </div>

              <button
                onClick={handleVerifyOtp}
                disabled={verifying || otp.join('').length < 6}
                className="btn-primary"
              >
                {verifying
                  ? <span className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                      Verifying…
                    </span>
                  : <span className="flex items-center justify-center gap-2">
                      <ShieldCheck size={16} /> Verify & Sign In
                    </span>}
              </button>

              {/* Resend + back */}
              <div className="flex items-center justify-between text-sm">
                <button
                  onClick={() => { setStep(1); setOtp(['','','','','','']); setOtpError('') }}
                  className="text-white/30 hover:text-white/60 transition-colors"
                >
                  ← Back
                </button>
                <button
                  onClick={handleResend}
                  disabled={countdown > 0 || resending}
                  className="flex items-center gap-1.5 text-brand-400 hover:text-brand-300 disabled:text-white/20 disabled:cursor-not-allowed transition-colors"
                >
                  <RefreshCw size={13} className={resending ? 'animate-spin' : ''} />
                  {countdown > 0 ? `Resend in ${countdown}s` : 'Resend OTP'}
                </button>
              </div>
            </div>
          )}
        </div>

        <p className="text-center text-white/20 text-xs mt-4 font-mono">
          {step === 1 ? 'Demo: register first, then login' : 'Check your email for the OTP'}
        </p>
      </div>
    </div>
  )
}
