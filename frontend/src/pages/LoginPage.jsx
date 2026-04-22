import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, Sparkles, AlertCircle, ShieldCheck, RefreshCw, KeyRound } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { authAPI } from '../utils/api'
import toast from 'react-hot-toast'

// ── Single-input OTP component — one invisible input, 6 visual boxes ─────────
function OtpInput({ value, onChange, error, autoFocus }) {
  const digits = (value + '      ').slice(0, 6).split('')
  return (
    <div className="relative flex justify-center">
      <div className="flex gap-2 pointer-events-none select-none">
        {digits.map((d, i) => (
          <div key={i} className={`w-12 h-14 rounded-xl border flex items-center justify-center text-xl font-mono font-700 transition-all ${
            error
              ? 'border-red-500/60 bg-red-500/5 text-red-300'
              : d.trim()
              ? 'border-brand-500/60 bg-brand-600/10 text-white'
              : value.length === i
              ? 'border-brand-400/80 bg-brand-600/5'
              : 'border-white/10 bg-surface-700/60'
          }`}>
            {d.trim()
              ? d
              : value.length === i
              ? <span className="animate-pulse text-brand-400 text-2xl leading-none">|</span>
              : null}
          </div>
        ))}
      </div>
      {/* Invisible input that captures all typing */}
      <input
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        autoFocus={autoFocus}
        value={value}
        maxLength={6}
        onChange={e => onChange(e.target.value.replace(/\D/g, '').slice(0, 6))}
        className="absolute inset-0 opacity-0 cursor-text w-full"
      />
    </div>
  )
}

