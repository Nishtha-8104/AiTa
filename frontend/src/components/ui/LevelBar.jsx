import { BAND_STYLE } from '../learning/labels'

const SEGMENTS = 10

export default function LevelBar({ value, band = 'unseen', className = '' }) {
  const style = BAND_STYLE[band] || BAND_STYLE.unseen
  const filled = Math.round(Math.max(0, Math.min(1, value)) * SEGMENTS)
  return (
    <div className={`grid grid-cols-10 gap-[4px] ${className}`} aria-hidden="true">
      {Array.from({ length: SEGMENTS }, (_, i) => (
        <span key={i} className={`h-3.5 rounded-[3px] ${i < filled ? style.bar : 'bg-white/[0.06]'}`} />
      ))}
    </div>
  )
}
