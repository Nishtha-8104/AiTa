import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, MessageSquare, Zap, Loader2,
  Clock, ChevronRight, X, Brain, TrendingUp,
  AlertCircle, User, Sparkles
} from 'lucide-react'
import { useFeedback } from '../hooks/useFeedback'
import FeedbackCard from '../components/feedback/FeedbackCard'

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr)
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const TYPE_COLOR = {
  code_review:    '#f97316',
  learning_recap: '#14b8a6',
  combined:       '#ec4899',
}

const CAPABILITIES = [
  { icon: Brain,       color: '#ec4899', bg: 'rgba(236,72,153,0.1)',  title: 'Pattern Analysis',       desc: 'Tracks errors and conceptual gaps across all your sessions automatically.' },
  { icon: AlertCircle, color: '#f59e0b', bg: 'rgba(245,158,11,0.1)',  title: 'Context-Aware Feedback', desc: 'Explains why errors matter and how to fix them — not just correct/incorrect.' },
  { icon: TrendingUp,  color: '#14b8a6', bg: 'rgba(20,184,166,0.1)',  title: 'Skill Progression',      desc: 'Synthesises Code Eval and Learning Studio findings into actionable next steps.' },
  { icon: User,        color: '#818cf8', bg: 'rgba(129,140,248,0.1)', title: 'Profile Updates',         desc: 'Writes weak areas and mastery signals back to your profile in real time.' },
]

function HistoryItem({ report, isActive, onClick }) {
  const dot = TYPE_COLOR[report.feedback_type] || '#ec4899'
  return (
    <button onClick={onClick} style={{
      ...S.histItem,
      background: isActive ? 'rgba(236,72,153,0.08)' : 'transparent',
      border: `1px solid ${isActive ? 'rgba(236,72,153,0.25)' : 'transparent'}`,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: dot, flexShrink: 0, marginTop: 4 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={S.histTitle}>{report.headline || 'Feedback Report'}</p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 }}>
          <span style={S.histType}>{report.feedback_type?.replace('_', ' ')}</span>
          {!report.is_read && <span style={S.unreadDot} />}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
          <Clock size={9} color="rgba(255,255,255,0.2)" />
          <span style={S.histTime}>{timeAgo(report.created_at)}</span>
        </div>
      </div>
      {isActive && <ChevronRight size={13} color="#ec4899" style={{ flexShrink: 0 }} />}
    </button>
  )
}

