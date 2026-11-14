// Transparent first-order rover estimates from a real DEM-sampled profile.
// Assumptions are intentionally explicit: spherical Mars, 1025 kg rover,
// 0.10 rolling coefficient, and 0.042 km/h reference speed.
export const MARS = Object.freeze({ radiusKm: 3389.5, gravityMps2: 3.721, solHours: 24.6598 })
const radians = (d) => d * Math.PI / 180

export function surfaceDistanceKm(a, b, radiusKm = MARS.radiusKm) {
  const dLat = radians(b.lat - a.lat)
  const dLon = radians(b.lon - a.lon)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(radians(a.lat)) * Math.cos(radians(b.lat)) * Math.sin(dLon / 2) ** 2
  return 2 * radiusKm * Math.asin(Math.sqrt(Math.min(1, h)))
}

const mean = (xs) => xs.reduce((s, x) => s + x, 0) / (xs.length || 1)
const stddev = (xs) => Math.sqrt(mean(xs.map((x) => (x - mean(xs)) ** 2)))

export function calculateMarsTraverse({ start, end, profile, speedKmh = 0.042, roverMassKg = 1025, rollingCoefficient = 0.1 }) {
  if (!start || !end || !Array.isArray(profile?.distancesKm) || !Array.isArray(profile?.elevations) || profile.distancesKm.length < 2 || profile.distancesKm.length !== profile.elevations.length) {
    throw new TypeError('A valid DEM-sampled elevation profile and two endpoints are required.')
  }
  const { distancesKm: d, elevations: z } = profile
  if ([...d, ...z].some((n) => !Number.isFinite(n)) || speedKmh <= 0 || roverMassKg <= 0 || rollingCoefficient < 0) throw new RangeError('Profile and rover parameters must be finite and physically valid.')
  const surfaceKm = surfaceDistanceKm(start, end)
  let terrainKm = 0, ascentM = 0, descentM = 0, elapsedH = 0, energyJ = 0
  const slopes = []
  const impassableSegments = []
  for (let i = 1; i < d.length; i++) {
    const horizontalKm = Math.max(0, d[i] - d[i - 1])
    const dh = z[i] - z[i - 1]
    const slopeDeg = Math.atan2(Math.abs(dh), horizontalKm * 1000) * 180 / Math.PI
    slopes.push(slopeDeg)
    if (dh > 0) ascentM += dh; else descentM += -dh
    const segmentKm = Math.hypot(horizontalKm, dh / 1000)
    terrainKm += segmentKm
    const speedFactor = Math.max(0.1, 1 - slopeDeg / 45)
    elapsedH += segmentKm / (speedKmh * speedFactor)
    energyJ += roverMassKg * MARS.gravityMps2 * (Math.max(0, dh) + rollingCoefficient * segmentKm * 1000)
    if (slopeDeg > 25) impassableSegments.push(i - 1)
  }
  const roughness = z.map((_, i) => stddev(z.slice(Math.max(0, i - 2), Math.min(z.length, i + 3))))
  const meanRoughnessM = mean(roughness)
  const meanSlopeDeg = mean(slopes)
  const maxSlopeDeg = Math.max(...slopes)
  // Score (0–10): 50% normalized slope, 30% 10 m local roughness, 20% elevation change/km.
  const changePerKm = (ascentM + descentM) / Math.max(terrainKm, 0.001)
  const difficultyScore = Math.min(10, 10 * (0.5 * Math.min(meanSlopeDeg / 25, 1) + 0.3 * Math.min(meanRoughnessM / 10, 1) + 0.2 * Math.min(changePerKm / 100, 1)))
  const propulsionKwh = energyJ / 3_600_000
  return {
    surfaceDistanceKm: surfaceKm, terrainDistanceKm: terrainKm,
    minElevationM: Math.min(...z), maxElevationM: Math.max(...z), ascentM, descentM,
    maxSlopeDeg, meanSlopeDeg, meanRoughnessM, difficultyScore, impassableSegments,
    travelHours: elapsedH, travelDays: elapsedH / 24, travelSols: elapsedH / MARS.solHours,
    propulsionKwh, averagePowerW: elapsedH > 0 ? propulsionKwh * 1000 / elapsedH : 0,
    marsGravityMps2: MARS.gravityMps2, speedKmh, roverMassKg, rollingCoefficient,
  }
}
