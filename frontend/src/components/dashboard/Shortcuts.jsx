import { Link } from 'react-router-dom'
import { ArrowUpRight, MessageSquareText, Shapes, SquareTerminal } from 'lucide-react'

const ITEMS = [
  {
    to: '/topics', icon: Shapes, title: 'Topic practice',
    text: 'Read about one topic, then answer 10 questions on it.',
    tile: 'border-pop-aqua/20 bg-pop-aqua/[0.07] hover:bg-pop-aqua/[0.12]', chip: 'bg-pop-aqua',
  },
  {
    to: '/code-eval', icon: SquareTerminal, title: 'Code workspace',
    text: 'Bring any problem and code. We test and review it.',
    tile: 'border-pop-sun/20 bg-pop-sun/[0.06] hover:bg-pop-sun/[0.11]', chip: 'bg-pop-sun',
  },
  {
    to: '/feedback', icon: MessageSquareText, title: 'Feedback',
    text: 'Reports on what you do well and what to fix.',
    tile: 'border-pop-pink/20 bg-pop-pink/[0.07] hover:bg-pop-pink/[0.12]', chip: 'bg-pop-pink', badge: true,
  },
]

export default function Shortcuts({ unread }) {
  return (
    <nav aria-label="Other tools" className="grid grid-cols-1 gap-4 md:grid-cols-[1.25fr_1fr_1fr]">
      {ITEMS.map(({ to, icon: Icon, title, text, tile, chip, badge }) => (
        <Link
          key={to}
          to={to}
          className={`group relative flex min-h-[148px] flex-col rounded-tile border p-5 transition-[background-color,transform] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 active:scale-[0.99] ${tile}`}
        >
          <div className="flex items-start justify-between">
            <span className={`flex h-10 w-10 items-center justify-center rounded-xl text-canvas ${chip}`}>
              <Icon size={19} strokeWidth={2} />
            </span>
            {badge && unread > 0 ? (
              <span className="rounded-full bg-pop-pink px-2.5 py-0.5 font-mono text-xs font-semibold text-canvas">{unread} new</span>
            ) : (
              <ArrowUpRight size={18} className="text-ink-subtle transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink" />
            )}
          </div>
          <div className="mt-auto pt-6">
            <h3 className="text-[15px] font-semibold tracking-tight text-ink">{title}</h3>
            <p className="mt-1 text-[13px] leading-relaxed text-ink-subtle">{text}</p>
          </div>
        </Link>
      ))}
    </nav>
  )
}