export default function FeedbackPage() {
  const navigate = useNavigate()
  const { reports, activeReport, generating, loading, fetchReports, openReport, autoGenerate, clearActive } = useFeedback()

  useEffect(() => { fetchReports() }, [])

  const unread = reports.filter(r => !r.is_read).length

  return (
    <div style={S.page}>
      <div style={S.gridBg} />

      {/* Navbar */}
      <nav style={S.nav}>
        <div style={S.navInner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={() => navigate('/dashboard')} style={S.backBtn}><ArrowLeft size={16} /></button>
            <div style={S.navBrand}>
              <div style={S.navIcon}><MessageSquare size={13} color="#fff" /></div>
              <span style={S.navTitle}>Feedback <span style={{ color: '#ec4899' }}>Agent</span></span>
            </div>
            {unread > 0 && <span style={S.badge}>{unread}</span>}
          </div>

          <button
            onClick={autoGenerate}
            disabled={generating}
            style={{ ...S.genBtn, opacity: generating ? 0.7 : 1 }}
          >
            {generating
              ? <><Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Analysing…</>
              : <><Zap size={14} /> Get My Feedback</>}
          </button>
        </div>
      </nav>

      <div style={S.body}>
        <div style={S.layout}>

          {/* Sidebar */}
          <div style={S.sidebar}>
            <div style={S.sidebarHead}>
              <p style={S.sidebarTitle}>Report History</p>
              <span style={S.sidebarCount}>{reports.length}</span>
            </div>

            <div style={S.sidebarBody}>
              {loading && [1,2,3].map(i => <div key={i} style={S.skel} />)}

              {!loading && reports.length === 0 && (
                <div style={S.sidebarEmpty}>
                  <MessageSquare size={22} color="rgba(255,255,255,0.1)" />
                  <p style={{ color: 'rgba(255,255,255,0.25)', fontSize: 12, margin: '8px 0 4px' }}>No reports yet</p>
                  <p style={{ color: 'rgba(255,255,255,0.15)', fontSize: 11, margin: 0 }}>Click "Get My Feedback" above</p>
                </div>
              )}

              {reports.map(r => (
                <HistoryItem
                  key={r.id}
                  report={r}
                  isActive={activeReport?.id === r.id}
                  onClick={() => openReport(r.id)}
                />
              ))}
            </div>
          </div>

          {/* Main */}
          <div style={S.main}>

            {/* Generating */}
            {generating && (
              <div style={S.generatingCard}>
                <div style={S.genIconWrap}>
                  <Loader2 size={28} color="#ec4899" style={{ animation: 'spin 1s linear infinite' }} />
                </div>
                <h3 style={S.genTitle}>Analysing your performance…</h3>
                <p style={S.genSub}>Reading your latest code evaluation and learning sessions</p>
                <div style={S.stepsList}>
                  {[
                    { e: '🔍', t: 'Fetching latest code evaluation' },
                    { e: '📚', t: 'Reading learning session data' },
                    { e: '📊', t: 'Identifying error patterns and gaps' },
                    { e: '🤖', t: 'Groq LLM synthesising personalised feedback' },
                    { e: '👤', t: 'Updating your profile in real time' },
                  ].map((s, i) => (
                    <div key={i} style={S.stepRow}>
                      <span>{s.e}</span>
                      <span style={S.stepText}>{s.t}</span>
                      <span style={{ color: '#ec4899', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: `${i * 0.2}s` }}>▸</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Active report */}
            {!generating && activeReport && (
              <div>
                <div style={S.reportBar}>
                  <span style={S.reportLabel}>Report #{activeReport.id}</span>
                  <button onClick={clearActive} style={S.closeBtn}><X size={14} /></button>
                </div>
                <FeedbackCard report={activeReport} />
              </div>
            )}

            {/* Empty state */}
            {!generating && !activeReport && (
              <div style={S.emptyCard}>
                <div style={S.emptyIcon}><Sparkles size={28} color="#ec4899" /></div>
                <h2 style={S.emptyTitle}>Feedback Agent</h2>
                <p style={S.emptyDesc}>
                  Automatically analyses your latest code evaluation and learning sessions.
                  No setup needed — just click <strong style={{ color: '#ec4899' }}>Get My Feedback</strong> and
                  the agent reads your recent activity, identifies patterns, and delivers
                  personalised, actionable feedback in seconds.
                </p>

                <div style={S.capGrid}>
                  {CAPABILITIES.map(c => {
                    const Icon = c.icon
                    return (
                      <div key={c.title} style={S.capCard}>
                        <div style={{ ...S.capIcon, background: c.bg }}>
                          <Icon size={17} color={c.color} />
                        </div>
                        <p style={S.capTitle}>{c.title}</p>
                        <p style={S.capDesc}>{c.desc}</p>
                      </div>
                    )
                  })}
                </div>

                <button onClick={autoGenerate} disabled={generating} style={{ ...S.genBtn, marginTop: 8, padding: '12px 32px', fontSize: 15 }}>
                  <Zap size={16} /> Get My Feedback
                </button>

                {reports.length > 0 && (
                  <p style={{ color: 'rgba(255,255,255,0.2)', fontSize: 12, marginTop: 16 }}>
                    ← Select a past report from history
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:.3} 50%{opacity:1} }
      `}</style>
    </div>
  )
}

const S = {
  page:    { minHeight: '100vh', background: '#050810', fontFamily: "'DM Sans','Segoe UI',sans-serif", position: 'relative' },
  gridBg:  { position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, backgroundImage: `linear-gradient(rgba(236,72,153,0.015) 1px,transparent 1px),linear-gradient(90deg,rgba(236,72,153,0.015) 1px,transparent 1px)`, backgroundSize: '48px 48px' },
  nav:     { position: 'sticky', top: 0, zIndex: 50, background: 'rgba(5,8,16,0.92)', borderBottom: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)' },
  navInner:{ maxWidth: 1200, margin: '0 auto', padding: '0 24px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  backBtn: { background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '7px 10px', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center' },
  navBrand:{ display: 'flex', alignItems: 'center', gap: 8 },
  navIcon: { width: 28, height: 28, borderRadius: 8, background: '#be185d', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  navTitle:{ fontSize: 15, fontWeight: 700, color: '#fff' },
  badge:   { background: '#ec4899', color: '#fff', fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 20, fontFamily: 'monospace' },
  genBtn:  { display: 'flex', alignItems: 'center', gap: 7, background: '#be185d', border: 'none', borderRadius: 10, padding: '9px 20px', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer', transition: 'opacity 0.15s' },
  body:    { maxWidth: 1200, margin: '0 auto', padding: '24px', position: 'relative', zIndex: 1 },
  layout:  { display: 'grid', gridTemplateColumns: '280px 1fr', gap: 20, alignItems: 'start' },
  // Sidebar
  sidebar:     { background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, overflow: 'hidden' },
  sidebarHead: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)' },
  sidebarTitle:{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.8px', margin: 0 },
  sidebarCount:{ fontSize: 11, color: 'rgba(255,255,255,0.25)', fontFamily: 'monospace' },
  sidebarBody: { padding: '6px 8px' },
  sidebarEmpty:{ padding: '28px 16px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' },
  skel:        { height: 52, background: 'rgba(255,255,255,0.04)', borderRadius: 10, marginBottom: 6, animation: 'pulse 1.5s ease-in-out infinite' },
  histItem:    { width: '100%', display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', borderRadius: 10, cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s', marginBottom: 2 },
  histTitle:   { fontSize: 13, fontWeight: 600, color: 'rgba(255,255,255,0.8)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 180 },
  histType:    { fontSize: 11, color: 'rgba(255,255,255,0.25)', fontFamily: 'monospace', textTransform: 'capitalize' },
  histTime:    { fontSize: 11, color: 'rgba(255,255,255,0.2)' },
  unreadDot:   { width: 6, height: 6, borderRadius: '50%', background: '#ec4899', flexShrink: 0 },
  // Main
  main:        { minWidth: 0 },
  reportBar:   { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  reportLabel: { fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase', letterSpacing: '1px', fontFamily: 'monospace' },
  closeBtn:    { background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.3)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', borderRadius: 6 },
  // Generating
  generatingCard: { background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(236,72,153,0.15)', borderRadius: 20, padding: '48px 36px', textAlign: 'center' },
  genIconWrap:    { width: 64, height: 64, borderRadius: 20, background: 'rgba(236,72,153,0.1)', border: '1px solid rgba(236,72,153,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' },
  genTitle:       { fontSize: 18, fontWeight: 700, color: '#fff', margin: '0 0 6px' },
  genSub:         { fontSize: 13, color: 'rgba(255,255,255,0.35)', margin: '0 0 28px' },
  stepsList:      { display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'left', maxWidth: 400, margin: '0 auto' },
  stepRow:        { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: 10 },
  stepText:       { flex: 1, fontSize: 13, color: 'rgba(255,255,255,0.6)' },
  // Empty
  emptyCard:  { background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 20, padding: '44px 40px', textAlign: 'center' },
  emptyIcon:  { width: 64, height: 64, borderRadius: 20, background: 'rgba(236,72,153,0.1)', border: '1px solid rgba(236,72,153,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' },
  emptyTitle: { fontSize: 22, fontWeight: 700, color: '#fff', margin: '0 0 12px', letterSpacing: '-0.3px' },
  emptyDesc:  { fontSize: 14, color: 'rgba(255,255,255,0.45)', lineHeight: 1.75, maxWidth: 520, margin: '0 auto 32px' },
  capGrid:    { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 28, textAlign: 'left' },
  capCard:    { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 14, padding: '16px' },
  capIcon:    { width: 38, height: 38, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 },
  capTitle:   { fontSize: 13, fontWeight: 700, color: '#fff', margin: '0 0 5px' },
  capDesc:    { fontSize: 12, color: 'rgba(255,255,255,0.4)', lineHeight: 1.6, margin: 0 },
}
