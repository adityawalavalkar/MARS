import { Component, lazy, Suspense } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMarsStore } from '../../store/useMarsStore.js'
import Skeleton from '../ui/Skeleton.jsx'
import Map2D from './Map2D.jsx'
import ViewToggle from './ViewToggle.jsx'
import LayerSwitcher from './LayerSwitcher.jsx'
import SettingsPanel from './SettingsPanel.jsx'
import { DEFAULT_REGION, REGIONAL_REGION } from '../../config.js'
import { fmt, fmtCoord } from '../../utils/format.js'

const Terrain3D = lazy(() => import('./Terrain3D.jsx'))

class RegionErrorBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error) { console.error(`Mars NAV terrain view failed for ${this.props.regionName}.`, error) }
  render() {
    if (this.state.failed) return <div className="terrain-empty"><strong>Terrain view unavailable</strong><span>{this.props.regionName}: the DEM or texture failed to load. Return to the Mars map and retry.</span></div>
    return this.props.children
  }
}

function RouteBar() {
  const region = useMarsStore((s) => s.selectedRegion)
  const viewMode = useMarsStore((s) => s.viewMode)
  const start = useMarsStore((s) => s.start)
  const end = useMarsStore((s) => s.end)
  const route = useMarsStore((s) => s.data.route)
  const status = useMarsStore((s) => s.status.route)
  const calculation = useMarsStore((s) => s.data.calculation)
  const profile = useMarsStore((s) => s.data.profile)
  const calculationRequested = useMarsStore((s) => s.calculationRequested)
  const requestCalculation = useMarsStore((s) => s.requestCalculation)
  const setReportOpen = useMarsStore((s) => s.setReportOpen)
  const clearRoute = useMarsStore((s) => s.clearRoute)

  if (region.id !== 'jezero') {
    return <div className="route-bar glass"><span className="route-hint">Regional overview · select <b className="c-start">Jezero Crater</b> to plan a detailed traverse</span></div>
  }
  if (viewMode === '3d' && !route && !calculation?.error && status !== 'error') return null

  return (
    <div className="route-bar glass">
      {!start && viewMode !== '3d' && <span className="route-hint">Click the map to set a <b className="c-start">START</b> point</span>}
      {start && !end && viewMode !== '3d' && <span className="route-hint">Start {fmtCoord(start.lat, start.lon)} — click to set the <b className="c-end">END</b> point</span>}
      {start && end && status === 'loading' && <Skeleton width={220} height={18} />}
      {start && end && (status === 'error' || route?.error) && <span className="route-hint err">{route?.detail || 'Route unavailable — the backend returned no route'}</span>}
      {calculation?.error && <span className="route-hint err">Profile calculation failed: {calculation.detail}</span>}
      {route && !route.error && (
        <div className="route-stats">
          <div><span>Surface distance</span><b>{fmt(calculation?.surfaceDistanceKm, 2)} km</b></div>
          <div><span>3D terrain distance</span><b>{fmt(calculation?.terrainDistanceKm, 2)} km</b></div>
          <div><span>Travel time</span><b>{fmt(calculation?.travelHours, 2)} h · {fmt(calculation?.travelDays, 2)} Earth days · {fmt(calculation?.travelSols, 2)} sols</b></div>
          <div><span>Climb / descent</span><b>{fmt(calculation?.ascentM, 0)} / {fmt(calculation?.descentM, 0)} m</b></div>
          <div><span>Max / mean slope</span><b>{fmt(calculation?.maxSlopeDeg, 1)}° / {fmt(calculation?.meanSlopeDeg, 1)}°</b></div>
          <div><span>Elevation min / max</span><b>{fmt(calculation?.minElevationM, 0)} / {fmt(calculation?.maxElevationM, 0)} m</b></div>
          <div><span>Mean roughness</span><b>{fmt(calculation?.meanRoughnessM, 1)} m</b></div>
          <div><span>Difficulty score</span><b>{fmt(calculation?.difficultyScore, 1)} / 10</b></div>
          <div><span>Estimated propulsion energy*</span><b>{fmt(calculation?.propulsionKwh, 2)} kWh</b></div>
          <div><span>Mean propulsion power*</span><b>{fmt(calculation?.averagePowerW ?? (calculation?.propulsionKwh * 1000 / calculation?.travelHours), 1)} W</b></div>
          {calculation?.impassableSegments?.length > 0 && <div className="err"><span>Impassable profile segments (&gt;25°)</span><b>{calculation.impassableSegments.map((n) => n + 1).join(', ')}</b></div>}
          <div><span>Backend route feasibility</span><b>{route.feasibility || '—'}</b></div>
          {profile?.elevations?.length > 1 && <div><span>Elevation profile · MOLA, {fmt(profile.sampleIntervalKm ?? 0.4630576672, 3)} km samples</span><svg viewBox="0 0 240 48" role="img" aria-label="Elevation profile chart" preserveAspectRatio="none"><polyline fill="none" stroke="#ff7a3d" strokeWidth="2" points={profile.elevations.map((e, i) => `${(i / (profile.elevations.length - 1)) * 238 + 1},${45 - ((e - profile.min) / (profile.max - profile.min || 1)) * 42}`).join(' ')} /></svg></div>}
          {route.evaDurationCheck && <div><span>EVA duration</span><b>{route.evaDurationCheck.status}: {route.evaDurationCheck.value} / {route.evaDurationCheck.threshold}</b></div>}
          <div className="hint">Difficulty / 10 = 0.5×min(mean slope / 25°, 1) + 0.3×min(5-sample roughness / 10 m, 1) + 0.2×min(total elevation change / distance / 100 m·km⁻¹, 1). Slopes &gt;25° are flagged. Speed uses {fmt(calculation?.speedKmh, 3)} km/h reduced linearly to 10% by 40.5°. Energy assumes 1025 kg and rolling coefficient 0.10; excludes drivetrain and hotel loads. Mean power is ideal propulsion energy divided by travel time.</div>
        </div>
      )}
      {viewMode !== '3d' && start && end && (!calculationRequested || status === 'error') && status !== 'loading' && <button type="button" className="link-btn" onClick={() => requestCalculation(true)}>{status === 'error' ? 'Retry calculation' : 'Calculate traverse'}</button>}
      {calculationRequested && status === 'loading' && <span className="route-hint">Sampling the Jezero DEM and calculating…</span>}
      {route && calculation && !calculation.error && <button type="button" className="link-btn" onClick={() => setReportOpen(true)}>Mission report</button>}
      {start && viewMode !== '3d' && (
        <button type="button" className="link-btn" onClick={clearRoute}>
          Clear
        </button>
      )}
    </div>
  )
}

