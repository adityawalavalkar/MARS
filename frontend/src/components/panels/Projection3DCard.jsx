import { useMemo } from 'react'
import { useMarsStore } from '../../store/useMarsStore.js'
import GlassCard from '../ui/GlassCard.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import { sampleGrid } from '../../utils/grid.js'

const ROWS = 24
const COLS = 30
const W = 260
const H = 130

// Hidden-line isometric wireframe of the elevation grid, drawn as SVG. Labels come from the data
// (backend `features`, plus the highest/lowest sampled points).
export default function Projection3DCard() {
  const elevation = useMarsStore((s) => s.data.elevation)
  const status = useMarsStore((s) => s.status.elevation)

  const model = useMemo(() => {
    if (!elevation) return null
    const g = elevation.grid
    const range = Math.max(1e-6, g.max - g.min)
    const pts = []
    let hi = { z: -Infinity }
    let lo = { z: Infinity }
    for (let r = 0; r < ROWS; r++) {
      const row = []
      for (let c = 0; c < COLS; c++) {
        const u = c / (COLS - 1)
        const v = 1 - r / (ROWS - 1)
        const e = sampleGrid(g, u, v)
        const z = Number.isFinite(e) ? (e - g.min) / range : 0
        const x = 14 + c * ((W - 60) / (COLS - 1)) + r * 1.9
        const y = 36 + r * 3.1 - z * 34
        row.push([x, y])
        if (z > hi.z) hi = { z, x, y, e }
        if (z < lo.z) lo = { z, x, y, e }
      }
      pts.push(row)
    }
    const b = g.bounds
    const features = (elevation.features || []).slice(0, 3).map((f) => {
      const u = (f.lon - b.west) / (b.east - b.west)
      const v = (f.lat - b.south) / (b.north - b.south)
      const c = Math.round(Math.min(1, Math.max(0, u)) * (COLS - 1))
      const r = Math.round((1 - Math.min(1, Math.max(0, v))) * (ROWS - 1))
      return { label: f.label, x: pts[r][c][0], y: pts[r][c][1] }
    })
    return { pts, labels: [{ label: `Peak ${Math.round(hi.e)} m`, x: hi.x, y: hi.y }, { label: `Low ${Math.round(lo.e)} m`, x: lo.x, y: lo.y }, ...features] }
  }, [elevation])

  return (
    <GlassCard title="3D projection" status={status} hasData={!!model}>
      {model ? (
        <svg className="wire" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Wireframe elevation surface">
          {model.pts.map((row, r) => {
            const line = row.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
            const last = row[row.length - 1]
            const fill = `M${row[0][0].toFixed(1)},${H} L${line.replaceAll(' ', ' L')} L${last[0].toFixed(1)},${H} Z`
            return (
              <g key={r}>
                <path d={fill} className="wire-fill" />
                <polyline points={line} className="wire-line" style={{ opacity: 0.35 + (r / ROWS) * 0.65 }} />
              </g>
            )
          })}
          {model.labels.map((l) => (
            <g key={l.label} className="wire-label">
              <circle cx={l.x} cy={l.y} r="2.4" />
              <text x={l.x + 5} y={l.y - 5}>
                {l.label}
              </text>
            </g>
          ))}
        </svg>
      ) : status === 'loading' ? (
        <Skeleton height={130} radius={12} />
      ) : (
        <EmptyState compact title="No surface model" hint="Waiting for elevation data" />
      )}
    </GlassCard>
  )
}
