import { Users, Target, Zap, Clock, Cpu } from 'lucide-react'

function Stat({ icon: Icon, label, value, color = 'text-white/60' }) {
  return (
    <div className="flex flex-col items-center gap-1 px-5 py-3 border-r border-white/[0.06] last:border-r-0">
      <div className={`flex items-center gap-1.5 ${color} text-xs font-mono`}>
        <Icon size={12} />
        {value}
      </div>
      <p className="text-white/25 text-xs">{label}</p>
    </div>
  )
}

export default function AgentStatsBar({ log }) {
  if (!log) return null

  const durationSec = log.duration_ms ? (log.duration_ms / 1000).toFixed(1) : '—'

  return (
    <div className="glass-card flex flex-wrap items-center justify-around divide-x divide-white/[0.06] overflow-hidden">
      <Stat icon={Users}  label="CF Candidates"  value={log.cf_candidates}   color="text-blue-400" />
      <Stat icon={Target} label="CBF Candidates" value={log.cbf_candidates}  color="text-green-400" />
      <Stat icon={Zap}    label="Final Picks"    value={log.final_count}     color="text-brand-400" />
      <Stat icon={Cpu}    label="LLM Tokens"     value={log.llm_tokens_used} color="text-purple-400" />
      <Stat icon={Clock}  label="Run Time"       value={`${durationSec}s`}   color="text-white/50" />
    </div>
  )
}