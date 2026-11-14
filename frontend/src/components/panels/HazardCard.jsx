import { useMemo } from 'react'
import { useMarsStore } from '../../store/useMarsStore.js'
import GlassCard from '../ui/GlassCard.jsx'
import Gauge from '../ui/Gauge.jsx'
import { hazardLevel } from '../../utils/format.js'

// Score priority: backend summary.score → mean of the hazard grid (derived from backend data only).
export default function HazardCard() {
  const hazard = useMarsStore((s) => s.data.hazard)
  const status = useMarsStore((s) => s.status.hazard)

  const { score, level } = useMemo(() => {
    if (!hazard) return { score: null, level: null }
    let s = hazard.summary.score
    if (!Number.isFinite(s)) {
      let sum = 0
      let n = 0
      for (const v of hazard.grid.values) {
        if (Number.isFinite(v)) {
          sum += v
          n++
        }
      }
      s = n ? sum / n : null
    }
    return { score: s, level: hazard.summary.level || hazardLevel(s) }
  }, [hazard])

  const warn = level === 'High' || level === 'Medium'

  return (
    <GlassCard
      title="Terrain hazard"
      status={status}
      hasData={!!hazard}
      right={
        <span className={`warn-icon ${level === 'High' ? 'is-high' : ''} ${warn ? 'is-on' : ''}`} title={level ? `${level} hazard` : 'No data'}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 3 2 21h20L12 3Z" />
            <path d="M12 10v5M12 18v.1" />
          </svg>
        </span>
      }
    >
      <div className="hazard-body">
        <Gauge value={score} variant="orb" caption="hazard" loading={status === 'loading'} />
        <div className="hazard-meta">
          <span className="stat-label">Level</span>
          <strong className={`level level-${(level || 'none').toLowerCase()}`}>{level || '—'}</strong>
          {Number.isFinite(hazard?.summary.confidence) && <span className="stat-label">Confidence {Math.round(hazard.summary.confidence * 100)}%</span>}
        </div>
      </div>
    </GlassCard>
  )
}
