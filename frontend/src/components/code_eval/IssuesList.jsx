import { useState } from 'react'
import { AlertTriangle, XCircle, Info, AlertOctagon, Filter } from 'lucide-react'

const SEVERITY_CONFIG = {
  critical: { icon: AlertOctagon, color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/20',    label: 'Critical' },
  error:    { icon: XCircle,      color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20', label: 'Error'  },
  warning:  { icon: AlertTriangle,color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20',label: 'Warning'},
  info:     { icon: Info,         color: 'text-brand-400',  bg: 'bg-brand-500/10 border-brand-500/20',  label: 'Info'  },
}

const CATEGORY_COLORS = {
  security:      'text-red-300 bg-red-500/10',
  complexity:    'text-orange-300 bg-orange-500/10',
  logic:         'text-yellow-300 bg-yellow-500/10',
  quality:       'text-brand-300 bg-brand-600/10',
  naming:        'text-purple-300 bg-purple-500/10',
  style:         'text-pink-300 bg-pink-500/10',
  documentation: 'text-green-300 bg-green-500/10',
}

const SEVERITIES = ['critical', 'error', 'warning', 'info']

export default function IssuesList({ issues = [] }) {
  const [filter, setFilter] = useState('all')

  if (issues.length === 0) {
    return (
      <div className="glass-card p-6 text-center animate-fade-in">
        <div className="w-12 h-12 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center mx-auto mb-3">
          <span className="text-2xl">✅</span>
        </div>
        <p className="font-display font-600 text-white text-sm">No static issues found</p>
        <p className="text-white/30 text-xs mt-1">The static analyser found nothing to flag.</p>
      </div>
    )
  }

  const counts = SEVERITIES.reduce((acc, s) => {
    acc[s] = issues.filter(i => i.severity === s).length
    return acc
  }, {})

  const visible = filter === 'all' ? issues : issues.filter(i => i.severity === filter)

  return (
    <div className="glass-card animate-fade-in overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-white/40" />
          <span className="font-display font-600 text-sm text-white">Issues ({issues.length})</span>
        </div>
        <div className="flex items-center gap-1.5">
          {/* All filter */}
          <button onClick={() => setFilter('all')}
            className={`px-2.5 py-1 rounded-lg text-xs font-display font-600 transition-all ${filter === 'all' ? 'bg-surface-500 text-white' : 'text-white/30 hover:text-white/60'}`}>
            All
          </button>
          {SEVERITIES.map(s => {
            if (counts[s] === 0) return null
            const cfg = SEVERITY_CONFIG[s]
            return (
              <button key={s} onClick={() => setFilter(s)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-display font-600 border transition-all ${filter === s ? cfg.bg + ' ' + cfg.color : 'border-transparent text-white/30 hover:text-white/60'}`}>
                {counts[s]} {cfg.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Issue rows */}
      <div className="divide-y divide-white/[0.04] max-h-72 overflow-y-auto">
        {visible.map((issue) => {
          const cfg  = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.info
          const Icon = cfg.icon
          return (
            <div key={issue.id} className="px-5 py-3.5 hover:bg-surface-700/20 transition-colors">
              <div className="flex items-start gap-3">
                <Icon size={15} className={`${cfg.color} shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {issue.line && (
                      <span className="text-white/30 text-xs font-mono">Line {issue.line}</span>
                    )}
                    <span className={`px-2 py-0.5 rounded-md text-xs font-mono capitalize ${CATEGORY_COLORS[issue.category] || 'text-white/40 bg-surface-600'}`}>
                      {issue.category}
                    </span>
                  </div>
                  <p className="text-white/70 text-sm leading-relaxed">{issue.message}</p>
                  <p className="text-white/35 text-xs mt-1 flex items-start gap-1">
                    <span className="text-brand-400 shrink-0">↳</span>
                    {issue.suggestion}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}