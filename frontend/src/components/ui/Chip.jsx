const TONES = {
  neutral: 'border-line-strong bg-tile-2 text-ink-muted',
  mint:    'border-pop-mint/25 bg-pop-mint/10 text-pop-mint',
  aqua:    'border-pop-aqua/25 bg-pop-aqua/10 text-pop-aqua',
  sun:     'border-pop-sun/25 bg-pop-sun/10 text-pop-sun',
  pink:    'border-pop-pink/25 bg-pop-pink/10 text-pop-pink',
  coral:   'border-pop-coral/25 bg-pop-coral/10 text-pop-coral',
  brand:   'border-brand-400/30 bg-brand-500/10 text-brand-300',
}

export default function Chip({ tone = 'neutral', icon: Icon, className = '', children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}>
      {Icon && <Icon size={12} strokeWidth={2} />}
      {children}
    </span>
  )
}
