import { useId } from 'react'
import { useCountUp } from '../../hooks/useCountUp.js'
import { RAMPS, rampColor } from '../../utils/colors.js'

// variant "orb": glowing circular gauge (hazard). variant "semi": semicircle gauge (mineral ratio).
// value is 0–1, or null for an empty gauge.
export default function Gauge({ value, variant = 'orb', caption, loading = false }) {
  const id = useId()
  const pct = useCountUp(Number.isFinite(value) ? value * 100 : null)
  const v = Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0
  const [r, g, b] = Number.isFinite(value) ? rampColor(RAMPS.hazard, v) : [120, 100, 95]
  const color = `rgb(${r | 0},${g | 0},${b | 0})`

  if (variant === 'semi') {
    return (
      <div className="gauge-semi">
        <svg viewBox="0 0 200 112" role="img" aria-label={Number.isFinite(value) ? `${Math.round(v * 100)} percent` : 'no data'}>
          <defs>
            <linearGradient id={id} x1="0" x2="1">
              <stop offset="0" stopColor="#f3d9cc" />
              <stop offset="0.6" stopColor="#ff7a3d" />
              <stop offset="1" stopColor="#c1440e" />
            </linearGradient>
          </defs>
          <path d="M16 100 A84 84 0 0 1 184 100" pathLength="1" className="gauge-track" />
          <path d="M16 100 A84 84 0 0 1 184 100" pathLength="1" stroke={`url(#${id})`} className="gauge-arc" style={{ strokeDasharray: `${v} 1` }} />
        </svg>
        <div className={`gauge-pill ${loading ? 'is-loading' : ''}`}>{pct === null ? '—' : `${Math.round(pct)}%`}</div>
      </div>
    )
  }

  return (
    <div className="gauge-orb">
      <svg viewBox="0 0 140 140" className="gauge-orb-ring" aria-hidden="true">
        <circle cx="70" cy="70" r="64" className="gauge-dash" />
        <circle cx="70" cy="70" r="56" className="gauge-track-round" />
        <circle cx="70" cy="70" r="56" pathLength="1" stroke={color} className="gauge-prog" style={{ strokeDasharray: `${v} 1` }} />
      </svg>
      <div
        className={`gauge-orb-core ${Number.isFinite(value) ? 'is-live' : ''}`}
        style={{ '--orb': color, '--orb-alpha': Number.isFinite(value) ? 0.45 + v * 0.45 : 0.12 }}
      >
        <strong>{pct === null ? '—' : `${Math.round(pct)}%`}</strong>
        {caption && <span>{caption}</span>}
      </div>
    </div>
  )
}
