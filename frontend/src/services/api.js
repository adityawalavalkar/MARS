// ─────────────────────────────────────────────────────────────────────────────
// MARS NAV – the ONE data layer. Every function calls the backend and returns the
// normalised payload, or `null` on network error / timeout / empty / malformed response.
// There is no mock data anywhere: null means the UI shows its empty or error state.
// Full request/response shapes: see FRONTEND_API_CONTRACT.md
// ─────────────────────────────────────────────────────────────────────────────
import { ELEVATION_RESOLUTION } from '../config.js'
import { normalizeGrid } from '../utils/grid.js'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

// All endpoint paths live here. Edit these when the backend URLs are final.
export const endpoints = {
  weather: { method: 'GET', path: '/api/weather' },
  radiation: { method: 'GET', path: '/api/dashboard/radiation' },
  hazardGrid: { method: 'GET', path: '/api/hazard-grid' },
  elevationGrid: { method: 'GET', path: '/api/elevation-grid' },
  elevationProfile: { method: 'POST', path: '/api/elevation-profile' },
  composition: { method: 'GET', path: '/api/composition' },
  mineralRatio: { method: 'GET', path: '/api/mineral-ratio' },
  route: { method: 'POST', path: '/api/route' },
  missionReport: { method: 'POST', path: '/api/mission-report' },
  regionalOverview: { method: 'GET', path: '/api/terrain/regional' },
  regionalGrid: { method: 'GET', path: '/api/terrain/regional/grid' },
  regionalFeatures: { method: 'GET', path: '/api/terrain/regional/features' },
}

const TIMEOUT_MS = 8000
const RETRIES = 2
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const isNum = (v) => typeof v === 'number' && Number.isFinite(v)
const numOrNull = (v) => (isNum(v) ? v : null)