function TerrainRouteControls() {
  const start = useMarsStore((s) => s.start)
  const end = useMarsStore((s) => s.end)
  const status = useMarsStore((s) => s.status.route)
  const route = useMarsStore((s) => s.data.route)
  const calculationRequested = useMarsStore((s) => s.calculationRequested)
  const requestCalculation = useMarsStore((s) => s.requestCalculation)
  const clearRoute = useMarsStore((s) => s.clearRoute)
  const busy = status === 'loading'
  const canCalculate = Boolean(start && end) && !busy && (!calculationRequested || status === 'error' || route?.error)

  return (
    <section className="terrain-route-controls glass" aria-label="3D traverse planner">
      <strong>3D traverse planner</strong>
      <p>{!start ? 'Click the terrain to place your START point.' : !end ? 'START set. Click the terrain again to place your END point.' : busy ? 'Calculating the Jezero traverse…' : 'Both points are set. Calculate a route across the terrain.'}</p>
      {(start || end) && <div className="terrain-route-points">
        <span>START<b>{start ? fmtCoord(start.lat, start.lon) : 'Not set'}</b></span>
        <span>END<b>{end ? fmtCoord(end.lat, end.lon) : 'Not set'}</b></span>
      </div>}
      <div className="terrain-route-actions">
        {canCalculate && <button type="button" className="btn btn-primary" onClick={() => requestCalculation(true)}>{status === 'error' || route?.error ? 'Retry route' : 'Calculate traverse'}</button>}
        {busy && <button type="button" className="btn btn-primary" disabled>Calculating…</button>}
        {(start || end || route) && <button type="button" className="link-btn" onClick={clearRoute}>Clear points</button>}
      </div>
    </section>
  )
}

