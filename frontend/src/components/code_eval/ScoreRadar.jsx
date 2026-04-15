import { useEffect, useState } from 'react'
import { Shield, Zap, Star, BookOpen, Code2, CheckCircle2 } from 'lucide-react'

const DIMENSIONS = [
  { key: 'correctness',   label: 'Correctness',   icon: CheckCircle2, color: 'bg-green-500',  text: 'text-green-400',  desc: 'Logic, output, edge cases' },
  { key: 'quality',       label: 'Code Quality',  icon: Star,         color: 'bg-brand-500',  text: 'text-brand-400',  desc: 'Naming, structure, DRY' },
  { key: 'efficiency',    label: 'Efficiency',    icon: Zap,          color: 'bg-yellow-500', text: 'text-yellow-400', desc: 'Time & space complexity' },
  { key: 'security',      label: 'Security',      icon: Shield,       color: 'bg-red-500',    text: 'text-red-400',    desc: 'Injection, eval, vulnerabilities' },
  { key: 'style',         label: 'Style',         icon: Code2,        color: 'bg-purple-500', text: 'text-purple-400', desc: 'Formatting, conventions' },
  { key: 'documentation', label: 'Docs',          icon: BookOpen,     color: 'bg-pink-500',   text: 'text-pink-400',   desc: 'Comments, docstrings' },
]

function ScoreGauge({ score }) {
  const [animated, setAnimated] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setAnimated(score), 100)
    return () => clearTimeout(t)
  }, [score])

  const color =
    score >= 80 ? '#22c55e' :
    score >= 60 ? '#f59e0b' :
    score >= 40 ? '#f97316' : '#ef4444'

  const radius      = 54
  const circumf     = 2 * Math.PI * radius
  const dashOffset  = circumf - (animated / 100) * circumf

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-36 h-36">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          {/* Track */}
          <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
          {/* Progress */}
          <circle
            cx="60" cy="60" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumf}
            strokeDashoffset={dashOffset}
            style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display font-800 text-3xl text-white">{score.toFixed(0)}</span>
          <span className="text-white/30 text-xs font-mono">/ 100</span>
        </div>
      </div>
      <div className="text-center">
        <p className="font-display font-700 text-sm" style={{ color }}>
          {score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : score >= 40 ? 'Needs Work' : 'Poor'}
        </p>
        <p className="text-white/30 text-xs">Overall Score</p>
      </div>
    </div>
  )
}

function DimBar({ dim, score }) {
  const [animated, setAnimated] = useState(0)
  const Icon = dim.icon

  useEffect(() => {
    const t = setTimeout(() => setAnimated(score), 150)
    return () => clearTimeout(t)
  }, [score])

  return (
    <div className="group">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <Icon size={13} className={dim.text} />
          <span className="text-white/60 text-xs font-display font-600">{dim.label}</span>
        </div>
        <span className={`text-xs font-mono font-600 ${dim.text}`}>{score.toFixed(0)}</span>
      </div>
      <div className="h-2 bg-surface-600/60 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${dim.color} transition-all duration-1000 ease-out`}
          style={{ width: `${animated}%`, opacity: 0.85 }}
        />
      </div>
      <p className="text-white/20 text-xs mt-1 opacity-0 group-hover:opacity-100 transition-opacity">{dim.desc}</p>
    </div>
  )
}

export default function ScoreRadar({ scores }) {
  if (!scores) return null

  return (
    <div className="glass-card p-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row items-center gap-8">
        {/* Gauge */}
        <div className="shrink-0">
          <ScoreGauge score={scores.overall || 0} />
        </div>

        {/* Dimension bars */}
        <div className="flex-1 w-full space-y-3">
          {DIMENSIONS.map(dim => (
            <DimBar key={dim.key} dim={dim} score={scores[dim.key] || 0} />
          ))}
        </div>
      </div>
    </div>
  )
}