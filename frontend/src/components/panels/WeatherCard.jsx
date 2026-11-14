import { useMarsStore } from '../../store/useMarsStore.js'
import GlassCard from '../ui/GlassCard.jsx'
import Stat from '../ui/Stat.jsx'
import { cToF } from '../../utils/format.js'

export default function WeatherCard() {
  const weather = useMarsStore((s) => s.data.weather)
  const status = useMarsStore((s) => s.status.weather)
  const unit = useMarsStore((s) => s.settings.tempUnit)
  const updateSettings = useMarsStore((s) => s.updateSettings)
  const loading = status === 'loading'
  const temp = Number.isFinite(weather?.temperatureC) ? (unit === 'C' ? weather.temperatureC : cToF(weather.temperatureC)) : null

  const toggle = (
    <div className="seg seg-mini" role="group" aria-label="Temperature unit">
      {['C', 'F'].map((u) => (
        <button key={u} type="button" className={unit === u ? 'on' : ''} onClick={() => updateSettings({ tempUnit: u })}>
          °{u}
        </button>
      ))}
    </div>
  )

  return (
    <GlassCard title="Weather" status={status} hasData={!!weather} right={toggle}>
      {weather?.error ? <p className="hint err">{weather.detail}</p> : <><div className="stat-row">
        <Stat label="Wind speed" value={weather?.windSpeedKmh} unit="km/h" digits={0} loading={loading} />
        <span className="stat-divider" />
        <Stat label="Day temperature" value={temp} unit={`°${unit}`} digits={0} loading={loading} />
      </div>
      <p className="hint">{weather?.source || 'Modeled estimate (MEDA-based), Jezero-only'} · Local solar time {Number.isFinite(weather?.localSolarTimeHours) ? `${Math.floor(weather.localSolarTimeHours).toString().padStart(2, '0')}:${Math.round((weather.localSolarTimeHours % 1) * 60).toString().padStart(2, '0')}` : '—'}</p></>}
    </GlassCard>
  )
}
