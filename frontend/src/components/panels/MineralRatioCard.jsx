import { useMarsStore } from '../../store/useMarsStore.js'
import GlassCard from '../ui/GlassCard.jsx'
import Gauge from '../ui/Gauge.jsx'
import Button from '../ui/Button.jsx'
import { pickColor } from '../../utils/palette.js'

export default function MineralRatioCard() {
  const mineral = useMarsStore((s) => s.data.mineral)
  const status = useMarsStore((s) => s.status.mineral)
  const route = useMarsStore((s) => s.data.route)
  const routeStatus = useMarsStore((s) => s.status.route)
  const setReportOpen = useMarsStore((s) => s.setReportOpen)

  return (
    <GlassCard title="Mineral catalog" status={status} hasData={!!mineral}>
      {Number.isFinite(mineral?.ratio) ? (
        <Gauge value={mineral.ratio} variant="semi" loading={status === 'loading'} />
      ) : (
        <p className="hint">CRISM detections · abundance ratio unavailable</p>
      )}
      <ul className="legend">
        {(mineral?.minerals || []).slice(0, 4).map((m, i) => (
          <li key={m.name}>
            <i style={{ background: pickColor(m, i) }} />
            {m.name}
            <b>{m.confidence}</b>
          </li>
        ))}
      </ul>
      <Button className="btn-block" disabled={!route} onClick={() => setReportOpen(true)}>
        {routeStatus === 'loading' ? 'Planning route…' : 'Generate Report'}
      </Button>
      {!route && routeStatus !== 'loading' && <p className="hint">Set a start and end point to enable the report.</p>}
    </GlassCard>
  )
}
