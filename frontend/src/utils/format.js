export const cToF = (c) => (c * 9) / 5 + 32

export function fmt(n, digits = 0) {
  return Number.isFinite(n) ? n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—'
}

export function fmtDuration(hours) {
  if (!Number.isFinite(hours)) return '—'
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  return m === 60 ? `${h + 1}h 00m` : `${h}h ${String(m).padStart(2, '0')}m`
}

export function fmtCoord(lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return '—'
  return `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? 'N' : 'S'}  ${Math.abs(lon).toFixed(4)}°${lon >= 0 ? 'E' : 'W'}`
}

export function hazardLevel(score) {
  if (!Number.isFinite(score)) return null
  return score < 0.33 ? 'Low' : score < 0.66 ? 'Medium' : 'High'
}
