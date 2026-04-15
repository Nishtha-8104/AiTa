import { CheckCircle2, Loader2, XCircle } from 'lucide-react'

export default function AgentSteps({ steps = [], evaluating }) {
  if (steps.length === 0 && !evaluating) return null

  // Show fake progress steps while evaluating (before real ones come in)
  const displaySteps = steps.length > 0 ? steps : evaluating ? [
    '🔍 Step 1: Running static analysis engine...',
    '📊 Step 2: Calculating dimension scores...',
    '🤖 Step 3: Calling Groq (llama-3.3-70b) for deep analysis...',
    '⚙️  Step 4: Blending static + LLM scores...',
    '💾 Step 5: Persisting evaluation results...',
  ] : []

  return (
    <div className="glass-card border-brand-500/15 overflow-hidden animate-fade-in">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/[0.06]">
        {evaluating
          ? <Loader2 size={14} className="text-brand-400 animate-spin" />
          : <CheckCircle2 size={14} className="text-green-400" />}
        <p className="font-display font-600 text-sm text-white">
          {evaluating ? 'Agent Running...' : 'Agent Thought Log'}
        </p>
        {evaluating && (
          <div className="ml-auto flex gap-1">
            {[0,1,2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse"
                style={{ animationDelay: `${i*200}ms` }} />
            ))}
          </div>
        )}
      </div>
      <div className="px-5 py-4 space-y-2.5 max-h-52 overflow-y-auto">
        {displaySteps.map((step, i) => {
          const isDone  = step.startsWith('✅')
          const isError = step.startsWith('❌')
          const isLast  = i === displaySteps.length - 1 && evaluating
          return (
            <div key={i} className="flex items-start gap-2.5 animate-slide-up"
              style={{ animationDelay: `${i * 50}ms`, animationFillMode: 'both' }}>
              <div className="shrink-0 mt-0.5">
                {isLast
                  ? <Loader2 size={13} className="text-brand-400 animate-spin" />
                  : isError
                    ? <XCircle size={13} className="text-red-400" />
                    : isDone
                      ? <CheckCircle2 size={13} className="text-green-400" />
                      : <div className="w-3 h-3 rounded-full border border-white/20" />}
              </div>
              <p className={`text-xs font-mono leading-relaxed ${
                isError ? 'text-red-300' : isDone ? 'text-green-300' : 'text-white/50'
              }`}>{step}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}