import { useMarsStore } from '../../store/useMarsStore.js'
import GlassCard from '../ui/GlassCard.jsx'
import Stat from '../ui/Stat.jsx'

export default function RadiationCard() {
  const radiation = useMarsStore((s) => s.data.radiation)
  const status = useMarsStore((s) => s.status.radiation)
  const loading = status === 'loading'
  return (
    <GlassCard title="Radiation" status={status} hasData={!!radiation}>
      {radiation?.error ? <p className="hint err">{radiation.detail}</p> : <><div className="stat-row">
        <Stat label="Dose rate" value={radiation?.doseRateUSvH} unit="µSv/h" digits={2} loading={loading} />
      </div>
      <p className="hint">{radiation?.source || 'Modeled Gale-to-Jezero transfer estimate (MSL RAD based), Jezero-only'}</p></>}
    </GlassCard>
  )
}
