/**
 * Lightweight SVG chart components — no external library needed.
 */

// ── Sparkline (line chart) ────────────────────────────────────────────────────
export function Sparkline({ data = [], color = '#14b8a6', height = 40, width = 120 }) {
  if (!data.length) return null
  const max = Math.max(...data, 1)
  const min = Math.min(...data)
  const range = max - min || 1
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x},${y}`
  })
  const path = `M ${pts.join(' L ')}`
  const fill = `M ${pts[0]} L ${pts.join(' L ')} L ${width},${height} L 0,${height} Z`

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`sg-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fill} fill={`url(#sg-${color.replace('#','')})`} />
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Last point dot */}
      <circle
        cx={(data.length - 1) / (data.length - 1) * width}
        cy={height - ((data[data.length - 1] - min) / range) * (height - 4) - 2}
        r="3" fill={color}
      />
    </svg>
  )
}

// ── Radial progress ring ──────────────────────────────────────────────────────
export function RadialProgress({ value = 0, size = 64, stroke = 5, color = '#14b8a6', label }) {
  const r = (size - stroke * 2) / 2
  const circ = 2 * Math.PI * r
  const offset = circ - (value / 100) * circ

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <div style={{ fontSize: size * 0.22, fontWeight: 800, color: '#fff', lineHeight: 1 }}>{value}%</div>
        {label && <div style={{ fontSize: size * 0.14, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{label}</div>}
      </div>
    </div>
  )
}

// ── Bar chart (horizontal) ────────────────────────────────────────────────────
export function BarChart({ data = [], color = '#14b8a6' }) {
  // data: [{ label, value }]
  const max = Math.max(...data.map(d => d.value), 1)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {data.map((d, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', width: 80, textAlign: 'right', flexShrink: 0, fontFamily: 'monospace' }}>
            {d.label}
          </span>
          <div style={{ flex: 1, height: 8, background: 'rgba(255,255,255,0.06)', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 4,
              width: `${(d.value / max) * 100}%`,
              background: `linear-gradient(90deg, ${color}, ${color}99)`,
              transition: 'width 0.8s ease',
            }} />
          </div>
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', width: 28, fontFamily: 'monospace', flexShrink: 0 }}>
            {d.value}
          </span>
        </div>
      ))}
    </div>
  )
}
