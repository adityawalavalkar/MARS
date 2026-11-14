import { lazy, Suspense, useEffect, useState } from 'react'
import { useMarsStore } from '../store/useMarsStore.js'
import { useJez } from './store.js'
import JezeroMap from './JezeroMap.jsx'
import PovPanel from './PovPanel.jsx'
import { GalleryCard, LayerPanel, MissionBrief, RadiationPanel, RoutePanel, Targets } from './panels.jsx'
import { DEFAULT_REGION } from '../config.js'
import './jezero.css'

const Terrain3D = lazy(() => import('./Terrain3D.jsx'))

function Clock() {
  const [t0] = useState(Date.now()); const [now, setNow] = useState(Date.now()); useEffect(() => { const i = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(i) }, [])
  const s = Math.floor((now - t0) / 1000); return <span className="clock">SESSION T+{String(Math.floor(s / 3600)).padStart(2, '0')}:{String(Math.floor(s / 60) % 60).padStart(2, '0')}:{String(s % 60).padStart(2, '0')}</span>
}

export default function JezeroDashboard() {
  const ready = useJez((s) => s.ready); const init = useJez((s) => s.init); const view = useJez((s) => s.view); const setView = useJez((s) => s.setView); const spe = useJez((s) => s.spe)
  const setRegion = useMarsStore((s) => s.setRegion); const route = useJez((s) => s.route)
  useEffect(() => { init() }, [init])
  const red = route && !route.error && route.fast?.worst_status === 'red'
  return (
    <div className={`jz ${spe.active ? 'jz-spe' : ''}`}>
      <header className="jz-top">
        <div><b className="jz-title">MARS NAV</b> <span className="dim">JEZERO CRATER · 20 m CTX terrain</span></div>
        <div className="jz-seg"><button className={view === '2d' ? 'on' : ''} onClick={() => setView('2d')}>2D MAP</button><button className={view === '3d' ? 'on' : ''} onClick={() => setView('3d')}>3D TERRAIN</button></div>
        {spe.active && <span className="spe-chip">SIMULATED EVENT · ×{spe.multiplier.toFixed(1)}</span>}{red && <span className="spe-chip red">RETURN NOW</span>}
        <Clock /><button className="lnk" onClick={() => setRegion(DEFAULT_REGION)}>← Mars map</button>
      </header>
      {!ready ? <div className="terrain-empty">Loading Jezero data…</div> : (
        <main className="jz-main">
          <aside className="jz-col"><MissionBrief /><Targets /><LayerPanel /></aside>
          <section className="jz-center">{view === '2d' ? <JezeroMap /> : <Suspense fallback={<div className="terrain-empty">Loading 3D…</div>}><Terrain3D /></Suspense>}</section>
          <aside className="jz-col"><RoutePanel /><RadiationPanel /><PovPanel /></aside>
        </main>
      )}
      <GalleryCard />
    </div>
  )
}
