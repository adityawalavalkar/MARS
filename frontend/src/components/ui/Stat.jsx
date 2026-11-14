import { useCountUp } from '../../hooks/useCountUp.js'
import Skeleton from './Skeleton.jsx'

// Large light numeral + small unit + caption. Counts up when the value changes; "—" when there is no value.
export default function Stat({ label, value, unit, digits = 0, loading = false }) {
  const shown = useCountUp(value)
  return (
    <div className="stat">
      <div className="stat-line">
        {loading && !Number.isFinite(value) ? (
          <Skeleton width={70} height={34} />
        ) : (
          <span className="stat-value">{shown === null ? '—' : shown.toFixed(digits)}</span>
        )}
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      <span className="stat-label">{label}</span>
    </div>
  )
}
