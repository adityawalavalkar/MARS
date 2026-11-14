import { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMarsStore } from '../../store/useMarsStore.js'
import GlassCard from '../ui/GlassCard.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import { fmt } from '../../utils/format.js'
import { pickColor } from '../../utils/palette.js'


const CW = 260
const CH = 96
const confidenceWeight = { HIGH: 3, MEDIUM: 2, LOW: 1 }

function ProfileChart({ profile }) {
  const [hover, setHover] = useState(null)
  const svg = useRef(null)
  const { distancesKm: d, elevations: e, min, max } = profile
  const dMax = d[d.length - 1] || 1
  const range = Math.max(1e-6, max - min)
  const xs = d.map((x) => (x / dMax) * CW)
  const ys = e.map((y) => CH - 6 - ((y - min) / range) * (CH - 18))
  const line = xs.map((x, i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ')
  const idx = hover ?? e.length - 1

  const onMove = (ev) => {
    const r = svg.current.getBoundingClientRect()
    const x = ((ev.clientX - r.left) / r.width) * CW
    let best = 0
    for (let i = 1; i < xs.length; i++) if (Math.abs(xs[i] - x) < Math.abs(xs[best] - x)) best = i
    setHover(best)
  }

  return (
    <>
      <svg ref={svg} className="profile" viewBox={`0 0 ${CW} ${CH}`} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="profile-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ff7a3d" stopOpacity="0.55" />
            <stop offset="1" stopColor="#ff7a3d" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${line} L${CW},${CH} L0,${CH} Z`} fill="url(#profile-fill)" />
        <path d={line} className="profile-line" />
        <line x1={xs[idx]} x2={xs[idx]} y1="0" y2={CH} className="profile-cursor" />
        <circle cx={xs[idx]} cy={ys[idx]} r="3.5" className="profile-dot" />
      </svg>
      <div className="mmc">
        <div><span>Min</span><b>{fmt(min)} m</b></div>
        <div><span>Current · {fmt(d[idx], 1)} km</span><b>{fmt(e[idx])} m</b></div>
        <div><span>Max</span><b>{fmt(max)} m</b></div>
      </div>
    </>
  )
}

export default function ViewCard() {
  const [tab, setTab] = useState('structure')
  const profile = useMarsStore((s) => s.data.profile)
  const profileStatus = useMarsStore((s) => s.status.profile)
  const routeStatus = useMarsStore((s) => s.status.route)
  const comp = useMarsStore((s) => s.data.composition)
  const compStatus = useMarsStore((s) => s.status.composition)
  const status = tab === 'structure' ? profileStatus : compStatus
  const hasData = tab === 'structure' ? !!profile : !!comp

  const tabs = (
    <div className="seg seg-mini" role="tablist">
      {['structure', 'composition'].map((t) => (
        <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>
          {t === 'structure' ? 'Structure' : 'Composition'}
        </button>
      ))}
    </div>
  )

  return (
    <GlassCard title="View" status={status} hasData={hasData} right={tabs}>
      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.18 }}>
          {tab === 'structure' ? (
            profile ? (
              <ProfileChart profile={profile} />
            ) : profileStatus === 'loading' || routeStatus === 'loading' ? (
              <Skeleton height={96} radius={12} />
            ) : (
              <EmptyState compact title="No elevation profile" hint="Plan a route to see terrain along the path" />
            )
          ) : comp ? (
              <div>
              <div className="stack-bar">
                {comp.components.map((c, i) => (
                  <i key={c.name} style={{ flex: confidenceWeight[c.confidence] || 1, background: pickColor(c, i) }} title={`${c.name} · ${c.confidence} confidence`} />
                ))}
              </div>
              <ul className="legend legend-col">
                {comp.components.map((c, i) => (
                  <li key={c.name}>
                    <i style={{ background: pickColor(c, i) }} />
                    {c.name}
                      <b>{c.confidence}</b>
                  </li>
                ))}
              </ul>
                <p className="hint">CRISM detection confidence, not mineral abundance.</p>
            </div>
          ) : compStatus === 'loading' ? (
            <Skeleton height={96} radius={12} />
          ) : (
            <EmptyState compact title="No composition data" />
          )}
        </motion.div>
      </AnimatePresence>
    </GlassCard>
  )
}
