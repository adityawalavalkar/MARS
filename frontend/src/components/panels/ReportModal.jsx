import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useMarsStore } from '../../store/useMarsStore.js'
import { useReport } from '../../hooks/useReport.js'
import Button from '../ui/Button.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import { fmt, fmtCoord } from '../../utils/format.js'

export default function ReportModal() {
  const report = useMarsStore((s) => s.data.report)
  const status = useMarsStore((s) => s.status.report)
  const route = useMarsStore((s) => s.data.route)
  const calculation = useMarsStore((s) => s.data.calculation)
  const profile = useMarsStore((s) => s.data.profile)
  const region = useMarsStore((s) => s.selectedRegion)
  const start = useMarsStore((s) => s.start)
  const end = useMarsStore((s) => s.end)
  const setReportOpen = useMarsStore((s) => s.setReportOpen)
  const [copied, setCopied] = useState(false)
  const retry = useReport(true)

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setReportOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setReportOpen])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify({ region: region.name, start, end, calculations: calculation, profile, route: route?.feature, backendReport: report }, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  const loading = status === 'loading' || (status === 'idle' && !report)

  return (
    <motion.div className="modal-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setReportOpen(false)}>
      <motion.div
        className="modal report-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Mission Report"
        initial={{ y: 30, scale: 0.97, opacity: 0 }}
        animate={{ y: 0, scale: 1, opacity: 1 }}
        exit={{ y: 20, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 260, damping: 26 }}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-head">
          <div>
            <span className="chip chip-muted">Mission Report</span>
            <h2>{region.name}</h2>
            <p className="hint">
              {fmtCoord(start?.lat, start?.lon)} → {fmtCoord(end?.lat, end?.lon)}
            </p>
          </div>
          <button className="icon-btn no-print" type="button" onClick={() => setReportOpen(false)} aria-label="Close">
            ×
          </button>
        </header>

        {calculation && !calculation.error ? (
          <>
            <div className="report-grid">
              <div><span>Surface geodesic</span><b>{fmt(calculation.surfaceDistanceKm, 2)} km</b></div>
              <div><span>3D terrain path</span><b>{fmt(calculation.terrainDistanceKm, 2)} km</b></div>
              <div><span>Travel duration</span><b>{fmt(calculation.travelHours, 2)} h · {fmt(calculation.travelDays, 2)} days</b></div>
              <div><span>Mars duration</span><b>{fmt(calculation.travelSols, 2)} sols</b></div>
              <div><span>Elevation minimum / maximum</span><b>{fmt(calculation.minElevationM, 0)} / {fmt(calculation.maxElevationM, 0)} m</b></div>
              <div><span>Total ascent / descent</span><b>{fmt(calculation.ascentM, 0)} / {fmt(calculation.descentM, 0)} m</b></div>
              <div><span>Max / mean slope</span><b>{fmt(calculation.maxSlopeDeg, 1)}° / {fmt(calculation.meanSlopeDeg, 1)}°</b></div>
              <div><span>Mean profile roughness</span><b>{fmt(calculation.meanRoughnessM, 1)} m</b></div>
              <div><span>Difficulty score</span><b>{fmt(calculation.difficultyScore, 1)} / 10</b></div>
              <div><span>Estimated propulsion energy</span><b>{fmt(calculation.propulsionKwh, 2)} kWh</b></div>
              <div><span>Mean propulsion power</span><b>{fmt(calculation.averagePowerW ?? (calculation.propulsionKwh * 1000 / calculation.travelHours), 1)} W</b></div>
              <div><span>Backend route feasibility</span><b>{route?.feasibility || '—'}</b></div>
              <div><span>High hazard exposure</span><b>{fmt(route?.hazardExposure?.high_pct, 1)}%</b></div>
              {calculation.impassableSegments.length > 0 && <div><span>Impassable profile segments (&gt;25°)</span><b>{calculation.impassableSegments.map((n) => n + 1).join(', ')}</b></div>}
              {profile?.elevations?.length > 1 && <div><span>Elevation profile · MOLA, {fmt(profile.sampleIntervalKm ?? 0.4630576672, 3)} km samples</span><svg viewBox="0 0 240 48" role="img" aria-label="Elevation profile chart" preserveAspectRatio="none"><polyline fill="none" stroke="#ff7a3d" strokeWidth="2" points={profile.elevations.map((e, i) => `${(i / (profile.elevations.length - 1)) * 238 + 1},${45 - ((e - profile.min) / (profile.max - profile.min || 1)) * 42}`).join(' ')} /></svg></div>}
            </div>
            <p className="hint">Model: Mars mean radius 3389.5 km; gravity 3.721 m/s²; Mars sol 24.6598 h. Speed {fmt(calculation.speedKmh, 3)} km/h (slope adjusted), rover mass {fmt(calculation.roverMassKg, 0)} kg, rolling coefficient {fmt(calculation.rollingCoefficient, 2)}. Energy excludes drivetrain efficiency and hotel loads. Slope segments above 25° are flagged impassable.</p>
            <h4>Summary</h4>
            <p className="report-summary">{report?.summary || (status === 'loading' ? 'Backend mission summary is loading.' : 'DEM-based traverse values above were calculated locally from the sampled MOLA elevation profile. Backend report summary was unavailable.')}</p>
            {report.generatedAt && <p className="hint">Generated {new Date(report.generatedAt).toLocaleString()}</p>}
            <footer className="modal-foot no-print">
              <Button variant="ghost" onClick={copy}>{copied ? 'Copied ✓' : 'Copy JSON'}</Button>
              <Button onClick={() => window.print()}>Download as PDF / Print</Button>
            </footer>
          </>
        ) : loading ? (
          <div className="report-grid">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i}><Skeleton width={90} height={10} /><Skeleton width={120} height={26} style={{ marginTop: 8 }} /></div>
            ))}
          </div>
        ) : (
          <>
            <EmptyState icon="warn" title="Report unavailable" hint="The backend did not return a mission report." />
            <footer className="modal-foot no-print"><Button onClick={retry}>Retry</Button></footer>
          </>
        )}
      </motion.div>
    </motion.div>
  )
}