export default function LoginPage() {
  const { loginStep1, loginStep2 } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/dashboard'

  const [mode, setMode] = useState('login')   // 'login' | 'forgot'

  // ── Login state ───────────────────────────────────────────────────────────
  const [form,         setForm]         = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [errors,       setErrors]       = useState({})
  const [loading,      setLoading]      = useState(false)
  const [step,         setStep]         = useState(1)
  const [otpToken,     setOtpToken]     = useState('')
  const [emailHint,    setEmailHint]    = useState('')
  const [otp,          setOtp]          = useState('')
  const [otpError,     setOtpError]     = useState('')
  const [verifying,    setVerifying]    = useState(false)
  const [resending,    setResending]    = useState(false)
  const [countdown,    setCountdown]    = useState(0)

  // ── Forgot password state ─────────────────────────────────────────────────
  const [fpEmail,       setFpEmail]       = useState('')
  const [fpStep,        setFpStep]        = useState(1)
  const [fpOtpToken,    setFpOtpToken]    = useState('')
  const [fpEmailHint,   setFpEmailHint]   = useState('')
  const [fpOtp,         setFpOtp]         = useState('')
  const [fpOtpError,    setFpOtpError]    = useState('')
  const [fpNewPassword, setFpNewPassword] = useState('')
  const [fpShowPw,      setFpShowPw]      = useState(false)
  const [fpLoading,     setFpLoading]     = useState(false)
  const [fpCountdown,   setFpCountdown]   = useState(0)

  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  useEffect(() => {
    if (fpCountdown <= 0) return
    const t = setTimeout(() => setFpCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [fpCountdown])

  // Auto-submit when 6 digits entered
  useEffect(() => {
    if (otp.length === 6) handleVerifyOtp(otp)
  }, [otp])

  useEffect(() => {
    if (fpOtp.length === 6 && fpStep === 2) handleFpVerifyOtp(fpOtp)
  }, [fpOtp])

  // ── Login handlers ────────────────────────────────────────────────────────
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
      setOtpToken(data.otp_token); setEmailHint(data.email_hint)
      setStep(2); setCountdown(30); setOtp('')
      toast.success('OTP sent to your email!')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed.'
      toast.error(msg); setErrors({ general: msg })
    } finally { setLoading(false) }
  }

  const handleVerifyOtp = async (code = otp) => {
    if (code.length < 6) { setOtpError('Enter all 6 digits'); return }
    if (verifying) return
    setVerifying(true); setOtpError('')
    try {
      const user = await loginStep2(otpToken, code)
      toast.success(`Welcome back, ${user.username}! 👋`)
      navigate(from, { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid OTP.'
      setOtpError(msg); setOtp('')
    } finally { setVerifying(false) }
  }

  const handleResend = async () => {
    if (countdown > 0) return
    setResending(true)
    try {
      const data = await loginStep1(form.email, form.password)
      setOtpToken(data.otp_token); setOtp(''); setOtpError(''); setCountdown(30)
      toast.success('New OTP sent!')
    } catch { toast.error('Failed to resend OTP.') }
    finally { setResending(false) }
  }

  // ── Forgot password handlers ──────────────────────────────────────────────
  const handleFpSendOtp = async (e) => {
    e.preventDefault()
    if (!fpEmail || !/\S+@\S+\.\S+/.test(fpEmail)) { toast.error('Enter a valid email'); return }
    setFpLoading(true)
    try {
      const { data } = await authAPI.forgotPassword(fpEmail)
      setFpOtpToken(data.otp_token); setFpEmailHint(data.email_hint)
      setFpStep(2); setFpCountdown(30); setFpOtp('')
      toast.success('OTP sent! Check your email.')
    } catch { toast.error('Something went wrong. Try again.') }
    finally { setFpLoading(false) }
  }

  const handleFpVerifyOtp = (code = fpOtp) => {
    if (code.length < 6) { setFpOtpError('Enter all 6 digits'); return }
    setFpStep(3)
  }

  const handleFpResend = async () => {
    if (fpCountdown > 0) return
    setFpLoading(true)
    try {
      const { data } = await authAPI.forgotPassword(fpEmail)
      setFpOtpToken(data.otp_token); setFpOtp(''); setFpOtpError(''); setFpCountdown(30)
      toast.success('New OTP sent!')
    } catch { toast.error('Failed to resend.') }
    finally { setFpLoading(false) }
  }

  const handleFpReset = async (e) => {
    e.preventDefault()
    if (!fpNewPassword || fpNewPassword.length < 8) { toast.error('Min 8 characters'); return }
    setFpLoading(true)
    try {
      await authAPI.resetPassword({ otp_token: fpOtpToken, otp: fpOtp, new_password: fpNewPassword })
      toast.success('Password reset! You can now log in.')
      setMode('login'); setFpStep(1); setFpEmail(''); setFpOtp(''); setFpNewPassword('')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reset failed.')
    } finally { setFpLoading(false) }
  }

  const title = mode === 'forgot'
    ? fpStep === 1 ? 'Reset your password' : fpStep === 2 ? 'Verify your email' : 'Set new password'
    : step === 1 ? 'Welcome back' : 'Verify your identity'

  const subtitle = mode === 'forgot'
    ? fpStep === 1 ? "Enter your email and we'll send you an OTP"
    : fpStep === 2 ? `OTP sent to ${fpEmailHint}`
    : 'Almost there — set your new password'
    : step === 1 ? 'Sign in to continue your learning journey'
    : `Enter the 6-digit OTP sent to ${emailHint}`

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
          <h1 className="font-display font-700 text-3xl text-white">{title}</h1>
          <p className="text-white/40 font-body mt-2 text-sm">{subtitle}</p>
        </div>

        {/* Step indicators */}
        {mode === 'login' && (
          <div className="flex items-center gap-2 justify-center mb-6">
            {[1, 2].map(s => (
              <div key={s} className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-700 transition-all ${
                  step === s ? 'bg-brand-600 text-white' : step > s ? 'bg-green-600 text-white' : 'bg-surface-700 text-white/30'
                }`}>{step > s ? '✓' : s}</div>
                {s < 2 && <div className={`w-10 h-0.5 rounded-full transition-all ${step > 1 ? 'bg-green-600' : 'bg-surface-700'}`} />}
              </div>
            ))}
          </div>
        )}
        {mode === 'forgot' && (
          <div className="flex items-center gap-2 justify-center mb-6">
            {[1, 2, 3].map(s => (
              <div key={s} className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-700 transition-all ${
                  fpStep === s ? 'bg-brand-600 text-white' : fpStep > s ? 'bg-green-600 text-white' : 'bg-surface-700 text-white/30'
                }`}>{fpStep > s ? '✓' : s}</div>
                {s < 3 && <div className={`w-10 h-0.5 rounded-full transition-all ${fpStep > s ? 'bg-green-600' : 'bg-surface-700'}`} />}
              </div>
            ))}
          </div>
        )}

        <div className="glass-card p-8">

          {/* ── Login Step 1 ── */}
          {mode === 'login' && step === 1 && (
            <>
              {errors.general && (
                <div className="mb-5 flex items-center gap-2.5 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm">
                  <AlertCircle size={16} className="shrink-0" />{errors.general}
                </div>
              )}
              <form onSubmit={handleStep1} className="space-y-5">
                <div>
                  <label className="label">Email Address</label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                    <input type="email" value={form.email}
                      onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                      placeholder="you@example.com"
                      className={`input-field pl-11 ${errors.email ? 'border-red-500/50' : ''}`}
                      autoComplete="email" />
                  </div>
                  {errors.email && <p className="error-text"><AlertCircle size={12} />{errors.email}</p>}
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="label mb-0">Password</label>
                    <button type="button" onClick={() => setMode('forgot')}
                      className="text-brand-400 hover:text-brand-300 text-xs font-display font-600 transition-colors">
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                    <input type={showPassword ? 'text' : 'password'} value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      placeholder="••••••••"
                      className={`input-field pl-11 pr-12 ${errors.password ? 'border-red-500/50' : ''}`}
                      autoComplete="current-password" />
                    <button type="button" onClick={() => setShowPassword(v => !v)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.password && <p className="error-text"><AlertCircle size={12} />{errors.password}</p>}
                </div>
                <button type="submit" disabled={loading} className="btn-primary mt-2">
                  {loading
                    ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Sending OTP…</span>
                    : 'Continue →'}
                </button>
              </form>
              <p className="text-center text-white/30 text-sm mt-6">
                Don't have an account?{' '}
                <Link to="/register" className="text-brand-400 hover:text-brand-300 font-500 transition-colors">Create one</Link>
              </p>
            </>
          )}

          {/* ── Login Step 2 OTP ── */}
          {mode === 'login' && step === 2 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 p-4 bg-brand-600/8 border border-brand-500/20 rounded-xl">
                <ShieldCheck size={20} className="text-brand-400 shrink-0" />
                <p className="text-white/60 text-sm">
                  OTP sent to <span className="text-white font-600">{emailHint}</span>. Expires in 10 minutes.
                </p>
              </div>
              <div>
                <label className="label text-center block mb-3">
                  Enter OTP {otp.length === 6 && !verifying && <span className="text-brand-400 text-xs ml-1">✓ verifying…</span>}
                </label>
                <OtpInput value={otp} onChange={v => { setOtp(v); setOtpError('') }} error={otpError} autoFocus />
                {otpError && (
                  <p className="flex items-center justify-center gap-1.5 text-red-400 text-xs mt-3">
                    <AlertCircle size={12} />{otpError}
                  </p>
                )}
              </div>
              <button onClick={() => handleVerifyOtp()} disabled={verifying || otp.length < 6} className="btn-primary">
                {verifying
                  ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Verifying…</span>
                  : <span className="flex items-center justify-center gap-2"><ShieldCheck size={16} />Verify & Sign In</span>}
              </button>
              <div className="flex items-center justify-between text-sm">
                <button onClick={() => { setStep(1); setOtp(''); setOtpError('') }}
                  className="text-white/30 hover:text-white/60 transition-colors">← Back</button>
                <button onClick={handleResend} disabled={countdown > 0 || resending}
                  className="flex items-center gap-1.5 text-brand-400 hover:text-brand-300 disabled:text-white/20 disabled:cursor-not-allowed transition-colors">
                  <RefreshCw size={13} className={resending ? 'animate-spin' : ''} />
                  {countdown > 0 ? `Resend in ${countdown}s` : 'Resend OTP'}
                </button>
              </div>
            </div>
          )}

          {/* ── Forgot Step 1 ── */}
          {mode === 'forgot' && fpStep === 1 && (
            <form onSubmit={handleFpSendOtp} className="space-y-5">
              <div>
                <label className="label">Registered Email</label>
                <div className="relative">
                  <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type="email" value={fpEmail} onChange={e => setFpEmail(e.target.value)}
                    placeholder="you@example.com" className="input-field pl-11" autoFocus />
                </div>
              </div>
              <button type="submit" disabled={fpLoading} className="btn-primary">
                {fpLoading
                  ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Sending OTP…</span>
                  : <span className="flex items-center justify-center gap-2"><KeyRound size={15} />Send Reset OTP</span>}
              </button>
              <p className="text-center">
                <button type="button" onClick={() => setMode('login')}
                  className="text-white/30 hover:text-white/60 text-sm transition-colors">← Back to login</button>
              </p>
            </form>
          )}

          {/* ── Forgot Step 2 OTP ── */}
          {mode === 'forgot' && fpStep === 2 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 p-4 bg-brand-600/8 border border-brand-500/20 rounded-xl">
                <ShieldCheck size={20} className="text-brand-400 shrink-0" />
                <p className="text-white/60 text-sm">
                  OTP sent to <span className="text-white font-600">{fpEmailHint}</span>. Expires in 10 minutes.
                </p>
              </div>
              <div>
                <label className="label text-center block mb-3">Enter OTP</label>
                <OtpInput value={fpOtp} onChange={v => { setFpOtp(v); setFpOtpError('') }} error={fpOtpError} autoFocus />
                {fpOtpError && (
                  <p className="flex items-center justify-center gap-1.5 text-red-400 text-xs mt-3">
                    <AlertCircle size={12} />{fpOtpError}
                  </p>
                )}
              </div>
              <button onClick={() => handleFpVerifyOtp()} disabled={fpOtp.length < 6} className="btn-primary">
                <span className="flex items-center justify-center gap-2"><ShieldCheck size={16} />Verify OTP</span>
              </button>
              <div className="flex items-center justify-between text-sm">
                <button onClick={() => setFpStep(1)} className="text-white/30 hover:text-white/60 transition-colors">← Back</button>
                <button onClick={handleFpResend} disabled={fpCountdown > 0 || fpLoading}
                  className="flex items-center gap-1.5 text-brand-400 hover:text-brand-300 disabled:text-white/20 disabled:cursor-not-allowed transition-colors">
                  <RefreshCw size={13} className={fpLoading ? 'animate-spin' : ''} />
                  {fpCountdown > 0 ? `Resend in ${fpCountdown}s` : 'Resend OTP'}
                </button>
              </div>
            </div>
          )}

          {/* ── Forgot Step 3 new password ── */}
          {mode === 'forgot' && fpStep === 3 && (
            <form onSubmit={handleFpReset} className="space-y-5">
              <div className="flex items-center gap-3 p-4 bg-green-600/8 border border-green-500/20 rounded-xl">
                <ShieldCheck size={18} className="text-green-400 shrink-0" />
                <p className="text-white/60 text-sm">OTP verified. Set your new password below.</p>
              </div>
              <div>
                <label className="label">New Password</label>
                <div className="relative">
                  <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
                  <input type={fpShowPw ? 'text' : 'password'} value={fpNewPassword}
                    onChange={e => setFpNewPassword(e.target.value)}
                    placeholder="Min 8 chars, 1 uppercase, 1 digit"
                    className="input-field pl-11 pr-12" autoFocus />
                  <button type="button" onClick={() => setFpShowPw(v => !v)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
                    {fpShowPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <button type="submit" disabled={fpLoading} className="btn-primary">
                {fpLoading
                  ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />Resetting…</span>
                  : <span className="flex items-center justify-center gap-2"><KeyRound size={15} />Reset Password</span>}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-white/20 text-xs mt-4 font-mono">
          {mode === 'forgot' ? 'Check your email for the OTP' : step === 1 ? 'Demo: register first, then login' : 'Check your email for the OTP'}
        </p>
      </div>
    </div>
  )
}
