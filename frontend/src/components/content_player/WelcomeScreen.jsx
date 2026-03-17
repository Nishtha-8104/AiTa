import { MessageSquare, Code2, Brain, Puzzle, BookOpen, Zap, ArrowRight } from 'lucide-react'

const MODES = [
  {
    value: 'qa',
    icon: MessageSquare,
    title: 'Q&A',
    subtitle: 'Concept Explanation',
    color: 'text-brand-400',
    bg: 'bg-brand-600/10 border-brand-500/20 hover:border-brand-500/40',
    desc: 'Ask any programming question. The agent explains with analogies, examples, and Socratic follow-ups.',
    example: '"How does recursion work?" or "Explain Big-O notation"',
  },
  {
    value: 'code_help',
    icon: Code2,
    title: 'Code Help',
    subtitle: 'Debug & Understand',
    color: 'text-green-400',
    bg: 'bg-green-600/10 border-green-500/20 hover:border-green-500/40',
    desc: 'Paste code + errors. The agent guides you to find the bug without giving the answer directly.',
    example: '"My for loop isn\'t iterating correctly" + paste code',
  },
  {
    value: 'brainstorm',
    icon: Brain,
    title: 'Brainstorm',
    subtitle: 'Design Approaches',
    color: 'text-purple-400',
    bg: 'bg-purple-600/10 border-purple-500/20 hover:border-purple-500/40',
    desc: 'Think through problem approaches, compare trade-offs, and design solutions with AI guidance.',
    example: '"How should I design a URL shortener?" ',
  },
  {
    value: 'quiz',
    icon: Puzzle,
    title: 'Quiz Me',
    subtitle: 'Test Your Knowledge',
    color: 'text-yellow-400',
    bg: 'bg-yellow-600/10 border-yellow-500/20 hover:border-yellow-500/40',
    desc: 'Adaptive quiz that adjusts difficulty based on your answers. Great for exam prep.',
    example: '"Quiz me on Python lists" or "Test my SQL knowledge"',
  },
  {
    value: 'walkthrough',
    icon: BookOpen,
    title: 'Walkthrough',
    subtitle: 'Step-by-Step',
    color: 'text-pink-400',
    bg: 'bg-pink-600/10 border-pink-500/20 hover:border-pink-500/40',
    desc: 'A guided walkthrough of any concept from scratch. Numbered steps with examples and checkpoints.',
    example: '"Walk me through binary search trees"',
  },
]

export default function WelcomeScreen({ onStartSession }) {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600/10 border border-brand-500/20 rounded-full text-brand-400 text-xs font-mono mb-4">
            <Zap size={12} />
            Powered by Groq · llama-3.3-70b-versatile
          </div>
          <h1 className="font-display font-800 text-4xl text-white mb-3">
            Content Player Agent
          </h1>
          <p className="text-white/40 text-base max-w-xl mx-auto leading-relaxed">
            Your AI tutor that adapts to your skill level, guides you through concepts,
            and never just gives answers — it teaches you to think.
          </p>
        </div>

        {/* Mode cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {MODES.map(m => {
            const Icon = m.icon
            return (
              <button
                key={m.value}
                onClick={() => onStartSession(m.value)}
                className={`group glass-card p-5 border text-left transition-all duration-200 hover:-translate-y-0.5 ${m.bg}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${m.bg.split(' ')[0]}`}>
                    <Icon size={20} className={m.color} />
                  </div>
                  <ArrowRight size={16} className="text-white/20 group-hover:text-white/50 transition-colors mt-1" />
                </div>
                <p className="font-display font-700 text-white text-sm mb-0.5">{m.title}</p>
                <p className={`text-xs font-mono mb-2 ${m.color}`}>{m.subtitle}</p>
                <p className="text-white/40 text-xs leading-relaxed mb-3">{m.desc}</p>
                <p className="text-white/20 text-xs italic">{m.example}</p>
              </button>
            )
          })}
        </div>

        {/* Feature callouts */}
        <div className="glass-card p-5">
          <p className="text-white/20 text-xs font-mono uppercase tracking-wider mb-4">How this agent works</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { icon: '🧠', title: 'Knows You', desc: 'Uses your skill level, weak areas, and learning goals from your profile to adapt responses.' },
              { icon: '🎯', title: 'Guides, Not Solves', desc: 'Designed around the Socratic method — hints and questions over direct answers.' },
              { icon: '📊', title: 'Feeds Your Profile', desc: 'Every session updates your User Profiling Agent with mastery and weakness signals.' },
            ].map(f => (
              <div key={f.title} className="flex items-start gap-3">
                <span className="text-2xl">{f.icon}</span>
                <div>
                  <p className="font-display font-600 text-white text-sm mb-1">{f.title}</p>
                  <p className="text-white/35 text-xs leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}