function PlannerControls() {
  const mode = useMarsStore((s) => s.missionMode)
  const safetyWeight = useMarsStore((s) => s.safetyWeight)
  const crewSize = useMarsStore((s) => s.crewSize)
  const roverSpeedKmh = useMarsStore((s) => s.roverSpeedKmh)
  const setOptions = useMarsStore((s) => s.setMissionOptions)
  return (
    <div className="planner-controls glass">
      <label>Mode <select value={mode} onChange={(e) => setOptions({ missionMode: e.target.value })}><option value="rover">Rover</option><option value="crewed">Crewed rover</option><option value="eva">EVA</option></select></label>
      <label className="safety-control">Safety weight <input type="range" min="0.5" max="3" step="0.1" value={safetyWeight} onChange={(e) => setOptions({ safetyWeight: Number(e.target.value) })} /> <b>{safetyWeight.toFixed(1)}</b></label>
      {mode !== 'rover' && <label>Crew <select value={crewSize} onChange={(e) => setOptions({ crewSize: Number(e.target.value) })}>{[1,2,3,4,5,6].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>}
      <label>Rover speed <input type="number" min="0.005" max="0.152" step="0.001" value={roverSpeedKmh} onChange={(e) => setOptions({ roverSpeedKmh: Math.max(0.005, Math.min(0.152, Number(e.target.value) || 0.042)) })} /> km/h</label>
    </div>
  )
}

export default function CenterView() {
  const viewMode = useMarsStore((s) => s.viewMode)
  const activeTab = useMarsStore((s) => s.activeTab)
  const region = useMarsStore((s) => s.selectedRegion)
  const setRegion = useMarsStore((s) => s.setRegion)
  const setViewMode = useMarsStore((s) => s.setViewMode)
  const settingsOpen = activeTab === 'settings'
  const key = settingsOpen ? 'settings' : viewMode

  return (
    <div className="center-view">
      <header className="zone-label">
        <span className="chip chip-light">Expedition</span>
        <h1>{region.zone}</h1>
        <div className="zone-mode" role="group" aria-label="Exploration scale">
          <button type="button" className={region.id === 'global' ? 'on' : ''} onClick={() => { setRegion(DEFAULT_REGION); setViewMode('2d') }}>Mars map</button>
          <button type="button" className={region.id === 'regional' ? 'on' : ''} onClick={() => { setRegion(REGIONAL_REGION); setViewMode('2d') }}>Regional DEM</button>
          {region.id !== 'global' && region.id !== 'regional' && <button type="button" onClick={() => { setRegion(DEFAULT_REGION); setViewMode('2d') }}>Back to Mars map</button>}
          {region.id === 'jezero' && <button type="button" className="on" onClick={() => setViewMode('3d')}>Jezero 3D</button>}
        </div>
      </header>
      <div className="stage">
        <AnimatePresence mode="wait">
          <motion.div key={key} className="stage-inner" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
            {settingsOpen ? (
              <SettingsPanel />
            ) : viewMode === '3d' ? (
              <Suspense fallback={<div className="terrain-empty"><Skeleton width="60%" height={26} /></div>}>
                <RegionErrorBoundary key={region.id} regionName={region.name}><Terrain3D /></RegionErrorBoundary>
              </Suspense>
            ) : (
              <Map2D />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      {!settingsOpen && viewMode === '3d' && region.id === 'jezero' && <TerrainRouteControls />}
      {activeTab === 'planner' && region.id === 'jezero' && <PlannerControls />}
      {!settingsOpen && viewMode === '2d' && region.id === 'jezero' && <LayerSwitcher />}
      {!settingsOpen && <RouteBar />}
      {region.terrainAvailable && <ViewToggle />}
    </div>
  )
}
