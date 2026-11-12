import { memo } from 'react'
import { palette } from '../../styles/palette'

const { canvas, chalk } = palette

function Backdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true" style={{ background: canvas }}>
      <svg className="absolute inset-0 h-full w-full">
        <defs>
          <pattern id="bd-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M24 0H0V24" fill="none" stroke={chalk} strokeOpacity="0.035" />
          </pattern>
          <filter id="bd-grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" />
            <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.5 0" />
          </filter>
        </defs>
        <rect width="100%" height="100%" fill="url(#bd-grid)" />
        <rect width="100%" height="100%" filter="url(#bd-grain)" opacity="0.05" />
      </svg>
    </div>
  )
}

export default memo(Backdrop)
