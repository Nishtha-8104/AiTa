import { palette, paper } from '../../styles/palette'

export default function LogoMark({ className = 'h-8 w-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={`shrink-0 ${className}`} aria-hidden="true">
      <rect x="0.75" y="0.75" width="30.5" height="30.5" rx="9.25" fill={paper.tile.DEFAULT} stroke={paper.line.strong} strokeWidth="1.5" />
      <path d="M9.5 10.5 15 16l-5.5 5.5" fill="none" stroke={palette.canvas} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="17.25" y="19.75" width="6.5" height="2.75" rx="1.375" fill={paper.pop.mint} className="motion-safe:animate-blink" />
      <path d="M23.5 7.25v4.5M21.25 9.5h4.5" stroke={paper.pop.sun} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function Wordmark({ className = '', tagline = false }) {
  return (
    <span className="flex flex-col">
      <span className={`font-display text-lg font-semibold tracking-[0.06em] text-ink ${className}`}>PET</span>
      {tagline && <span className="text-[11px] leading-tight text-ink-subtle">Programming Education Tool</span>}
    </span>
  )
}