async function request(endpoint, { query, body } = {}) {
  const qs = query
    ? '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null)).toString()
    : ''
  const url = `${API_BASE_URL}${endpoint.path}${qs}`
  for (let attempt = 0; attempt <= RETRIES; attempt++) {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
    try {
      const res = await fetch(url, {
        method: endpoint.method,
        headers: body ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
      })
      if (res.status >= 400 && res.status < 500) {
        const payload = await res.json().catch(() => ({}))
        return { error: true, status: res.status, detail: payload.detail || `Request failed (${res.status})` }
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      return json && typeof json === 'object' ? json : null
    } catch {
      if (attempt === RETRIES) return null
      await wait(400 * 2 ** attempt)
    } finally {
      clearTimeout(timer)
    }
  }
  return null
}

const regionQuery = (region) => ({
  regionId: region?.id,
  lat: region?.center?.lat,
  lon: region?.center?.lon,
})

const boundsQuery = (b) => ({ south: b.south, west: b.west, north: b.north, east: b.east })

const normCatalog = (list) =>
  Array.isArray(list)
    ? list
        .filter((c) => c && typeof c.name === 'string' && typeof c.confidence === 'string')
        .map((c) => ({ name: c.name, confidence: c.confidence, color: typeof c.color === 'string' ? c.color : null }))
    : []

/** GET weather → { windSpeedKmh, temperatureC } */
export async function getWeather(region) {
  const clock = marsSolarClock(region?.center?.lon ?? 77.4508)
  const r = await request(endpoints.weather, { query: { ...regionQuery(region), ...clock } })
  if (r?.error) return r
  if (!r || (!isNum(r.windSpeedKmh) && !isNum(r.temperatureC))) return null
  return { windSpeedKmh: numOrNull(r.windSpeedKmh), temperatureC: numOrNull(r.temperatureC), localSolarTimeHours: r.localSolarTimeHours, solarLongitudeLs: r.solarLongitudeLs, source: r.source }
}

// NASA GISS Mars24 algorithm (AM2000): computes current Ls and Jezero LTST from
// the system clock, accounting for east longitude and the Martian equation of time.
function marsSolarClock(eastLongitudeDeg) {
  const jdUT = 2440587.5 + Date.now() / 86400000
  const jdTT = jdUT + 69.184 / 86400
  const dt = jdTT - 2451545.0
  const rad = Math.PI / 180
  const mod = (n, d) => ((n % d) + d) % d
  const M = mod(19.3871 + 0.52402073 * dt, 360)
  const alphaFms = mod(270.3871 + 0.524038496 * dt, 360)
  const amps = [0.0071, 0.0057, 0.0039, 0.0037, 0.0021, 0.002, 0.0018]
  const periods = [2.2353, 2.7543, 1.1177, 15.7866, 2.1354, 2.4694, 32.8493]
  const phases = [49.409, 168.173, 191.837, 21.736, 15.704, 95.528, 49.095]
  const pbs = amps.reduce((sum, a, i) => sum + a * Math.cos(rad * (0.985626 * dt / periods[i] + phases[i])), 0)
  const equationCenter = (10.691 + 3e-7 * dt) * Math.sin(rad * M) + 0.623 * Math.sin(rad * 2 * M) + 0.05 * Math.sin(rad * 3 * M) + 0.005 * Math.sin(rad * 4 * M) + 0.0005 * Math.sin(rad * 5 * M) + pbs
  const ls = mod(alphaFms + equationCenter, 360)
  const eotDeg = 2.861 * Math.sin(rad * 2 * ls) - 0.071 * Math.sin(rad * 4 * ls) + 0.002 * Math.sin(rad * 6 * ls) - equationCenter
  const mst = mod(24 * (((jdTT - 2451549.5) / 1.0274912517) + 44796 - 0.0009626), 24)
  const localSolarTime = mod(mst + eastLongitudeDeg / 15 + eotDeg / 15, 24)
  return { sol_time_hours: localSolarTime, solar_longitude_ls: ls, longitude_deg: eastLongitudeDeg }
}

/** GET radiation → { doseRateUSvH, grid? } */
export async function getRadiation(region) {
  const r = await request(endpoints.radiation, { query: regionQuery(region) })
  if (r?.error) return r
  if (!r || !isNum(r.doseRateUSvH)) return null
  return { doseRateUSvH: r.doseRateUSvH, source: r.source, grid: normalizeGrid(r.grid, region?.bounds) }
}

/** GET hazard grid → { grid, summary: { level?, score?, confidence? } } */
export async function getHazardGrid(bounds) {
  const r = await request(endpoints.hazardGrid, { query: boundsQuery(bounds) })
  if (r?.error) return r
  const grid = normalizeGrid(r, bounds)
  if (!grid) return null
  const s = r.summary || {}
  return {
    grid,
    summary: {
      level: ['Low', 'Medium', 'High'].includes(s.level) ? s.level : null,
      score: numOrNull(s.score),
      confidence: numOrNull(s.confidence),
    },
  }
}

/** GET elevation grid → { grid, slope?, features? } (meters; slope in degrees) */
export async function getElevationGrid(bounds, resolution = ELEVATION_RESOLUTION) {
  const r = await request(endpoints.elevationGrid, { query: { ...boundsQuery(bounds), resolution } })
  if (r?.error) return r
  const grid = normalizeGrid(r, bounds)
  if (!grid) return null
  const slope = Array.isArray(r.slope) || ArrayBuffer.isView(r.slope)
    ? normalizeGrid({ ...r, values: r.slope, min: undefined, max: undefined }, bounds)
    : null
  const features = Array.isArray(r.features)
    ? r.features.filter((f) => f && isNum(f.lat) && isNum(f.lon) && typeof f.label === 'string')
    : []
  return { grid, slope, features }
}

/** POST elevation profile for a route → { distancesKm[], elevations[], min, max } */
export async function getElevationProfile(route) {
  if (!route) return null
  const r = await request(endpoints.elevationProfile, { body: { route: route.feature } })
  if (r?.error) return r
  if (!r || !Array.isArray(r.distancesKm) || !Array.isArray(r.elevations)) return null
  if (r.distancesKm.length < 2 || r.distancesKm.length !== r.elevations.length) return null
  return {
    distancesKm: r.distancesKm,
    elevations: r.elevations,
    min: isNum(r.min) ? r.min : Math.min(...r.elevations),
    max: isNum(r.max) ? r.max : Math.max(...r.elevations),
    sampleIntervalKm: isNum(r.sampleIntervalKm) ? r.sampleIntervalKm : null,
  }
}

/** GET composition → { components: [{ name, fraction, color? }] } */
export async function getComposition(region) {
  const r = await request(endpoints.composition, { query: regionQuery(region) })
  if (r?.error) return r
  const components = normCatalog(r?.components)
  return components.length ? { components, basis: r.basis || null } : null
}

/** GET CRISM mineral catalog. The backend intentionally supplies no abundance ratio. */
export async function getMineralRatio(region) {
  const r = await request(endpoints.mineralRatio, { query: regionQuery(region) })
  if (r?.error) return r
  const minerals = normCatalog(r?.minerals)
  return minerals.length ? { ratio: numOrNull(r.ratio), minerals, basis: r.basis || null, grid: normalizeGrid(r.grid, region?.bounds) } : null
}

/** POST route { start, end } → GeoJSON Feature (LineString) + properties; normalised below. */
export async function getRoute(start, end, options = {}) {
  const r = await request(endpoints.route, { body: { start, end, ...options } })
  if (r?.error) return r
  const coords = r?.geometry?.coordinates
  if (!Array.isArray(coords) || coords.length < 2) return null
  const p = r.properties || {}
  return {
    feature: r,
    coordinates: coords, // [lon, lat][]
    waypoints: Array.isArray(p.waypoints) ? p.waypoints.filter((w) => w && isNum(w.lat) && isNum(w.lon)) : [],
    distanceKm: numOrNull(p.distanceKm),
    durationHours: numOrNull(p.durationHours),
    difficulty: typeof p.difficulty === 'string' ? p.difficulty : null,
    difficultyScore: numOrNull(p.difficultyScore),
    feasibility: p.feasibility || null,
    hazardExposure: p.hazardExposure || null,
    energy: p.energy || {},
    evaDurationCheck: p.evaDurationCheck || null,
    comparison: Array.isArray(p.comparison) ? p.comparison.map((item) => ({
      label: item.label,
      safetyWeight: item.safetyWeight,
      coordinates: item.feature?.geometry?.coordinates || [],
    })) : [],
    missionMode: p.mode || 'rover',
  }
}

/** POST mission report for a route → report object */
export async function getMissionReport(route) {
  if (!route) return null
  const r = await request(endpoints.missionReport, { body: { route: route.feature } })
  if (!r || !isNum(r.distanceKm)) return null
  const res = r.resources || {}
  return {
    distanceKm: r.distanceKm,
    travelTimeHours: numOrNull(r.travelTimeHours),
    difficultyScore: numOrNull(r.difficultyScore),
    feasibility: r.feasibility || null,
    hazardExposure: r.hazardExposure || null,
    mode: r.mode || null,
    evaDurationCheck: r.evaDurationCheck || null,
    resources: { powerKwh: numOrNull(res.powerKwh), propulsionKwh: numOrNull(res.propulsionKwh), hotelKwh: numOrNull(res.hotelKwh), waterL: numOrNull(res.waterL), oxygenKg: numOrNull(res.oxygenKg) },
    summary: typeof r.summary === 'string' ? r.summary : '',
    generatedAt: typeof r.generatedAt === 'string' ? r.generatedAt : null,
  }
}

/** GET the regional display-only MOLA metadata. */
export async function getRegionalOverview() {
  const r = await request(endpoints.regionalOverview)
  return r?.available === true ? r : null
}

/** GET one lazily loaded regional map viewport; this never requests hazards. */
export async function getRegionalGrid(bounds, resolution = 256) {
  const r = await request(endpoints.regionalGrid, { query: { ...boundsQuery(bounds), resolution } })
  const grid = normalizeGrid(r, bounds)
  return grid ? { grid, cache: r.cache, source: r.source, analysisScope: r.analysis_scope } : null
}

/** GET GeoJSON display extents for named regional features. */
export async function getRegionalFeatures() {
  const r = await request(endpoints.regionalFeatures)
  if (!Array.isArray(r?.features)) return null
  return r.features
    .filter((f) => f?.geometry?.type === 'Polygon' && Array.isArray(f.geometry.coordinates?.[0]) && f.properties?.name)
    .map((f) => ({ ...f.properties, coordinates: f.geometry.coordinates[0] }))
}

